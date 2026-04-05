"""
Pytest: граф LangGraph, трассировка с Rich, точечные проверки.
"""
from __future__ import annotations

import pytest

from prototiping.checks.suite import ALL_CHECKS
from prototiping.graph.app import build_scenario_graph, summarize_results
from prototiping.graph.spec import verify_spec_matches_all_checks
from prototiping.graph.trace import run_prototype_traced


def test_graph_spec_matches_all_checks():
    """Согласованность ``GRAPH_NODES_SPEC`` и ``ALL_CHECKS``."""
    verify_spec_matches_all_checks()


@pytest.fixture(scope="module")
def graph():
    """Скомпилированный LangGraph на время модуля."""
    return build_scenario_graph()


def test_scenario_graph_runs_with_rich_console(graph):
    """Прямой прогон ``run_prototype_traced``: все проверки OK, длина flat = ``len(ALL_CHECKS)``."""
    trace_full = run_prototype_traced(console=True, write_trace_json=True)
    assert trace_full["overall_ok"], trace_full["nodes"]
    flat = trace_full["flat_results"]
    assert len(flat) == len(ALL_CHECKS), (len(flat), len(ALL_CHECKS))
    failed = [r for r in flat if not r.get("ok")]
    assert not failed, failed


def test_langgraph_invoke_matches_spec(graph):
    """Тот же набор проверок через ``graph.invoke`` и ``summarize_results``."""
    final = graph.invoke(
        {},
        config={
            "run_name": "fuel_tracker_prototype_pytest",
            "tags": ["prototyping", "pytest"],
        },
    )
    ok_n, fail_n, results = summarize_results(final)
    assert len(results) == len(ALL_CHECKS), (len(results), len(ALL_CHECKS))
    assert fail_n == 0, [r for r in results if not r.get("ok")]


@pytest.mark.parametrize("check_fn", ALL_CHECKS, ids=lambda f: f.__name__)
def test_individual_check(check_fn):
    """Каждая функция из ``ALL_CHECKS`` по отдельности возвращает ``ok``."""
    r = check_fn()
    assert r.get("ok"), f"{r.get('name')}: {r.get('detail')}"
