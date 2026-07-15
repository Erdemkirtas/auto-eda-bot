"""
backend/agent/agent.py — LangChain ReAct Ajan Kurulumu
======================================================
LLM, sistem promptları ve özel araçlarımızı (Tools) birleştirerek
'AgentExecutor' (Otonom Ajan) oluşturur.
"""

from langgraph.prebuilt import create_react_agent
from .llm import get_llm
from .prompts import SYSTEM_MESSAGE

import sys
import os
# tools klasörünü bulabilmek için
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.python_repl import SafePythonREPLTool
from tools.file_io import DataLoadTool

def create_eda_agent():
    """
    Otonom veri bilimcisi ajanını oluşturur.
    LangGraph create_react_agent fonksiyonunu kullanır.
    """
    
    # 1. LLM Motorunu al
    llm = get_llm()
    
    # 2. Araçları tanımla
    tools = [
        DataLoadTool(),
        SafePythonREPLTool()
    ]
    
    # 3. Ajanı oluştur
    agent_executor = create_react_agent(
        llm, 
        tools=tools,
        prompt=SYSTEM_MESSAGE
    )
    
    return agent_executor
