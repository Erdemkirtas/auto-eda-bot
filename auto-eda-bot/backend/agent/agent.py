"""
backend/agent/agent.py — LangChain ReAct Ajan Kurulumu
======================================================
LLM, sistem promptları ve özel araçlarımızı (Tools) birleştirerek
'AgentExecutor' (Otonom Ajan) oluşturur.

Kalıcı hafıza: SqliteSaver ile sohbet geçmişi SQLite veritabanında
saklanır — sunucu yeniden başlasa bile geçmiş korunur.
"""

import os
import sqlite3
from langgraph.prebuilt import create_react_agent
from .llm import get_llm
from .prompts import SYSTEM_MESSAGE

import sys
# tools klasörünü bulabilmek için
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.python_repl import SafePythonREPLTool
from tools.file_io import DataLoadTool

from config import settings

# ---------------------------------------------------------------------------
# Kalıcı Hafıza (SQLite Checkpointer)
# ---------------------------------------------------------------------------
# SqliteSaver ile kalıcı hafıza — paket bulunamazsa MemorySaver'a geri dön
try:
    from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore[import-untyped]

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _db_path = os.path.join(
        os.path.dirname(BASE_DIR),  # proje kök dizini
        settings.memory_db_path
    )
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)

    _conn = sqlite3.connect(_db_path, check_same_thread=False)
    memory = SqliteSaver(_conn)
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    print("⚠️  langgraph-checkpoint-sqlite bulunamadı, geçici hafıza (MemorySaver) kullanılıyor.")


def create_eda_agent():
    """
    Otonom veri bilimcisi ajanını oluşturur.
    LangGraph create_react_agent fonksiyonunu kullanır.
    SqliteSaver ile sohbet geçmişini kalıcı olarak SQLite'ta tutar.
    """
    
    # 1. LLM Motorunu al
    llm = get_llm()
    
    # 2. Araçları tanımla
    tools = [
        DataLoadTool(),
        SafePythonREPLTool()
    ]
    
    # 3. Ajanı oluştur (kalıcı hafıza ile)
    agent_executor = create_react_agent(
        llm, 
        tools=tools,
        prompt=SYSTEM_MESSAGE,
        checkpointer=memory
    )
    
    return agent_executor
