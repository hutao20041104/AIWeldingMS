def get_grade_analysis_prompt(query_type: str, query_value: str, raw_data_str: str) -> str:
    """
    Returns a prompt string instructing the LLM on how to analyze the grade data.
    """
    target = f"班级/专业【{query_value}】" if query_type == "class" else f"学生【{query_value}】"
    
    prompt = f"""您刚刚查询了 {target} 的成绩数据。
以下是数据库返回的原始数据内容：

<RAW_DATA>
{raw_data_str}
</RAW_DATA>

请您作为 AI 焊接数字化教学管理平台的智能教学助手，对上述成绩数据进行专业分析。
请遵循以下分析指南：
1. 如果 RAW_DATA 为空或提示未找到数据，请礼貌地告知用户没有找到相关成绩记录。
2. 提炼核心指标：计算并展示平均分、最高分、最低分（如果是班级查询）。
3. 发现规律与问题：
   - AI评分与教师评分是否存在显著差异？
   - 整体表现处于什么水平（优秀、良好、待提升）？
4. 给出教学建议：根据成绩分布，给教师或学生提供建设性的改进建议（比如加强某项实训、关注个别落后学生等）。

请以自然、专业、易读的格式（可以使用 Markdown 表格和列表）输出您的分析报告。
【极其重要的格式要求】：
- 你的标题必须极为干净，例如："# 张三 实训成绩分析报告"。
- **绝对禁止**在报告的任何地方（包括标题、正文、注释）出现“基于数据库原始数据”、“RAW_DATA”、“由于您提供了数据”等暴露系统内部查询过程的字眼。
- 请直接以专家助手的口吻给出结论，不要解释你的数据来源。
"""
    return prompt
