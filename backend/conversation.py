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
    
class ConversationStore:
    def __init__(self, persist_path: Path = None):
        self._conversations: dict[str, Conversation] = {}
        self._persist_path = persist_path

        if persist_path and persist_path.exists():
            self._load()
    
    # create a new conversation
    def create(self, pdf_ids: list[str] = None) -> Conversation:
        conv_id = str(uuid.uuid4())[:8]
        conversation = Conversation(
            id=conv_id,
            pdf_ids=pdf_ids or []
        )
        self._conversations[conv_id] = conversation
        self._save()
        return conversation
    
    # get a conversation by ID
    def get(self, conversation_id: str) -> Optional[Conversation]:
        return self._conversations.get(conversation_id)
    
    # get existing conversations or create new one
    def get_or_create(self, conversation_id: str = None, pdf_ids: list[str] = None) -> Conversation:
        if conversation_id and conversation_id in self._conversations:
            conv = self._conversations[conversation_id]
            if pdf_ids:
                conv.pdf_ids = pdf_ids
            return conv
        return self.create(pdf_ids)
    
    # delete a conversation
    def delete(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            self._save()
            return True
        return False
    
    # list all conversations
    def list_all(self) -> list[dict]:
        return [
            {
                "id": conv.id,
                "message_count": len(conv.messages),
                "created_at": conv.created_at.isoformat(),
                "last_active": conv.last_active.isoformat(),
            }
            for conv in self._conversations.values()
        ]
    
    # remove conversations older than max_age_hours
    def cleanup_old(self, max_age_hours: int = 24):
        now = datetime.now()
        to_delete = []
        for conv_id, conv in self._conversations.items():
            age = (now - conv.last_active).total_seconds() / 3600
            if age > max_age_hours:
                to_delete.append(conv_id)
        
        for conv_id in to_delete:
            del self._conversations[conv_id]
        
        if to_delete:
            self._save()
        
        return len(to_delete)
    
    # persist conversations to file
    def _save(self):
        if not self._persist_path:
            return
        pass
    
    # load conversations from file
    def _load(self):
        if not self._persist_path:
            return
        pass
    
    