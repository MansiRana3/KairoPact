from __future__ import annotations

from typing import Any, Awaitable, Callable, cast

from langgraph.graph import END, START, StateGraph

from app.v1.schemas import DocumentAnalysisState

GraphNode = Callable[[DocumentAnalysisState], Awaitable[dict[str, Any]]]


def build_document_analysis_graph(
    *,
    ingest_node: GraphNode,
    retrieve_node: GraphNode,
    synthesise_node: GraphNode,
) -> Any:
    workflow = StateGraph(DocumentAnalysisState)
    workflow.add_node("ingest_node", cast(Any, ingest_node))
    workflow.add_node("retrieve_node", cast(Any, retrieve_node))
    workflow.add_node("synthesise_node", cast(Any, synthesise_node))

    workflow.add_edge(START, "ingest_node")
    workflow.add_edge("ingest_node", "retrieve_node")
    workflow.add_edge("retrieve_node", "synthesise_node")
    workflow.add_edge("synthesise_node", END)

    return workflow.compile()
