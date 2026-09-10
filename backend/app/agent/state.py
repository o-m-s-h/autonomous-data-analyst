from typing import Annotated

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class AnalystState(TypedDict, total=False):

    # -------------------------
    # Existing V2 state
    # -------------------------

    messages: Annotated[
        list[BaseMessage],
        add_messages
    ]

    dataset_id: str
    file_path: str

    # -------------------------
    # V3 hypothesis system
    # -------------------------

    hypotheses: list[str]

    current_hypothesis_index: int

    current_hypothesis: str

    # -------------------------
    # Investigation tracking
    # -------------------------

    executed_queries: list[str]

    query_results: list[list[dict]]

    # Queries/results belonging only
    # to the current hypothesis
    current_queries: list[str]

    current_results: list[list[dict]]

    # Number of investigation rounds
    # for the current hypothesis
    investigation_round: int

    # Maximum rounds allowed for
    # one hypothesis
    max_investigation_rounds: int

    # Number of tool-execution turns used for the current hypothesis.
    # This is the hard guard against an LLM repeatedly requesting tools.
    tool_rounds: int

    # -------------------------
    # Hypothesis evaluation
    # -------------------------

    hypothesis_status: str

    needs_more_analysis: bool

    investigation_history: list[dict]

    # -------------------------
    # Final result
    # -------------------------

    final_conclusion: str
