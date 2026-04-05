"""
LangGraph-приложение прототипирования (узлы из graph.spec).
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langsmith import traceable

from prototiping.graph.spec import GRAPH_EDGE_ORDER, GRAPH_NODES_SPEC


class ScenarioState(TypedDict, total=False):
    """Состояние графа LangGraph: накопление списков результатов проверок."""

    results: Annotated[list, operator.add]


def _node_factory(node_id: str, fns: tuple):
    """Создаёт callable узла графа: вызывает все ``fns`` и возвращает фрагмент состояния.

    :param node_id: Идентификатор узла (для ``@traceable``).
    :type node_id: str
    :param fns: Кортеж функций проверок без аргументов.
    :type fns: tuple

    :returns: Функция ``_node(state) -> {"results": [...]}``.
    :rtype: typing.Callable
    """
    @traceable(name=f"proto_node_{node_id}")
    def _node(_: ScenarioState) -> dict:
        return {"results": [f() for f in fns]}

    _node.__name__ = f"node_{node_id}"
    return _node


def build_scenario_graph():
    """Собирает скомпилированный LangGraph по ``GRAPH_NODES_SPEC`` и ``GRAPH_EDGE_ORDER``.

    :returns: Скомпилированный граф (у объекта есть ``invoke``).
    :rtype: typing.Any

    Пример::

        g = build_scenario_graph()
        g.invoke({})
    """
    g = StateGraph(ScenarioState)
    for spec in GRAPH_NODES_SPEC:
        g.add_node(spec["id"], _node_factory(spec["id"], tuple(spec["checks"])))
    g.add_edge(START, GRAPH_EDGE_ORDER[0])
    for a, b in zip(GRAPH_EDGE_ORDER, GRAPH_EDGE_ORDER[1:]):
        g.add_edge(a, b)
    g.add_edge(GRAPH_EDGE_ORDER[-1], END)
    return g.compile()


@traceable(name="proto_run_full_scenario_graph")
def run_full_scenario_graph() -> dict:
    """Однократный ``invoke`` полного графа с тегами LangSmith.

    :returns: Финальное состояние (в т.ч. ключ ``results`` со списком ответов проверок).
    :rtype: dict
    """
    graph = build_scenario_graph()
    return graph.invoke(
        {},
        config={
            "run_name": "fuel_tracker_prototype_full",
            "tags": ["prototyping", "fuel-tracker-bot"],
        },
    )


def summarize_results(final: dict) -> tuple[int, int, list[dict]]:
    """Считает число успешных и проваленных проверок из результата ``invoke``.

    :param final: Словарь состояния после ``graph.invoke`` (LangGraph агрегирует ``results``).
    :type final: dict

    :returns: Кортеж ``(ok_count, fail_count, results)``.
    :rtype: tuple[int, int, list[dict]]
    """
    results = final.get("results") or []
    ok_n = sum(1 for r in results if r.get("ok"))
    fail_n = len(results) - ok_n
    return ok_n, fail_n, results
