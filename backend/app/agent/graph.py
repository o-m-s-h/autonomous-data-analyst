"""V4: bounded SQL, Python statistics and chart tools in one evidence loop."""
import json
from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END

from app.agent.state import AnalystState
from app.agent.content import answer_text
from app.agent.prompts import ANALYST_SYSTEM_PROMPT, FINAL_ANALYSIS_PROMPT, VISUAL_ANALYSIS_PROMPT
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.tools.sql_tool import get_schema, execute_sql


MAX_TOOL_ROUNDS = 3
MAX_QUERIES_PER_ROUND = 4
MAX_RESULT_ROWS = 50
MAX_RESULT_CHARS = 12000
MAX_CHARTS = 2


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

    @tool
    def run_statistics(
        sql: str,
        method: Literal["pearson", "spearman", "welch_ttest", "chi_square", "ols"],
        x: str = "", y: str = "", predictors: list[str] | None = None,
        hypothesis: str = "Investigate a statistical relationship",
    ) -> str:
        """Run a predefined Python statistical analysis on SQL-selected observations.

        SELECT raw needed columns from dataset, not a preview or arbitrary LIMIT.
        Maximum 50000 rows, 20 columns. Pearson/Spearman: numeric x and y.
        Welch: x has exactly two groups, y is numeric; rows are independent.
        Chi-square: categorical x/y, one observation per row, not aggregate counts.
        OLS: numeric y and 1-12 numeric predictors; x is unused. Returns coefficients,
        uncertainty and caveats. This tool does not execute arbitrary Python code.
        """
        from app.tools.statistics_tool import analyze_statistics
        return analyze_statistics(file_path, sql, method, x, y, predictors)

    @tool
    def plot_chart(
        sql: str, kind: Literal["bar", "line", "scatter", "histogram", "box"],
        x: str, y: str = "", title: str = "",
        hypothesis: str = "Show a useful pattern",
    ) -> str:
        """Create a Matplotlib chart from SQL-selected rows of dataset.

        Bar: <=40 rows, one per category x, numeric y (aggregate in SQL).
        Line: unique numeric/date x and numeric y, <=5000 rows, sorted by x.
        Scatter: numeric x/y, <=5000 rows. Histogram: numeric x only.
        Box: categorical x (<=12 groups), numeric y. All inputs <=50000 rows.
        Choose a clear title that describes the selected data and any filtering.
        At most two charts per answer. The chart appears directly in the UI.
        """
        from app.tools.visualization_tool import create_chart
        return create_chart(file_path, sql, kind, x, y, title)

    return [inspect_schema, run_sql, run_statistics, plot_chart]


def create_graph(file_path: str):
    # Once per request: no model round trip just to discover the schema.
    schema = get_schema(file_path)
    tools = {item.name: item for item in create_tools(file_path, schema)}
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
    )
    llm_with_tools = llm.bind_tools(list(tools.values()))

    def analyst(state: AnalystState):
        rounds = state.get("tool_rounds", 0)
        force_final = rounds >= MAX_TOOL_ROUNDS
        prompt = ANALYST_SYSTEM_PROMPT + "\nDataset schema:\n" + schema
        if state.get("include_visuals", True):
            prompt += "\n" + VISUAL_ANALYSIS_PROMPT
        else:
            prompt += "\nGenerate charts only if the question explicitly requests one."
        prompt += f"\nSuccessfully generated charts: {len(state.get('charts', []))}."
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
            update["final_conclusion"] = answer_text(response.content)
        return update

    def execute_tools(state: AnalystState):
        # Every call gets a matching tool response, including failures/skips.
        # Local execution is sequential to bound memory; planning is batched.
        messages = []
        evidence = list(state.get("evidence", []))
        queries = list(state.get("executed_queries", []))
        results = list(state.get("query_results", []))
        cache = dict(state.get("query_cache", {}))
        charts = list(state.get("charts", []))
        for index, call in enumerate(state["messages"][-1].tool_calls):
            name, args = call["name"], call["args"]
            sql = args.get("sql", "")
            # Include operation and parameters; identical SQL can feed different tests.
            key = json.dumps([name, {k: v for k, v in args.items() if k != "hypothesis"}], sort_keys=True)
            cached = False
            if index >= MAX_QUERIES_PER_ROUND:
                payload = {"error": "Round limit reached; this tool was not executed."}
            elif name not in tools:
                payload = {"error": "Unknown tool. Use inspect_schema, run_sql, run_statistics or plot_chart."}
            elif key in cache:
                payload = cache[key]
                cached = True
            elif name == "plot_chart" and len(charts) >= MAX_CHARTS:
                payload = {"error": "Two charts already exist. Use their evidence or finish the answer."}
            else:
                try:
                    content = tools[name].invoke(args)
                    payload = {"schema": content} if name == "inspect_schema" else json.loads(content)
                    if "chart" in payload:
                        # Image bytes never enter model context or the evidence cache.
                        chart = {**payload["chart"], "id": f"chart-{len(charts) + 1}"}
                        charts.append(chart)
                        payload["chart"] = {k: v for k, v in chart.items() if k != "image"}
                    cache[key] = payload
                except Exception as exc:
                    payload = {"error": str(exc)[:1000]}
            messages.append(ToolMessage(
                content=json.dumps(payload, ensure_ascii=False),
                tool_call_id=call["id"], name=name,
            ))
            if name in {"run_sql", "run_statistics", "plot_chart"}:
                evidence.append({
                    "tool": name,
                    "hypothesis": args.get("hypothesis", "Answer the question"),
                    "parameters": {k: v for k, v in args.items() if k not in {"sql", "hypothesis"}},
                    "sql": sql, "cached": cached, **payload,
                })
                if name == "run_sql" and "rows" in payload and not cached:
                    queries.append(sql)
                    results.append(payload["rows"])
        return {
            "messages": messages, "evidence": evidence,
            "executed_queries": queries, "query_results": results,
            "query_cache": cache, "tool_rounds": state.get("tool_rounds", 0) + 1,
            "charts": charts,
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
