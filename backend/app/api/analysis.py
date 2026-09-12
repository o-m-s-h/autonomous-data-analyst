from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from app.agent.graph import create_graph


router = APIRouter(prefix="/analysis", tags=["Analysis"])


class AnalysisRequest(BaseModel):
    dataset_id: str
    question: str = Field(min_length=1, max_length=4000)
    include_visuals: bool = True


DATASETS = {}


def register_dataset(dataset_id: str, file_path: str):
    DATASETS[dataset_id] = file_path


@router.post("/ask")
def analyze(request: AnalysisRequest):
    if request.dataset_id not in DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Please enter a question.")

    file_path = DATASETS[request.dataset_id]
    started = perf_counter()
    try:
        graph = create_graph(file_path)
        final_state = graph.invoke({
            "messages": [HumanMessage(content=request.question.strip())],
            "dataset_id": request.dataset_id,
            "file_path": file_path,
            "include_visuals": request.include_visuals,
            "executed_queries": [],
            "query_results": [],
        })
        queries = final_state.get("executed_queries", [])
        results = final_state.get("query_results", [])
        # Keep the V1 response fields; expose all V3 evidence separately.
        return {
            "question": request.question,
            "sql": queries[-1] if queries else None,
            "result": results[-1] if results else [],
            "explanation": final_state.get("final_conclusion", ""),
            "evidence": final_state.get("evidence", []),
            "charts": final_state.get("charts", []),
            "metrics": {
                "elapsed_seconds": round(perf_counter() - started, 2),
                "llm_calls": final_state.get("llm_calls", 0),
                "query_count": sum(
                    1 for item in final_state.get("evidence", [])
                    if not item.get("error") and not item.get("cached")
                ),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
