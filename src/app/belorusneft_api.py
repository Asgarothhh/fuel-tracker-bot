# src/app/belorusneft_api.py
import requests
import logging
import time
import os
import json
from datetime import datetime
from typing import Any, Dict, Optional, List

from src.app.config import (
    BEL_PASSWORD,
    BEL_EMITENT_ID,
    BEL_CONTRACT_ID,
)
from src.app.legacy_ssl import LegacySSLAdapter

# HTTP session with legacy SSL adapter
session = requests.Session()
session.mount("https://", LegacySSLAdapter())

# Documented endpoints
TOKEN_URL = "https://belorusneft.by/identity/connect/token"
OPERATIONAL_URL = "https://ssl.beloil.by/rcp/i/api/v3/Contract/operational"

_token_cache: Dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def get_username() -> str:
    return f"{BEL_EMITENT_ID}.{BEL_CONTRACT_ID}"


def auth() -> str:
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 10:
        return _token_cache["access_token"]

    data = {
        "grant_type": "password",
        "client_id": "rcp.web",
        "client_secret": "secret",
        "scope": "rcp.api",
        "username": get_username(),
        "password": BEL_PASSWORD,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    logging.info("Belorusneft: requesting token for user=%s", get_username())
    r = session.post(TOKEN_URL, data=data, headers=headers, timeout=15)

    logging.debug("Auth request url=%s headers=%s body=%s", getattr(r.request, "url", TOKEN_URL), r.request.headers, getattr(r.request, "body", None))
    logging.debug("Auth response status=%s body=%s", r.status_code, r.text[:2000])

    if r.status_code != 200:
        logging.error("Auth error: %s %s", r.status_code, r.text[:2000])
        r.raise_for_status()

    j = r.json()
    access = j.get("access_token")
    expires_in = int(j.get("expires_in", 3600))

    if not access:
        logging.error("Auth response missing access_token: %s", j)
        raise RuntimeError("Auth failed: no access_token in response")

    _token_cache["access_token"] = access
    _token_cache["expires_at"] = now + expires_in

    logging.info("Belorusneft API: auth OK, expires_in=%s", expires_in)
    return access


def _save_response_text(text: str, filename: str):
    try:
        path = os.path.join(os.path.dirname(__file__), filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        logging.info("Saved response to %s", path)
    except Exception:
        logging.exception("Failed to save response to %s", filename)


def _ensure_str(v):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", errors="replace")
        except Exception:
            return str(v)
    try:
        return str(v)
    except Exception:
        return repr(v)


def _headers_to_dict(headers):
    out = {}
    try:
        for k, v in dict(headers).items():
            out[_ensure_str(k)] = _ensure_str(v)
    except Exception:
        try:
            for k, v in headers:
                out[_ensure_str(k)] = _ensure_str(v)
        except Exception:
            out["__headers_conversion_error__"] = "failed to convert headers"
    return out


def save_debug_dump(prefix: str, request_obj: requests.PreparedRequest, response_obj: requests.Response):
    """
    Save full debug dump: request (method, url, headers, body) and response (status, headers, body).
    Files:
      - {prefix}_request.txt
      - {prefix}_response.txt
      - {prefix}_full.json  (combined JSON with metadata)
    """
    base = os.path.join(os.path.dirname(__file__), f"{prefix}")
    try:
        # request
        req_path = base + "_request.txt"
        with open(req_path, "w", encoding="utf-8") as f:
            f.write(f"{_ensure_str(request_obj.method)} {_ensure_str(request_obj.url)}\n")
            f.write(json.dumps(_headers_to_dict(request_obj.headers), ensure_ascii=False, indent=2))
            f.write("\n\n")
            body = request_obj.body
            f.write(_ensure_str(body) or "")

        # response
        resp_path = base + "_response.txt"
        with open(resp_path, "w", encoding="utf-8") as f:
            f.write(f"HTTP {_ensure_str(response_obj.status_code)}\n")
            f.write(json.dumps(_headers_to_dict(response_obj.headers), ensure_ascii=False, indent=2))
            f.write("\n\n")
            f.write(_ensure_str(response_obj.text) or "")

        # combined metadata (JSON-safe)
        combined = {
            "request": {
                "method": _ensure_str(request_obj.method),
                "url": _ensure_str(request_obj.url),
                "headers": _headers_to_dict(request_obj.headers),
                "body_preview": (_ensure_str(request_obj.body) or "")[:2000]
            },
            "response": {
                "status": _ensure_str(response_obj.status_code),
                "headers": _headers_to_dict(response_obj.headers),
                "body_preview": (_ensure_str(response_obj.text) or "")[:2000]
            },
            "saved_at": datetime.utcnow().isoformat() + "Z"
        }
        with open(base + "_full.json", "w", encoding="utf-8") as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)

        logging.info("Saved debug dump: %s*, %s*, %s*", base + "_request.txt", base + "_response.txt", base + "_full.json")
    except Exception:
        logging.exception("Failed to save debug dump with prefix %s", prefix)


def fetch_operational_raw(date: datetime) -> Dict[str, Any]:
    """
    Perform a strict JSON POST to the documented operational endpoint and return a dict:
      {
        "status": int,
        "content_type": str or None,
        "text": str,
        "json": parsed_json or None,
        "debug_files": [paths...]
      }
    This function does NOT attempt to parse domain-specific operations; it only returns raw response and saves debug files.
    """
    token = auth()

    payload = {
        "startDate": date.strftime("%m-%d-%Y"),
        "endDate": date.strftime("%m-%d-%Y"),
        "contractId": int(BEL_CONTRACT_ID),
        "contractIssuerId": int(BEL_EMITENT_ID),
        "flChoice": 1,
        "cardNumber": 0,
        "subDivisnNumber": -1,
        "discountCode": 0,
        "AzsCode": -1,
        "EmtCodeFrm": -1
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # safe logging of payload preview
    date_preview = payload.get("startDate") or payload.get("date") or ""
    if date_preview:
        logging.info("Belorusneft: requesting operational raw for %s", date_preview)
    else:
        try:
            payload_preview = json.dumps(payload, ensure_ascii=False)
        except Exception:
            payload_preview = str(payload)
        logging.info("Belorusneft: requesting operational raw; payload preview: %s", (payload_preview[:200] + "...") if len(payload_preview) > 200 else payload_preview)

    logging.debug("Request URL: %s", OPERATIONAL_URL)
    logging.debug("Request headers: %s", headers)
    logging.debug("Request payload: %s", payload)

    try:
        r = session.post(OPERATIONAL_URL, json=payload, headers=headers, timeout=30)
    except requests.RequestException as e:
        logging.exception("Request to operational endpoint failed: %s", e)
        raise

    content_type = r.headers.get("Content-Type")
    result = {
        "status": r.status_code,
        "content_type": content_type,
        "text": r.text,
        "json": None,
        "debug_files": []
    }

    # try parse JSON safely
    if r.status_code == 200 and content_type and "application/json" in content_type:
        try:
            result["json"] = r.json()
        except Exception:
            logging.exception("Failed to parse JSON despite content-type header")

    # save debug dump always for later analysis
    prefix = f"belorusneft_operational_debug_{int(time.time())}"
    save_debug_dump(prefix, r.request, r)
    result["debug_files"] = [
        os.path.join(os.path.dirname(__file__), prefix + "_request.txt"),
        os.path.join(os.path.dirname(__file__), prefix + "_response.txt"),
        os.path.join(os.path.dirname(__file__), prefix + "_full.json"),
    ]

    # also save raw text for quick inspection
    _save_response_text(r.text or "", prefix + "_raw.html")

    return result


def parse_operations(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Универсальный парсер операций.
    Поддерживает:
      - documented API: payload.get('items') or payload.get('data')
      - current response: payload['cardList'][...]['issueRows'][...]
    Возвращает список операций с ключами:
      date_time, product, quantity, cost, azs, car_num, driver, doc_number, card_number, raw
    """
    ops: List[Dict[str, Any]] = []

    # 1) стандартный вариант items/data
    items = payload.get("items") or payload.get("data")
    if items:
        for item in items:
            ops.append({
                "date_time": item.get("dateTimeIssue"),
                "product": item.get("productName"),
                "quantity": item.get("productQuantity"),
                "cost": item.get("productCost"),
                "azs": item.get("azsNumber") or item.get("AzsCode") or item.get("azs"),
                "car_num": item.get("carNum") or item.get("carNumber"),
                "driver": item.get("driverName"),
                "doc_number": item.get("docNumber"),
                "card_number": item.get("cardNumber") or item.get("cardCode"),
                "raw": item
            })
        return ops

    # 2) текущая структура: cardList -> issueRows
    card_list = payload.get("cardList") or []
    for card in card_list:
        card_number = card.get("cardNumber")
        issue_rows = card.get("issueRows") or []
        for row in issue_rows:
            ops.append({
                "date_time": row.get("dateTimeIssue"),
                "product": row.get("productName"),
                "quantity": row.get("productQuantity"),
                "cost": row.get("productCost") or row.get("productUnitPrice"),
                "azs": row.get("azsNumber") or row.get("AzsCode"),
                "car_num": row.get("carNum") or row.get("carNum") or row.get("carNum"),
                "driver": row.get("driverName"),
                "doc_number": row.get("docNumber"),
                "card_number": card_number,
                "raw": {"card": card, "row": row}
            })

    return ops
