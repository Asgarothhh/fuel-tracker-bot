import requests
import logging
import time
from datetime import datetime, timezone
from src.app.config import (
    BEL_PASSWORD,
    BEL_EMITENT_ID,
    BEL_CONTRACT_ID,
)
from src.app.legacy_ssl import LegacySSLAdapter


# --- HTTP session с legacy SSL ---
session = requests.Session()
session.mount("https://", LegacySSLAdapter())


# --- API endpoints ---
TOKEN_URL = "https://belorusneft.by/identity/connect/token"
OPERATIONAL_URL = "https://belorusneft.by/rcp.api/Contract/operational"


# --- Кэш токена ---
_token_cache = {
    "access_token": None,
    "expires_at": 0
}


# --- Формирование username ---
def get_username():
    return f"{BEL_EMITENT_ID}.{BEL_CONTRACT_ID}"



# --- Авторизация ---
def auth():
    now = time.time()
    print("USERNAME:", get_username())
    print("PASSWORD RAW:", repr(BEL_PASSWORD))
    # Используем кэш, если токен ещё жив
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

    r = session.post(TOKEN_URL, data=data, headers=headers, timeout=15)

    if r.status_code != 200:
        logging.error("Auth error: %s %s", r.status_code, r.text)
        r.raise_for_status()

    j = r.json()
    access = j["access_token"]
    expires_in = int(j.get("expires_in", 3600))

    _token_cache["access_token"] = access
    _token_cache["expires_at"] = now + expires_in

    logging.info("Belorusneft API: auth OK, expires_in=%s", expires_in)

    return access


# --- Получение пооперационного отчёта ---
def fetch_operational_report(date):
    token = auth()

    payload = {
        "date": date.strftime("%Y-%m-%d")
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    r = session.post(OPERATIONAL_URL, json=payload, headers=headers, timeout=30)

    if r.status_code != 200:
        logging.error("Operational report error: %s %s", r.status_code, r.text)
        r.raise_for_status()

    return r.json()


# --- Парсер операций ---
def parse_operations(payload):
    items = payload.get("items") or payload.get("data") or []

    ops = []
    for item in items:
        ops.append({
            "date_time": item.get("dateTimeIssue"),
            "product": item.get("productName"),
            "quantity": item.get("productQuantity"),
            "cost": item.get("productCost"),
            "azs": item.get("azsNumber"),
            "car_num": item.get("carNum"),
            "driver": item.get("driverName"),
            "doc_number": item.get("docNumber"),
            "card_number": item.get("cardNumber"),
            "raw": item
        })
    return ops
