from conf_agent.settings import logger
from .grade_tool import query_grade_tool
from .course_tool import manage_course_tool, query_course_tool

tools = [query_grade_tool, manage_course_tool, query_course_tool]

logger.debug(f"Loaded {len(tools)} tools.")
