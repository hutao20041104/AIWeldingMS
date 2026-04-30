from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import datetime

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
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # 动态生成未来14天的参考日历，避免大模型算错时间
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        today_wd = now.weekday()
        calendar_lines = []
        for i in range(14):
            t_date = now + datetime.timedelta(days=i)
            wd = t_date.weekday()
            rel = "今天" if i == 0 else "明天" if i == 1 else "后天" if i == 2 else ""
            days_from_monday = t_date.toordinal() - (now.toordinal() - today_wd)
            week_desc = "本" if 0 <= days_from_monday < 7 else "下" if 7 <= days_from_monday < 14 else "下下"
            calendar_lines.append(f"{t_date.strftime('%Y-%m-%d')}({week_desc}{weekdays[wd]} {rel})")
        calendar_str = ", ".join(calendar_lines)

        sys_msg = f"""您是AI焊接数字化教学管理平台的智能教学助手。您的主要职责是帮助教师排课、解答问题、分析实训等。
【系统时间与日历】：当前系统时间是 {now_str}。为了防止日期计算错误，请严格参考以下系统日历对照表：
{calendar_str}
当用户提到“今天”、“下周五”等相对时间时，请务必直接从上面的参考日历中查找对应的标准日期并使用！
【重要指令】：
1. 成绩查询：遇到询问成绩或表现时，必须调用 `query_grade_tool`。
2. 课程管理：当用户要求创建、排课或删除课程时，必须调用 `manage_course_tool`。如果由于地点不存在等原因工具返回了错误或中止信息，您绝对不能假装创建成功，必须诚实地将错误信息转达给用户，并询问他们是否要换一个地点或重新尝试！
3. 课表查询：当用户询问其课程安排、有没有课等，必须调用 `query_course_tool`，并计算准确的时间范围传入。
绝对不允许捏造任何数据库数据、ID、课程编号或编造工具调用的成功结果！"""
        system_prompt = SystemMessage(content=sys_msg)
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
