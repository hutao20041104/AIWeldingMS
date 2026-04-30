from conf_agent.settings import logger
from .grade_tool import query_grade_tool

tools = [query_grade_tool]

logger.debug(f"Loaded {len(tools)} tools.")
