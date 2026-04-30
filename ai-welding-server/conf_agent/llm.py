from langchain_openai import ChatOpenAI
from .settings import LLM_API_KEY, LLM_BASE_URL, logger

def get_llm():
    logger.debug(f"Initializing LLM with base_url: {LLM_BASE_URL}")
    return ChatOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        model="qwen-turbo-latest",
        temperature=0.0
    )
