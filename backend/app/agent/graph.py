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

        Returns column names and their data types.
        """

        return get_schema(file_path)


    @tool
    def run_sql(sql: str) -> str:
        """
        Execute a read-only DuckDB SQL query.

        The uploaded CSV is available as table `dataset`.

        Only SELECT and WITH queries are allowed.
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


    llm = ChatOpenAI(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL,
    temperature=0
    )


    llm_with_tools = llm.bind_tools(
        tools
    )


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


    tool_node = ToolNode(
        tools
    )


    def should_continue(
        state: AnalystState
    ):

        last_message = state["messages"][-1]

        if last_message.tool_calls:

            return "tools"

        return END


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
        "analyst"
    )


    return builder.compile()