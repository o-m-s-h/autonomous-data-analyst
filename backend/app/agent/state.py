from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AnalystState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    dataset_id: str
    file_path: str
    executed_queries: list[str]
    query_results: list[list[dict]]
    evidence: list[dict]
    charts: list[dict]
    include_visuals: bool
    query_cache: dict[str, dict]
    tool_rounds: int
    llm_calls: int
    final_conclusion: str
