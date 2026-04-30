import json
from ninja import Router, Schema
from django.http import StreamingHttpResponse
from core.auth import JWTAuth
from apps.users.models import Teacher, TeacherChatSession, TeacherChatMessage
from conf_agent.agent import app as agent_app
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk

assistant_router = Router(tags=["AI Assistant"])

def _get_teacher(auth) -> Teacher:
    if auth.role != "teacher":
        return None
    return Teacher.objects.filter(user_id=auth.id).first()

class SessionOut(Schema):
    id: str
    title: str
    created_at: str

class MessageOut(Schema):
    id: str
    role: str
    content: str
    created_at: str

class ChatRequest(Schema):
    message: str

@assistant_router.get("/sessions/", auth=JWTAuth(), response=list[SessionOut])
def list_sessions(request):
    teacher = _get_teacher(request.auth)
    if not teacher:
        return []
    
    sessions = TeacherChatSession.objects.filter(teacher=teacher)
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "created_at": s.created_at.isoformat()
        } for s in sessions
    ]

@assistant_router.post("/sessions/", auth=JWTAuth(), response=SessionOut)
def create_session(request):
    teacher = _get_teacher(request.auth)
    session = TeacherChatSession.objects.create(teacher=teacher, title="新会话")
    return {
        "id": str(session.id),
        "title": session.title,
        "created_at": session.created_at.isoformat()
    }

@assistant_router.get("/sessions/{session_id}/messages/", auth=JWTAuth(), response=list[MessageOut])
def list_messages(request, session_id: str):
    teacher = _get_teacher(request.auth)
    session = TeacherChatSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        return []
    
    msgs = TeacherChatMessage.objects.filter(session=session)
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        } for m in msgs
    ]

@assistant_router.post("/sessions/{session_id}/chat/", auth=JWTAuth())
def chat_stream(request, session_id: str, payload: ChatRequest):
    teacher = _get_teacher(request.auth)
    session = TeacherChatSession.objects.filter(id=session_id, teacher=teacher).first()
    if not session:
        return {"message": "Session not found"}, 404

    # Save user message
    user_msg_text = payload.message
    TeacherChatMessage.objects.create(session=session, role="user", content=user_msg_text)

    # Rename session if it's the first message
    if TeacherChatMessage.objects.filter(session=session).count() == 1:
        session.title = user_msg_text[:10] + ("..." if len(user_msg_text) > 10 else "")
        session.save()

    # Load history for the agent
    history_msgs = TeacherChatMessage.objects.filter(session=session).order_by("created_at")
    langchain_messages = []
    for m in history_msgs:
        if m.role == "user":
            langchain_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            langchain_messages.append(AIMessage(content=m.content))
            
    inputs = {"messages": langchain_messages}

    def event_stream():
        full_response = ""
        # stream_mode="messages" yields chunks of messages as they are generated
        try:
            for msg_chunk, metadata in agent_app.stream(inputs, stream_mode="messages"):
                # Capture Tool Calls
                if hasattr(msg_chunk, "tool_call_chunks") and msg_chunk.tool_call_chunks:
                    for tc in msg_chunk.tool_call_chunks:
                        if tc.get("name"):
                            tool_name = tc.get("name")
                            display_name = "学生成绩查询" if tool_name == "query_grade_tool" else tool_name
                            yield f"data: {json.dumps({'tool_call': f'\n> 🔧 正在调用系统工具：{display_name}...\n\n'})}\n\n"
                            
                # We only care about AIMessages from the assistant node
                if isinstance(msg_chunk, AIMessageChunk) and msg_chunk.content:
                    chunk_text = msg_chunk.content
                    if isinstance(chunk_text, str):
                        full_response += chunk_text
                        # SSE format
                        yield f"data: {json.dumps({'content': chunk_text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # End of stream
            yield "data: [DONE]\n\n"
            # Save assistant message to DB
            if full_response:
                TeacherChatMessage.objects.create(session=session, role="assistant", content=full_response)

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
