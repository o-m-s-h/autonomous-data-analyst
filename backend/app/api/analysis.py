from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langchain_core.messages import HumanMessage

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
def analyze(
    request: AnalysisRequest
):

    if request.dataset_id not in DATASETS:

        raise HTTPException(
            status_code=404,
            detail="Dataset not found."
        )


    file_path = DATASETS[
        request.dataset_id
    ]


    try:

        graph = create_graph(
            file_path
        )


        initial_state = {

            "messages": [
                HumanMessage(
                    content=request.question
                )
            ],

            "dataset_id":
                request.dataset_id,

            "file_path":
                file_path,

            "executed_queries": [],

            "query_results": []
        }


        final_state = graph.invoke(
            initial_state
        )


        messages = final_state[
            "messages"
        ]


        # -----------------------------------------
        # Final explanation
        # -----------------------------------------

        explanation = ""

        for message in reversed(messages):

            if (
                hasattr(message, "content")
                and message.content
            ):

                # Last textual LLM response
                if message.type == "ai":

                    explanation = message.content

                    break


        # -----------------------------------------
        # Get final SQL/result
        # -----------------------------------------

        executed_queries = final_state.get(
            "executed_queries",
            []
        )

        query_results = final_state.get(
            "query_results",
            []
        )


        sql = (
            executed_queries[-1]
            if executed_queries
            else None
        )


        result = (
            query_results[-1]
            if query_results
            else []
        )


        # -----------------------------------------
        # Preserve V1 API
        # -----------------------------------------

        return {

            "question":
                request.question,

            "sql":
                sql,

            "result":
                result,

            "explanation":
                explanation
        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )