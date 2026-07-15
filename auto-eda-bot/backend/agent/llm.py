"""
backend/agent/llm.py — LLM Bağlantı Yöneticisi
================================================
Tamamen yerel cihazda çalışan LLM'e (Foundry Local, Ollama vb.)
LangChain üzerinden bağlantı sağlar. İnternet kullanmaz.
"""

import os
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

def get_llm() -> BaseChatModel:
    """
    Yerel ağda/cihazda çalışan LLM modeline bağlantı kurar.
    
    Not: Microsoft Foundry Local SDK veya Ollama gibi çoğu yerel sistem
    OpenAI uyumlu bir REST API sunar. Biz de LangChain'in standart ChatOpenAI
    sınıfını kullanarak yerel URL'ye istek atıyoruz.
    """
    
    # .env'den ayarları çek veya varsayılanları kullan
    # Örnek: Ollama için "http://localhost:11434/v1", Foundry için ilgili yerel port
    local_api_base = os.getenv("LOCAL_LLM_API_BASE", "http://localhost:11434/v1")
    model_name = os.getenv("LOCAL_LLM_MODEL", "llama3") # Varsayılan model adı
    
    # Sıcaklık 0'a yakın tutulur ki ajan kod yazarken (Python REPL)
    # yaratıcılık yapmak yerine kesin ve tutarlı kodlar üretsin.
    temperature = float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.0"))

    # İnternete gitmesini engellemek ve yerel API'ye zorlamak için:
    # api_key="local" olarak sahte bir key verilir.
    llm = ChatOpenAI(
        openai_api_base=local_api_base,
        openai_api_key="local-offline-key",
        model_name=model_name,
        temperature=temperature,
        max_tokens=2048
    )
    
    return llm
