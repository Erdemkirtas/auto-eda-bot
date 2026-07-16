"""
backend/agent/agent.py — LangChain ReAct Ajan Kurulumu
======================================================
LLM, sistem promptları ve özel araçlarımızı (Tools) birleştirerek
'AgentExecutor' (Otonom Ajan) oluşturur.
Sohbet hafızası (MemorySaver) ile konuşma bağlamını korur.
"""

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from .llm import get_llm
from .prompts import SYSTEM_MESSAGE

import sys
import os
# tools klasörünü bulabilmek için
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.python_repl import SafePythonREPLTool
from tools.file_io import DataLoadTool

# ---------------------------------------------------------------------------
# Hafıza (Checkpointer) — Oturum bazlı sohbet geçmişi
# ---------------------------------------------------------------------------
memory = MemorySaver()

def create_eda_agent():
    """
    Otonom veri bilimcisi ajanını oluşturur.
    LangGraph create_react_agent fonksiyonunu kullanır.
    MemorySaver ile sohbet geçmişini oturum bazında tutar.
    """
    
    # 1. LLM Motorunu al
    llm = get_llm()
    
    # 2. Araçları tanımla
    tools = [
        DataLoadTool(),
        SafePythonREPLTool()
    ]
    
    # 3. Ajanı oluştur (hafıza ile)
    agent_executor = create_react_agent(
        llm, 
        tools=tools,
        prompt=SYSTEM_MESSAGE,
        checkpointer=memory
    )
    
    return agent_executor
