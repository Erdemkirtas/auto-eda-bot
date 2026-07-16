"""
backend/agent/llm.py — LLM Bağlantı Yöneticisi
================================================
Tamamen yerel cihazda çalışan LLM'e (Foundry Local, Ollama vb.)
LangChain üzerinden bağlantı sağlar. İnternet kullanmaz.

Konfigürasyon: backend/config.py (Pydantic Settings) üzerinden yönetilir.
"""

from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from config import settings


def get_llm() -> BaseChatModel:
    """
    Yerel ağda/cihazda çalışan LLM modeline bağlantı kurar.
    
    Tüm ayarlar merkezi config.py'den (pydantic-settings) gelir.
    """

    llm = ChatOpenAI(
        openai_api_base=settings.local_llm_api_base,
        openai_api_key="local-offline-key",
        model_name=settings.local_llm_model,
        temperature=settings.local_llm_temperature,
        max_tokens=2048
    )
    
    return llm
