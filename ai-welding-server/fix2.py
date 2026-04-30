with open('apps/users/assistant_api.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_str = '''                            display_name = "学生成绩查询" if tool_name == "query_grade_tool" else tool_name'''

new_str = '''                            if tool_name == "query_grade_tool":
                                display_name = "学生成绩查询"
                            elif tool_name == "manage_course_tool":
                                display_name = "课程管理"
                            elif tool_name == "query_course_tool":
                                display_name = "课表查询"
                            else:
                                display_name = tool_name'''

content = content.replace(old_str, new_str)

with open('apps/users/assistant_api.py', 'w', encoding='utf-8') as f:
    f.write(content)
