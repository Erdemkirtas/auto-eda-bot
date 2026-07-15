"""
backend/agent/callbacks.py — Ajan Düşünce Adımları Takipçisi
=============================================================
AgentExecutor'un her adımını (düşünme, araç çağırma, sonuç) yakalayarak
kullanıcıya canlı ilerleme gösterimi sağlar.
"""

from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List, Optional
from uuid import UUID


class ThinkingStepsCallback(BaseCallbackHandler):
    """
    Ajanın düşünce sürecini adım adım kaydeder.
    Bu adımlar Frontend'e gönderilebilir.
    """

    def __init__(self) -> None:
        super().__init__()
        self.steps: List[Dict[str, str]] = []
        self.generated_code: List[str] = []

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        """Ajan bir araç çağırdığında tetiklenir."""
        tool_name = getattr(action, "tool", "bilinmeyen_araç")
        tool_input = getattr(action, "tool_input", "")

        if tool_name == "python_repl":
            self.steps.append({
                "type": "code",
                "status": "💻 Python kodu çalıştırılıyor...",
                "detail": str(tool_input)[:200]
            })
            self.generated_code.append(str(tool_input))
        elif tool_name == "load_data":
            self.steps.append({
                "type": "data",
                "status": "📂 Veri dosyası okunuyor...",
                "detail": str(tool_input)[:200]
            })
        else:
            self.steps.append({
                "type": "tool",
                "status": f"🔧 Araç çağrılıyor: {tool_name}",
                "detail": str(tool_input)[:200]
            })

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Araç çalışması bittiğinde tetiklenir."""
        self.steps.append({
            "type": "result",
            "status": "✅ Sonuç alındı",
            "detail": str(output)[:300]
        })

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        """Ajan işini bitirdiğinde tetiklenir."""
        self.steps.append({
            "type": "done",
            "status": "🎯 Analiz tamamlandı",
            "detail": ""
        })

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """LLM hata verdiğinde tetiklenir."""
        self.steps.append({
            "type": "error",
            "status": "⚠️ LLM hatası",
            "detail": str(error)[:200]
        })

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Araç hata verdiğinde tetiklenir."""
        self.steps.append({
            "type": "error",
            "status": "🔄 Hata alındı, düzeltiliyor...",
            "detail": str(error)[:200]
        })

    def get_steps(self) -> List[Dict[str, str]]:
        """Tüm adımları döndürür."""
        return self.steps

    def get_generated_code(self) -> List[str]:
        """Çalıştırılan tüm kodları döndürür."""
        return self.generated_code

    def reset(self) -> None:
        """Adımları sıfırlar."""
        self.steps = []
        self.generated_code = []
