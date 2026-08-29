"""
src/memory.py — LawAgent AI Konuşma Hafızası (Session Memory)
============================================================
Oturum bazlı konuşma geçmişini ve son sorgudan dönen chunk'ları tutar.
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List


class ConversationMemory:
    def __init__(self, max_memory: int = 4):
        self.memory: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.last_chunks: Dict[str, List[Dict]] = defaultdict(list)
        self.max_memory = max_memory

    def add_exchange(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        if session_id not in self.memory:
            self.memory[session_id] = []
        self.memory[session_id].append(
            {
                "role": "user",
                "content": user_msg,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self.memory[session_id].append(
            {
                "role": "assistant",
                "content": assistant_msg,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.memory[session_id]) > self.max_memory * 2:
            self.memory[session_id] = self.memory[session_id][-(self.max_memory * 2):]

    def save_chunks(self, session_id: str, chunks: List[Dict]) -> None:
        self.last_chunks[session_id] = chunks

    def get_chunks(self, session_id: str) -> List[Dict]:
        return self.last_chunks.get(session_id, [])

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.memory.get(session_id, [])

    def get_context_string(self, session_id: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return ""
        context_lines = ["--- ÖNCEKI BAĞLAM ---"]
        for msg in history[-4:]:
            role = "Kullanıcı" if msg["role"] == "user" else "Asistan"
            context_lines.append(f"{role}: {msg['content'][:300]}")
        return "\n".join(context_lines) + "\n\n"
