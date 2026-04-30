import json
from langchain_core.tools import tool
from apps.courses.models import CourseGrade
from apps.users.models import Student
from conf_agent.prompts.grade_prompt import get_grade_analysis_prompt
from conf_agent.settings import logger

@tool
def query_grade_tool(query_type: str, query_value: str, course_code: str = "") -> str:
    """
    查询学生成绩的工具。
    当用户询问某个班级或专业的成绩时，query_type 填 "class"，query_value 填班级名（如"机电1班"）。
    当用户询问某个学生的成绩时，query_type 填 "student"，query_value 填学生名（如"张三"）。
    如果用户指定了课程编号，可以填入 course_code。
    此工具将返回数据库中的原始成绩数据，并附带一条指导如何进行分析的指令给语言模型。
    """
    logger.info(f"Using query_grade_tool: type={query_type}, value={query_value}, course={course_code}")
    
    # 因为 LangGraph agent 在 Django 上下文中运行，可以直接使用 ORM
    queryset = CourseGrade.objects.all().select_related("student__user", "course")
    
    if course_code:
        queryset = queryset.filter(course__course_code__icontains=course_code)
        
    if query_type == "class":
        # 模糊匹配班级名
        queryset = queryset.filter(student__class_name__icontains=query_value)
    elif query_type == "student":
        # 模糊匹配学生名
        queryset = queryset.filter(student__user__username__icontains=query_value)
    else:
        return "无法识别的 query_type，必须是 'class' 或 'student'。"
        
    # 执行查询并格式化
    records = list(queryset)
    if not records:
        raw_data_str = "未查询到相关的成绩数据。"
    else:
        data_list = []
        for r in records:
            data_list.append({
                "student_name": r.student.user.username,
                "class_name": r.student.class_name,
                "course_code": r.course.course_code,
                "ai_score": r.ai_score,
                "teacher_score": r.teacher_score,
                "final_score": r.final_score
            })
        raw_data_str = json.dumps(data_list, ensure_ascii=False, indent=2)
        
    # 返回的内容不仅包括数据，还包括如何分析的指令
    return get_grade_analysis_prompt(query_type, query_value, raw_data_str)
