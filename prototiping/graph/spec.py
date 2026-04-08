"""
Единая спецификация узлов графа: id, заголовок, список проверок.
Используется LangGraph, trace и отчёт.
"""
from __future__ import annotations

from typing import Any, Callable

from prototiping.checks import suite as chk

GRAPH_TITLE = "fuel_tracker_prototype"

GRAPH_NODES_SPEC: list[dict[str, Any]] = [
    {
        "id": "belorusneft_parse",
        "title": "Парсинг API / даты (Belorusneft)",
        "checks": [
            chk.check_parse_operations_items,
            chk.check_parse_operations_cardlist,
            chk.check_parse_api_datetime,
            chk.check_api_local_yesterday,
            chk.check_parse_operations_empty_items_fallback_cardlist,
            chk.check_parse_api_datetime_invalid_inputs,
        ],
    },
    {
        "id": "plates_import",
        "title": "Номера, импорт API, дедупликация",
        "checks": [
            chk.check_normalize_plate,
            chk.check_extract_flat_and_duplicate,
            chk.check_extract_flat_fields_malformed_raw,
            chk.check_import_api_operations_dry_run,
            chk.check_import_skips_without_date_and_doc,
        ],
    },
    {
        "id": "auth_permissions",
        "title": "Права и токены привязки",
        "checks": [
            chk.check_user_has_permission,
            chk.check_tokens_flow,
        ],
    },
    {
        "id": "excel_ocr",
        "title": "Схема чека и строка Excel",
        "checks": [
            chk.check_receipt_schema,
            chk.check_excel_operation_row,
        ],
    },
    {
        "id": "web_backend",
        "title": "Web backend: роутеры и сервисы",
        "checks": [
            chk.check_web_health_check,
            chk.check_web_get_db_yields_session,
            chk.check_web_get_users_endpoint,
            chk.check_web_get_all_users_role_fallback,
            chk.check_web_edit_user_updates_fields,
            chk.check_web_delete_user_success,
            chk.check_web_format_operation_api_fields,
            chk.check_web_get_operations_pending_filter,
            chk.check_web_confirm_reject_reassign_flow,
            chk.check_web_excel_builder_has_sheets,
            chk.check_breaker_web_unknown_tab_404,
            chk.check_breaker_web_edit_user_not_found_404,
            chk.check_breaker_web_delete_op_not_found_404,
            chk.check_breaker_web_reassign_not_found_404,
            chk.check_breaker_web_excel_empty_404,
        ],
    },
    {
        "id": "breaker_probes",
        "title": "Негативные (ломающие) сценарии",
        "checks": [
            chk.check_breaker_permissions_module_import_cycle_probe,
            chk.check_breaker_parse_operations_type_poison,
            chk.check_breaker_parse_operations_card_rows_type_poison,
            chk.check_breaker_import_quantity_format_dedup_gap,
            chk.check_breaker_import_invalid_cardlist_shape,
            chk.check_breaker_parse_api_datetime_naive_timezone,
        ],
    },
]

GRAPH_EDGE_ORDER: list[str] = [n["id"] for n in GRAPH_NODES_SPEC]


def all_check_functions() -> list[Callable[..., dict]]:
    """Плоский список всех callable проверок в порядке узлов ``GRAPH_NODES_SPEC``.

    :returns: Список функций ``check_*``; каждая без аргументов возвращает ``dict``.
    :rtype: list[typing.Callable[..., dict]]

    Пример::

        from prototiping.graph.spec import all_check_functions

        fns = all_check_functions()
        assert all(callable(f) for f in fns)
    """
    out: list[Callable[..., dict]] = []
    for spec in GRAPH_NODES_SPEC:
        out.extend(spec["checks"])
    return out


def verify_spec_matches_all_checks() -> None:
    """Проверяет, что множество проверок в спеке совпадает с ``checks.suite.ALL_CHECKS``.

    :returns: ``None``.

    :raises RuntimeError: Если длины или множества функций различаются.

    Пример::

        from prototiping.graph.spec import verify_spec_matches_all_checks

        verify_spec_matches_all_checks()
    """
    from prototiping.checks.suite import ALL_CHECKS

    spec_fns = all_check_functions()
    if len(spec_fns) != len(ALL_CHECKS) or set(spec_fns) != set(ALL_CHECKS):
        raise RuntimeError(
            "graph.spec.GRAPH_NODES_SPEC и checks.suite.ALL_CHECKS разошлись; синхронизируйте списки."
        )
