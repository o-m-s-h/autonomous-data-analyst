import json

from langchain_groq import ChatGroq

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage
)

from langchain_core.tools import tool

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.prebuilt import ToolNode

from app.agent.state import AnalystState

from app.agent.prompts import (
    ANALYST_SYSTEM_PROMPT,
    HYPOTHESIS_GENERATION_PROMPT,
    EVALUATION_PROMPT,
    FINAL_ANALYSIS_PROMPT
)

from app.tools.sql_tool import (
    get_schema,
    execute_sql
)

from app.config import GROQ_API_KEY, GROQ_MODEL


# ============================================================
# Configuration
# ============================================================

MAX_HYPOTHESES = 5
MAX_INVESTIGATION_ROUNDS = 3
MAX_TOOL_ROUNDS_PER_HYPOTHESIS = 4


# ============================================================
# Tools
# ============================================================

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


# ============================================================
# Create Graph
# ============================================================

def create_graph(file_path: str):

    tools = create_tools(file_path)

    llm = ChatGroq(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0
    )

    llm_with_tools = llm.bind_tools(tools)

    tool_node = ToolNode(tools)


    # ========================================================
    # V3 - Generate Hypotheses
    # ========================================================

    def generate_hypotheses(
        state: AnalystState
    ):

        question = state["messages"][0].content

        # Get schema directly so the hypothesis generator
        # knows what the dataset actually contains.
        schema = get_schema(file_path)

        prompt = HYPOTHESIS_GENERATION_PROMPT.format(
            question=question,
            schema=schema
        )

        response = llm.invoke(
            [
                SystemMessage(
                    content=prompt
                )
            ]
        )

        hypotheses = []

        for line in response.content.splitlines():

            line = line.strip()

            if not line:
                continue

            # Remove numbering:
            # "1. something"
            # "2. something"
            if "." in line[:4]:

                first_part, remaining = line.split(
                    ".",
                    1
                )

                if first_part.strip().isdigit():

                    line = remaining.strip()

            if line:
                hypotheses.append(line)


        hypotheses = hypotheses[
            :MAX_HYPOTHESES
        ]


        return {

            "hypotheses": hypotheses,

            "current_hypothesis_index": 0,

            "investigation_history": [],

            "executed_queries": [],

            "query_results": [],

            "current_queries": [],

            "current_results": [],

            "investigation_round": 0,

            "tool_rounds": 0,

            "max_investigation_rounds":
                MAX_INVESTIGATION_ROUNDS
        }


    # ========================================================
    # V3 - Select Hypothesis
    # ========================================================

    def select_hypothesis(
        state: AnalystState
    ):

        hypotheses = state.get(
            "hypotheses",
            []
        )

        index = state.get(
            "current_hypothesis_index",
            0
        )

        if index >= len(hypotheses):

            return {}


        return {

            "current_hypothesis":
                hypotheses[index],

            "current_queries": [],

            "current_results": [],

            "investigation_round": 0,

            "tool_rounds": 0,

            "hypothesis_status":
                "INVESTIGATING",

            "needs_more_analysis": False
        }


    # ========================================================
    # V3 - Analyst / Investigation
    # ========================================================

    def analyst_node(
        state: AnalystState
    ):

        question = state["messages"][0].content

        hypothesis = state[
            "current_hypothesis"
        ]

        history = state.get(
            "investigation_history",
            []
        )

        current_queries = state.get(
            "current_queries",
            []
        )

        current_results = state.get(
            "current_results",
            []
        )


        investigation_context = f"""
User question:

{question}

Current hypothesis:

{hypothesis}

Queries already executed for this hypothesis:

{json.dumps(
    current_queries,
    indent=2
)}

Results already obtained for this hypothesis:

{json.dumps(
    current_results,
    indent=2
)}

Previous hypothesis findings:

{json.dumps(
    history,
    indent=2
)}
"""


        system_message = SystemMessage(
            content=(
                ANALYST_SYSTEM_PROMPT
                + "\n\n"
                + investigation_context
            )
        )


        response = llm_with_tools.invoke(
            [
                system_message,
                *state["messages"]
            ]
        )


        return {
            "messages": [response]
        }


    # ========================================================
    # Record SQL results
    # ========================================================

    def record_tool_results(
        state: AnalystState
    ):

        messages = state["messages"]

        if not messages:
            return {}


        # ToolNode can append more than one ToolMessage in a single turn.
        # Locate that most recent tool-call batch and record every SQL result,
        # rather than only the final ToolMessage.
        tool_call_message_index = None

        for index in range(len(messages) - 1, -1, -1):

            message = messages[index]

            if (
                isinstance(message, AIMessage)
                and message.tool_calls
            ):

                tool_call_message_index = index
                break


        if tool_call_message_index is None:
            return {}


        tool_calls = messages[
            tool_call_message_index
        ].tool_calls

        tool_results = {
            message.tool_call_id: message.content
            for message in messages[tool_call_message_index + 1:]
            if isinstance(message, ToolMessage)
        }

        completed_tool_calls = [
            tool_call
            for tool_call in tool_calls
            if tool_call["id"] in tool_results
        ]

        if not completed_tool_calls:
            return {}


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

        current_queries = list(
            state.get(
                "current_queries",
                []
            )
        )

        current_results = list(
            state.get(
                "current_results",
                []
            )
        )


        for tool_call in completed_tool_calls:

            if tool_call["name"] != "run_sql":
                continue

            query = tool_call["args"].get("sql")
            result = tool_results[tool_call["id"]]

            try:
                parsed_result = json.loads(result)
            except (TypeError, json.JSONDecodeError):
                parsed_result = result

            executed_queries.append(query)
            query_results.append(parsed_result)
            current_queries.append(query)
            current_results.append(parsed_result)


        return {

            "executed_queries":
                executed_queries,

            "query_results":
                query_results,

            "current_queries":
                current_queries,

            "current_results":
                current_results,

            "tool_rounds": state.get(
                "tool_rounds",
                0
            ) + 1
        }


    # ========================================================
    # V3 - Evaluate Current Hypothesis
    # ========================================================

    def evaluate_hypothesis(
        state: AnalystState
    ):

        question = state[
            "messages"
        ][0].content

        hypothesis = state[
            "current_hypothesis"
        ]

        queries = state.get(
            "current_queries",
            []
        )

        results = state.get(
            "current_results",
            []
        )


        prompt = EVALUATION_PROMPT.format(

            question=question,

            hypothesis=hypothesis,

            queries=json.dumps(
                queries,
                indent=2
            ),

            results=json.dumps(
                results,
                indent=2
            )
        )


        response = llm.invoke(
            [
                SystemMessage(
                    content=prompt
                )
            ]
        )


        text = response.content


        upper_text = text.upper()


        # -------------------------
        # Parse status
        # -------------------------

        if "STATUS: SUPPORTED" in upper_text:

            status = "SUPPORTED"

        elif "STATUS: REJECTED" in upper_text:

            status = "REJECTED"

        else:

            status = "INCONCLUSIVE"


        # -------------------------
        # Parse whether more
        # analysis is required
        # -------------------------

        needs_more = (
            "NEEDS_MORE_ANALYSIS: YES"
            in upper_text
        )


        # -------------------------
        # Increment investigation
        # round
        # -------------------------

        current_round = (
            state.get(
                "investigation_round",
                0
            )
            + 1
        )


        # Safety limit
        if current_round >= state.get(
            "max_investigation_rounds",
            MAX_INVESTIGATION_ROUNDS
        ):

            needs_more = False


        # The evaluator cannot re-enter investigation once the hard tool
        # budget has been exhausted.  This also guarantees graph termination
        # when the model keeps asking for more queries.
        if state.get(
            "tool_rounds",
            0
        ) >= MAX_TOOL_ROUNDS_PER_HYPOTHESIS:

            needs_more = False


        return {

            "hypothesis_status":
                status,

            "needs_more_analysis":
                needs_more,

            "investigation_round":
                current_round
        }


    # ========================================================
    # V3 - Store completed hypothesis
    # ========================================================

    def advance_hypothesis(
        state: AnalystState
    ):

        history = list(
            state.get(
                "investigation_history",
                []
            )
        )


        history.append({

            "hypothesis":
                state[
                    "current_hypothesis"
                ],

            "status":
                state.get(
                    "hypothesis_status",
                    "INCONCLUSIVE"
                ),

            "queries":
                state.get(
                    "current_queries",
                    []
                ),

            "results":
                state.get(
                    "current_results",
                    []
                )
        })


        next_index = (
            state.get(
                "current_hypothesis_index",
                0
            )
            + 1
        )


        return {

            "investigation_history":
                history,

            "current_hypothesis_index":
                next_index
        }


    # ========================================================
    # V3 - Final analysis
    # ========================================================

    def final_analysis(
        state: AnalystState
    ):

        question = state[
            "messages"
        ][0].content

        history = state.get(
            "investigation_history",
            []
        )


        prompt = FINAL_ANALYSIS_PROMPT.format(

            question=question,

            history=json.dumps(
                history,
                indent=2
            )
        )


        response = llm.invoke(
            [
                SystemMessage(
                    content=prompt
                )
            ]
        )


        conclusion = response.content


        return {

            "messages": [
                AIMessage(
                    content=conclusion
                )
            ],

            "final_conclusion":
                conclusion
        }


    # ========================================================
    # Routing
    # ========================================================

    def route_after_analyst(
        state: AnalystState
    ):

        last_message = (
            state["messages"][-1]
        )


        if (
            isinstance(
                last_message,
                AIMessage
            )
            and last_message.tool_calls
        ):

            return "tools"


        return "evaluate"


    def route_after_evaluation(
        state: AnalystState
    ):

        # Agent decided it needs
        # additional evidence.
        if state.get(
            "needs_more_analysis",
            False
        ):

            return "investigate"


        # Current hypothesis is sufficiently
        # investigated.
        return "advance"


    def route_after_tool_results(
        state: AnalystState
    ):

        # Force an evidence decision after a bounded number of tool turns.
        # Routing here (after ToolNode) ensures every requested tool call has
        # a matching ToolMessage before another LLM call is made.
        if state.get(
            "tool_rounds",
            0
        ) >= MAX_TOOL_ROUNDS_PER_HYPOTHESIS:

            return "evaluate"


        return "analyst"


    def route_after_advance(
        state: AnalystState
    ):

        hypotheses = state.get(
            "hypotheses",
            []
        )

        index = state.get(
            "current_hypothesis_index",
            0
        )


        if index < len(hypotheses):

            return "select"


        return "final"


    # ========================================================
    # Build graph
    # ========================================================

    builder = StateGraph(
        AnalystState
    )


    # -------------------------
    # Nodes
    # -------------------------

    builder.add_node(
        "generate_hypotheses",
        generate_hypotheses
    )

    builder.add_node(
        "select_hypothesis",
        select_hypothesis
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
        "record_tool_results",
        record_tool_results
    )

    builder.add_node(
        "evaluate",
        evaluate_hypothesis
    )

    builder.add_node(
        "advance",
        advance_hypothesis
    )

    builder.add_node(
        "final",
        final_analysis
    )


    # -------------------------
    # Initial flow
    # -------------------------

    builder.add_edge(
        START,
        "generate_hypotheses"
    )

    builder.add_edge(
        "generate_hypotheses",
        "select_hypothesis"
    )

    builder.add_edge(
        "select_hypothesis",
        "analyst"
    )


    # -------------------------
    # Investigation loop
    # -------------------------

    builder.add_conditional_edges(

        "analyst",

        route_after_analyst,

        {

            "tools":
                "tools",

            "evaluate":
                "evaluate"
        }
    )


    builder.add_edge(
        "tools",
        "record_tool_results"
    )


    builder.add_conditional_edges(
        "record_tool_results",
        route_after_tool_results,
        {
            "analyst": "analyst",
            "evaluate": "evaluate"
        }
    )


    # -------------------------
    # Evaluation loop
    # -------------------------

    builder.add_conditional_edges(

        "evaluate",

        route_after_evaluation,

        {

            "investigate":
                "analyst",

            "advance":
                "advance"
        }
    )


    # -------------------------
    # Next hypothesis
    # -------------------------

    builder.add_conditional_edges(

        "advance",

        route_after_advance,

        {

            "select":
                "select_hypothesis",

            "final":
                "final"
        }
    )


    # -------------------------
    # Finish
    # -------------------------

    builder.add_edge(
        "final",
        END
    )


    return builder.compile()
