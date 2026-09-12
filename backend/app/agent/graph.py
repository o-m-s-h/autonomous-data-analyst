"""V3: plan queries together, then answer or investigate remaining gaps."""
import json

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END

from app.agent.state import AnalystState
from app.agent.prompts import ANALYST_SYSTEM_PROMPT, FINAL_ANALYSIS_PROMPT
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.tools.sql_tool import get_schema, execute_sql


MAX_TOOL_ROUNDS = 3
MAX_QUERIES_PER_ROUND = 4
MAX_RESULT_ROWS = 50
MAX_RESULT_CHARS = 12000


def create_tools(file_path: str, schema: str | None = None):
    @tool
    def inspect_schema() -> str:
        """Inspect columns and types; already supplied in the initial context."""
        return schema if schema is not None else get_schema(file_path)

    @tool
    def run_sql(sql: str, hypothesis: str = "Answer the question") -> str:
        """Test a hypothesis with read-only DuckDB SQL on table dataset.

        Supply a short plain-language hypothesis or purpose. Prefer aggregates:
        results are previews capped at 50 rows and 12000 characters.
        """
        result = execute_sql(file_path, sql)
        rows = json.loads(result.head(MAX_RESULT_ROWS).to_json(orient="records"))
        payload = {
            "rows": rows,
            "row_count": len(result),
            "truncated": len(result) > len(rows),
        }
        while rows and len(json.dumps(payload, ensure_ascii=False)) > MAX_RESULT_CHARS:
            rows.pop()
            payload["truncated"] = True
        return json.dumps(payload, ensure_ascii=False)

    return [inspect_schema, run_sql]


def create_graph(file_path: str):
    # Once per request: no model round trip just to discover the schema.
    schema = get_schema(file_path)
    tools = {item.name: item for item in create_tools(file_path, schema)}
    llm = ChatGroq(
        model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0,
        max_tokens=1800, timeout=45, max_retries=0,
    )
    llm_with_tools = llm.bind_tools(list(tools.values()))

    def analyst(state: AnalystState):
        rounds = state.get("tool_rounds", 0)
        force_final = rounds >= MAX_TOOL_ROUNDS
        prompt = ANALYST_SYSTEM_PROMPT + "\nDataset schema:\n" + schema
        prompt += f"\nCompleted query rounds: {rounds}/{MAX_TOOL_ROUNDS}."
        if force_final:
            prompt += "\n" + FINAL_ANALYSIS_PROMPT
        model = llm if force_final else llm_with_tools
        response = model.invoke([SystemMessage(content=prompt), *state["messages"]])
        update = {
            "messages": [response],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }
        if not response.tool_calls:
            update["final_conclusion"] = response.content
        return update

    def execute_tools(state: AnalystState):
        # Every call gets a matching tool response, including failures/skips.
        # Local execution is sequential to bound memory; planning is batched.
        messages = []
        evidence = list(state.get("evidence", []))
        queries = list(state.get("executed_queries", []))
        results = list(state.get("query_results", []))
        cache = dict(state.get("query_cache", {}))
        for index, call in enumerate(state["messages"][-1].tool_calls):
            name, args = call["name"], call["args"]
            sql = args.get("sql", "") if name == "run_sql" else ""
            # Preserve literal whitespace, which can change SQL semantics.
            key = sql.strip() if isinstance(sql, str) else ""
            cached = False
            if index >= MAX_QUERIES_PER_ROUND:
                payload = {"error": "Round limit reached; this query was not executed."}
            elif name not in tools:
                payload = {"error": "Unknown tool. Use run_sql or inspect_schema."}
            elif name == "run_sql" and key in cache:
                payload = cache[key]
                cached = True
            else:
                try:
                    content = tools[name].invoke(args)
                    payload = json.loads(content) if name == "run_sql" else {"schema": content}
                    if name == "run_sql":
                        cache[key] = payload
                except Exception as exc:
                    payload = {"error": str(exc)[:1000]}
            messages.append(ToolMessage(
                content=json.dumps(payload, ensure_ascii=False),
                tool_call_id=call["id"], name=name,
            ))
            if name == "run_sql":
                evidence.append({
                    "hypothesis": args.get("hypothesis", "Answer the question"),
                    "sql": sql, "cached": cached, **payload,
                })
                if "rows" in payload and not cached:
                    queries.append(sql)
                    results.append(payload["rows"])
        return {
            "messages": messages, "evidence": evidence,
            "executed_queries": queries, "query_results": results,
            "query_cache": cache, "tool_rounds": state.get("tool_rounds", 0) + 1,
        }

    builder = StateGraph(AnalystState)
    builder.add_node("analyst", analyst)
    builder.add_node("tools", execute_tools)
    builder.add_edge(START, "analyst")
    builder.add_conditional_edges(
        "analyst",
        lambda state: "tools" if state["messages"][-1].tool_calls else "done",
        {"tools": "tools", "done": END},
    )
    builder.add_edge("tools", "analyst")
    return builder.compile()
