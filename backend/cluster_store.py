import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from threading import Lock


@dataclass
class SavedCluster:
    cluster_id: str
    name: str
    pdf_ids: List[str]
    topics: List[str] = field(default_factory=list)
    method: str = "hierarchical"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SavedCluster":
        return cls(**data)


@dataclass
class ClusteringSession:
    """A saved clustering session with multiple clusters."""
    session_id: str
    name: str
    method: str
    clusters: List[SavedCluster]
    total_papers: int
    outliers: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "method": self.method,
            "clusters": [c.to_dict() for c in self.clusters],
            "total_papers": self.total_papers,
            "outliers": self.outliers,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClusteringSession":
        clusters = [SavedCluster.from_dict(c) for c in data.get("clusters", [])]
        return cls(
            session_id=data["session_id"],
            name=data["name"],
            method=data["method"],
            clusters=clusters,
            total_papers=data["total_papers"],
            outliers=data.get("outliers", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


class ClusterStore:
    """
    JSON-based storage for saved clustering results.
    Allows users to save, name, and revisit clustering sessions.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path(__file__).parent / "data" / "clusters.json"

        self._storage_path = storage_path
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._sessions: Dict[str, ClusteringSession] = {}
        self._load()

    def _load(self) -> None:
        """Load sessions from JSON file."""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, "r") as f:
                    data = json.load(f)
                    self._sessions = {
                        sid: ClusteringSession.from_dict(session)
                        for sid, session in data.items()
                    }
            except (json.JSONDecodeError, KeyError):
                self._sessions = {}

    def _save(self) -> None:
        """Save sessions to JSON file."""
        with open(self._storage_path, "w") as f:
            data = {sid: session.to_dict() for sid, session in self._sessions.items()}
            json.dump(data, f, indent=2)

    def save_clustering_result(
        self,
        name: str,
        method: str,
        clusters: List[Dict[str, Any]],
        total_papers: int,
        outliers: Optional[List[str]] = None,
    ) -> ClusteringSession:
        """Save a clustering result as a new session."""
        with self._lock:
            session_id = str(uuid.uuid4())

            saved_clusters = []
            for i, cluster_data in enumerate(clusters):
                saved_cluster = SavedCluster(
                    cluster_id=str(uuid.uuid4()),
                    name=f"Cluster {i + 1}",
                    pdf_ids=cluster_data.get("papers", []),
                    topics=cluster_data.get("topics", []),
                    method=method,
                )
                saved_clusters.append(saved_cluster)

            session = ClusteringSession(
                session_id=session_id,
                name=name,
                method=method,
                clusters=saved_clusters,
                total_papers=total_papers,
                outliers=outliers or [],
            )

            self._sessions[session_id] = session
            self._save()
            return session

    def get_session(self, session_id: str) -> Optional[ClusteringSession]:
        """Get a clustering session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def rename_session(self, session_id: str, new_name: str) -> Optional[ClusteringSession]:
        """Rename a clustering session."""
        with self._lock:
            if session_id not in self._sessions:
                return None

            self._sessions[session_id].name = new_name
            self._save()
            return self._sessions[session_id]

    def rename_cluster(
        self, session_id: str, cluster_id: str, new_name: str
    ) -> Optional[SavedCluster]:
        """Rename a cluster within a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            for cluster in session.clusters:
                if cluster.cluster_id == cluster_id:
                    cluster.name = new_name
                    cluster.updated_at = datetime.now(timezone.utc).isoformat()
                    self._save()
                    return cluster

            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a clustering session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self._save()
                return True
            return False

    def list_sessions(self) -> List[ClusteringSession]:
        """List all saved clustering sessions."""
        with self._lock:
            return sorted(
                self._sessions.values(),
                key=lambda s: s.created_at,
                reverse=True,
            )

    def clear(self) -> None:
        """Clear all saved sessions."""
        with self._lock:
            self._sessions = {}
            self._save()


# Singleton instance
cluster_store = ClusterStore()
