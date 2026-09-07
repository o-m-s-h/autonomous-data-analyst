from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage
)

from app.agent.graph import create_graph


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"]
)


class AnalysisRequest(BaseModel):
    dataset_id: str
    question: str


DATASETS = {}


def register_dataset(
    dataset_id: str,
    file_path: str
):
    DATASETS[dataset_id] = file_path


@router.post("/ask")
def analyze(request: AnalysisRequest):

    if request.dataset_id not in DATASETS:

        raise HTTPException(
            status_code=404,
            detail="Dataset not found."
        )

    file_path = DATASETS[
        request.dataset_id
    ]

    try:

        # -----------------------------------------
        # Create dataset-specific LangGraph
        # -----------------------------------------

        graph = create_graph(
            file_path
        )

        initial_state = {
            "messages": [
                HumanMessage(
                    content=request.question
                )
            ],
            "dataset_id": request.dataset_id,
            "file_path": file_path
        }

        # -----------------------------------------
        # Run agent
        # -----------------------------------------

        final_state = graph.invoke(
            initial_state
        )

        messages = final_state["messages"]

        # -----------------------------------------
        # Extract SQL + result from tool calls
        # -----------------------------------------

        sql = None
        result = []

        for i, message in enumerate(messages):

            # Find LLM tool call
            if isinstance(message, AIMessage):

                if not message.tool_calls:
                    continue

                for tool_call in message.tool_calls:

                    if tool_call["name"] == "run_sql":

                        sql = tool_call["args"].get(
                            "sql"
                        )

                        # The next ToolMessage contains
                        # the result of this SQL query.
                        if i + 1 < len(messages):

                            next_message = messages[i + 1]

                            if isinstance(
                                next_message,
                                ToolMessage
                            ):

                                tool_result = (
                                    next_message.content
                                )

                                result = json.loads(tool_result)

        # -----------------------------------------
        # Final explanation
        # -----------------------------------------

        explanation = ""

        for message in reversed(messages):

            if isinstance(message, AIMessage):

                # Ignore AI messages that only contain
                # tool calls.
                if message.content:

                    explanation = message.content

                    break

        # -----------------------------------------
        # Return OLD API CONTRACT
        # -----------------------------------------

        return {
            "question": request.question,
            "sql": sql,
            "result": result,
            "explanation": explanation
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


