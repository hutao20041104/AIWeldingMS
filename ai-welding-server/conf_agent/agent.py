from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .settings import logger
from .llm import get_llm
from .tools import tools

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

def create_agent():
    logger.info("Building the basic agent graph...")
    
    llm = get_llm()
    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    # Nodes
    def call_model(state: AgentState):
        logger.debug("Calling LLM model node...")
        messages = state["messages"]
        system_prompt = SystemMessage(content="您是AI焊接数字化教学管理平台的智能教学助手。您的主要职责是帮助教师生成教案、解答焊接工艺问题、分析学生实训表现等。\n【重要指令】：当用户询问某个学生、班级或专业的成绩、表现或要求分析时，您**必须**调用 `query_grade_tool` 工具获取真实数据。绝对不允许使用您的预训练知识捏造数据，也不能借口无法访问数据库而拒绝查询。请直接调用工具！\n您的回答应该专业、精准，符合工程教育的严谨性。")
        response = llm_with_tools.invoke([system_prompt] + list(messages))
        return {"messages": [response]}

    # Edges
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there is no tool call, then we finish
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            logger.debug("No tool calls. Routing to END.")
            return "end"
        
        logger.debug(f"Tool calls found: {last_message.tool_calls}. Routing to tools.")
        return "continue"

    # Define the graph
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    
    # We only add the tool node if there are tools
    if tools:
        tool_node = ToolNode(tools)
        workflow.add_node("tools", tool_node)
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "continue": "tools",
                "end": END,
            },
        )
        workflow.add_edge("tools", "agent")
    else:
        # Without tools, agent goes directly to END
        workflow.add_edge("agent", END)

    workflow.set_entry_point("agent")
    
    app = workflow.compile()
    logger.info("Agent graph compiled successfully.")
    return app

# The main exported entry point
app = create_agent()

def run_agent(user_input: str):
    """
    Convenience function to test running the agent.
    """
    logger.info(f"Running agent with input: {user_input}")
    
    inputs = {"messages": [HumanMessage(content=user_input)]}
    for output in app.stream(inputs, stream_mode="values"):
        last_message = output["messages"][-1]
        last_message.pretty_print()
        
    logger.info("Agent run finished.")
