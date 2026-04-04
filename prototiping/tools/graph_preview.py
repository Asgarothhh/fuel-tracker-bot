"""
Генерация prototiping/output/graph_preview.html — Mermaid + подробности по каждой проверке.

Использует .last_prototype_trace.json или выполняет короткий прогон.
"""
from __future__ import annotations

import html
import json

from prototiping.lib.env import load_prototype_env
from prototiping.lib.paths import OUTPUT_DIR, TRACE_JSON
from prototiping.reporting.diagram import build_mermaid_source_for_browser


def _load_trace() -> dict | None:
    if TRACE_JSON.is_file():
        try:
            return json.loads(TRACE_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    from prototiping.graph.trace import run_prototype_traced

    load_prototype_env()
    return run_prototype_traced(console=False, write_trace_json=True)


def build_scenarios_sections_html(trace: dict) -> str:
    from prototiping.checks.scenarios import SCENARIO_META

    parts: list[str] = [
        '<section id="scenarios-detail" class="scenarios">',
        "<h2>Подробно по узлам и проверкам</h2>",
        '<p class="nav-top"><a href="#mermaid-block">↑ Диаграмма</a> · '
        '<a href="#top">↑ Наверх</a></p>',
        '<div class="nodes">',
    ]
    for idx, node in enumerate(trace.get("nodes") or [], start=1):
        nid = node["id"]
        n_ok = node.get("ok")
        title = node.get("title", "")
        ms = node.get("elapsed_ms", "")
        status_class = "ok" if n_ok else "fail"
        status_txt = "успех узла" if n_ok else "ошибка в узле"
        nid_e = html.escape(nid)
        parts.append(
            f'<article class="node-card {status_class}" id="node-{nid_e}">'
            f'<h3><span class="badge {status_class}">{html.escape(status_txt)}</span> '
            f"Узел {idx}: <code>{nid_e}</code></h3>"
            f'<p class="node-meta">{html.escape(title)} · <strong>{html.escape(str(ms))} ms</strong></p>'
            '<table class="checks"><thead><tr>'
            "<th>ID</th><th>Функция</th><th>Сценарий</th>"
            "<th>Проверяемый код</th><th>Что проверяется</th><th>Результат</th><th>Детали</th>"
            "</tr></thead><tbody>"
        )
        for c in node.get("checks") or []:
            fn = c.get("fn", "")
            meta = SCENARIO_META.get(fn, {})
            sid = html.escape(str(meta.get("id", "—")))
            fn_e = html.escape(fn)
            stitle = html.escape(str(meta.get("title", "—")))
            code_raw = str(meta.get("code_under_test", "—"))
            desc_raw = str(meta.get("description", "—"))
            code_e = html.escape(code_raw)
            desc_e = html.escape(desc_raw)
            code_short = code_e if len(code_e) <= 140 else code_e[:137] + "…"
            desc_short = desc_e if len(desc_e) <= 220 else desc_e[:217] + "…"
            cok = c.get("ok")
            row_cls = "row-ok" if cok else "row-fail"
            res_txt = "OK" if cok else "FAIL"
            det_raw = c.get("detail") or "—"
            det_cell = html.escape(det_raw).replace("\n", "<br/>")
            parts.append(f'<tr class="{row_cls}">')
            parts.append(f"<td>{sid}</td><td><code>{fn_e}</code></td><td>{stitle}</td>")
            parts.append(
                f'<td class="code" title="{code_e}">{code_short}</td>'
                f'<td class="desc" title="{desc_e}">{desc_short}</td>'
                f'<td><span class="pill {"pill-ok" if cok else "pill-fail"}">{res_txt}</span></td>'
                f'<td class="detail">{det_cell}</td>'
            )
            parts.append("</tr>")
        parts.append("</tbody></table></article>")
    parts.append("</div></section>")
    return "\n".join(parts)


def build_html(trace: dict) -> str:
    mermaid_src = build_mermaid_source_for_browser(trace)
    graph = html.escape(trace.get("graph", ""))
    ok = trace.get("overall_ok")
    status = "успех" if ok else "есть ошибки"
    status_class = "ok" if ok else "fail"
    scenarios_html = build_scenarios_sections_html(trace)

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Граф прототипирования — {graph}</title>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{ theme: "dark" }});
    await mermaid.run({{ querySelector: ".mermaid-render" }});
  </script>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 1.5rem; background: #111; color: #e6e6e6; line-height: 1.45; }}
    body#top {{ scroll-behavior: smooth; }}
    h1 {{ font-size: 1.35rem; }}
    h2 {{ font-size: 1.1rem; margin-top: 2rem; border-bottom: 1px solid #333; padding-bottom: 0.35rem; }}
    h3 {{ font-size: 1rem; margin: 0 0 0.5rem 0; }}
    .nav {{ margin: 1rem 0; font-size: 0.95rem; }}
    .nav a {{ color: #7cb8ff; margin-right: 1rem; }}
    .nav-top {{ font-size: 0.9rem; margin: 0 0 1rem 0; }}
    .nav-top a {{ color: #7cb8ff; }}
    .status {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 6px; font-weight: 600; }}
    .status.ok {{ background: #1a472a; color: #cfe; }}
    .status.fail {{ background: #5c1a1a; color: #fcc; }}
    .mermaid {{ background: #1a1a1a; padding: 1rem; border-radius: 8px; margin-top: 0.5rem; }}
    pre.raw {{ white-space: pre-wrap; font-size: 0.75rem; color: #888; }}
    .node-card {{ border: 1px solid #333; border-radius: 10px; padding: 1rem 1.1rem; margin-bottom: 1.5rem; background: #161616; }}
    .node-card.ok {{ border-left: 4px solid #2d6a3e; }}
    .node-card.fail {{ border-left: 4px solid #8b2a2a; }}
    .badge {{ font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 4px; margin-right: 0.5rem; }}
    .badge.ok {{ background: #1a472a; color: #cfe; }}
    .badge.fail {{ background: #5c1a1a; color: #fcc; }}
    .node-meta {{ color: #aaa; font-size: 0.9rem; margin: 0 0 1rem 0; }}
    table.checks {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
    table.checks th, table.checks td {{ border: 1px solid #2a2a2a; padding: 0.45rem 0.5rem; vertical-align: top; }}
    table.checks th {{ background: #222; text-align: left; }}
    tr.row-ok td {{ background: #0f1a12; }}
    tr.row-fail td {{ background: #1a0f0f; }}
    td.code, td.desc {{ max-width: 14rem; word-break: break-word; }}
    td.detail {{ max-width: 18rem; }}
    .pill {{ display: inline-block; padding: 0.1rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }}
    .pill-ok {{ background: #1a472a; color: #cfe; }}
    .pill-fail {{ background: #6b1c1c; color: #fcc; }}
    code {{ font-size: 0.85em; background: #222; padding: 0.1rem 0.25rem; border-radius: 3px; }}
  </style>
</head>
<body id="top">
  <h1>Граф: {graph}</h1>
  <p>Итог прогона: <span class="status {status_class}">{html.escape(status)}</span></p>
  <p>Источник: <code>prototiping/.last_prototype_trace.json</code> (обновляется при <code>pytest prototiping</code> или <code>python -m prototiping</code>)</p>
  <nav class="nav">
    <a href="#mermaid-block">Диаграмма Mermaid</a>
    <a href="#scenarios-detail">Подробности по сценариям</a>
    <a href="#mermaid-raw">Исходник Mermaid</a>
  </nav>

  <h2 id="mermaid-block">Диаграмма</h2>
  <pre class="mermaid mermaid-render">{mermaid_src}</pre>

  {scenarios_html}

  <h2 id="mermaid-raw">Исходник Mermaid (копирование)</h2>
  <pre class="raw">{html.escape(mermaid_src)}</pre>
</body>
</html>
"""


def main() -> None:
    import os

    load_prototype_env()
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("BOT_TOKEN", "000000:prototype-dummy-token")
    os.environ.setdefault("TOKEN_SALT", "prototype-test-salt")
    os.environ.setdefault("BEL_PASSWORD", "dummy")
    os.environ.setdefault("BEL_EMITENT_ID", "1")
    os.environ.setdefault("BEL_CONTRACT_ID", "1")
    trace = _load_trace()
    if not trace:
        print("Не удалось получить трассировку графа.")
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "graph_preview.html"
    out.write_text(build_html(trace), encoding="utf-8")
    print(out.resolve())


if __name__ == "__main__":
    main()
