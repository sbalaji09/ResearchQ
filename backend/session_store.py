import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class Session:
    session_id: str
    pdf_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def add_pdf(self, pdf_id: str):
        if pdf_id not in self.pdf_ids:
            self.pdf_ids.append(pdf_id)
            self.last_active = time.time()

    def remove_pdf(self, pdf_id: str):
        if pdf_id in self.pdf_ids:
            self.pdf_ids.remove(pdf_id)


class SessionStore:
    def __init__(self, session_timeout_hours: int = 24):
        self._sessions: Dict[str, Session] = {}
        self._timeout_seconds = session_timeout_hours * 3600

    def create_session(self) -> Session:
        session_id = uuid.uuid4().hex[:16]
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session:
            # Check if session has expired
            if time.time() - session.last_active > self._timeout_seconds:
                del self._sessions[session_id]
                return None
            session.last_active = time.time()
        return session

    def get_or_create_session(self, session_id: Optional[str]) -> Session:
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        return self.create_session()

    def add_pdf_to_session(self, session_id: str, pdf_id: str) -> bool:
        session = self.get_session(session_id)
        if session:
            session.add_pdf(pdf_id)
            return True
        return False

    def get_session_pdfs(self, session_id: str) -> List[str]:
        session = self.get_session(session_id)
        if session:
            return session.pdf_ids.copy()
        return []

    def delete_session(self, session_id: str) -> Optional[List[str]]:
        """Delete session and return list of pdf_ids that were associated with it."""
        session = self._sessions.pop(session_id, None)
        if session:
            return session.pdf_ids
        return None

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        now = time.time()
        expired = [
            sid for sid, session in self._sessions.items()
            if now - session.last_active > self._timeout_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)


session_store = SessionStore()
