from typing import Annotated

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AnalystState(TypedDict):

    messages: Annotated[
        list[BaseMessage],
        add_messages
    ]

    dataset_id: str

    file_path: str

    executed_queries: list[str]

    query_results: list[list[dict]]