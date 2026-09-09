import json
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.prebuilt import ToolNode

from app.agent.state import AnalystState
from app.agent.prompts import ANALYST_SYSTEM_PROMPT

from app.tools.sql_tool import (
    get_schema,
    execute_sql
)

from app.config import (
    LLM_API_KEY,
    LLM_MODEL,
    LLM_BASE_URL
)


def create_tools(file_path: str):

    @tool
    def inspect_schema() -> str:
        """
        Inspect the uploaded CSV dataset.

        Returns column names and data types.
        """

        return get_schema(file_path)


    @tool
    def run_sql(sql: str) -> str:
        """
        Execute a read-only DuckDB SQL query.

        The uploaded CSV is available as table `dataset`.

        Only SELECT and WITH queries are allowed.

        Returns the result as JSON.
        """

        result = execute_sql(
            file_path,
            sql
        )

        if result.empty:
            return "[]"

        return result.to_json(
            orient="records"
        )


    return [
        inspect_schema,
        run_sql
    ]


def create_graph(file_path: str):

    tools = create_tools(
        file_path
    )


    # -----------------------------------------
    # LLM
    # -----------------------------------------

    llm = ChatOpenAI(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        temperature=0
    )


    llm_with_tools = llm.bind_tools(
        tools
    )


    # -----------------------------------------
    # Analyst node
    # -----------------------------------------

    def analyst_node(
        state: AnalystState
    ):

        messages = state["messages"]

        system_message = SystemMessage(
            content=ANALYST_SYSTEM_PROMPT
        )

        response = llm_with_tools.invoke(
            [
                system_message,
                *messages
            ]
        )

        return {
            "messages": [response]
        }


    # -----------------------------------------
    # Tool node
    # -----------------------------------------

    tool_node = ToolNode(
        tools
    )


    # -----------------------------------------
    # Routing
    # -----------------------------------------

    def should_continue(
        state: AnalystState
    ):

        last_message = state["messages"][-1]

        if last_message.tool_calls:

            return "tools"

        return END

    def track_results(
            state: AnalystState
        ):
    
            messages = state["messages"]
    
            executed_queries = list(
                state.get(
                    "executed_queries",
                    []
                )
            )
    
            query_results = list(
                state.get(
                    "query_results",
                    []
                )
            )
    
    
            for i, message in enumerate(messages):
    
                if not isinstance(
                    message,
                    AIMessage
                ):
                    continue
    
    
                for tool_call in message.tool_calls:
    
                    if tool_call["name"] != "run_sql":
                        continue
    
    
                    sql = tool_call["args"].get(
                        "sql"
                    )
    
    
                    # Avoid recording the same query twice
                    if sql in executed_queries:
                        continue
    
    
                    executed_queries.append(
                        sql
                    )
    
    
                    # Find corresponding tool result
                    for next_message in messages[i + 1:]:
    
                        if not isinstance(
                            next_message,
                            ToolMessage
                        ):
                            continue
    
    
                        if (
                            next_message.tool_call_id
                            == tool_call["id"]
                        ):
    
                            try:
    
                                parsed_result = json.loads(
                                    next_message.content
                                )
    
                            except Exception:
    
                                parsed_result = []
    
    
                            query_results.append(
                                parsed_result
                            )
    
                            break
    
    
            return {
                "executed_queries":
                    executed_queries,
    
                "query_results":
                    query_results
            }

    # -----------------------------------------
    # Graph
    # -----------------------------------------

    builder = StateGraph(
        AnalystState
    )


    builder.add_node(
        "analyst",
        analyst_node
    )


    builder.add_node(
        "tools",
        tool_node
    )

    builder.add_node(
        "track_results",
        track_results
    )


    builder.add_edge(
        START,
        "analyst"
    )


    builder.add_conditional_edges(
        "analyst",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )


    builder.add_edge(
        "tools",
        "track_results"
    )

    builder.add_edge(
        "track_results",
        "analyst"
    )

    


    return builder.compile()    