from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid
import json
from pathlib import Path

@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    citations: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "citations": self.citations
        }
    
@dataclass
class Conversation:
    id: str
    messages: list[Message] = field(default_factory=list)
    pdf_ids: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

    # add a message to the conversation
    def add_message(self, role: str, content: str, citations: list = None):
        self.messages.append(Message(
            role=role,
            content=content,
            citations=citations or []
        ))

        self.last_active = datetime.now()
    
    # get recent conversation history for prompt
    def get_history(self, max_turns: int = 5) -> list[dict]:
        recent = self.messages[-(max_turns * 2):]
        return [{"role": m.role, "content": m.content} for m in recent]

    # get a brief summary of conversation context
    def get_context_summary(self) -> str:
        if not self.messages:
            return ""
        
        recent = self.messages[-4:]
        summary_parts = []
        for msg in recent:
            prefix = "User asked:" if msg.role == "user" else "You answered:"

            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            summary_parts.append(f"{prefix} {content}")
        
        return "\n".join(summary_parts)
    
    