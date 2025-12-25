"""
LLM and Embedding Provider Abstraction Layer

Supports multiple backends:
- OpenAI (cloud): Default, requires OPENAI_API_KEY
- Ollama (local): Free, runs locally, no API key needed
- LlamaCPP (local): Direct model loading for offline use

Configuration via environment variables:
- LLM_PROVIDER: "openai" | "ollama" | "llamacpp" (default: "openai")
- EMBEDDING_PROVIDER: "openai" | "local" (default: "openai")
- OLLAMA_BASE_URL: Ollama server URL (default: "http://localhost:11434")
- OLLAMA_MODEL: Model name for Ollama (default: "mistral")
- LOCAL_EMBEDDING_MODEL: HuggingFace model for local embeddings (default: "all-MiniLM-L6-v2")
"""

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


# ============================================================================
# LLM Provider Interface
# ============================================================================

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        """Generate a chat completion response."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (cloud)."""

    def __init__(self):
        self._client = None
        self._api_key = os.environ.get("OPENAI_API_KEY")

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        model = model or "gpt-4o-mini"
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def is_available(self) -> bool:
        return bool(self._api_key)

    @property
    def name(self) -> str:
        return "OpenAI"


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self):
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.default_model = os.environ.get("OLLAMA_MODEL", "mistral")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            # Ollama provides an OpenAI-compatible API
            self._client = OpenAI(
                base_url=f"{self.base_url}/v1",
                api_key="ollama"  # Ollama doesn't need a real key
            )
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        model = model or self.default_model
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        import requests
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    @property
    def name(self) -> str:
        return f"Ollama ({self.default_model})"


class LlamaCppProvider(LLMProvider):
    """LlamaCPP local LLM provider for fully offline use."""

    def __init__(self):
        self.model_path = os.environ.get("LLAMACPP_MODEL_PATH")
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            from llama_cpp import Llama
            if not self.model_path:
                raise ValueError("LLAMACPP_MODEL_PATH environment variable not set")
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=4096,
                n_threads=4,
            )
        return self._llm

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        # Convert messages to prompt format
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
        prompt += "Assistant: "

        response = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["User:", "\n\n"],
        )
        return response["choices"][0]["text"].strip()

    def is_available(self) -> bool:
        return bool(self.model_path) and Path(self.model_path).exists()

    @property
    def name(self) -> str:
        return "LlamaCPP (Local)"


# ============================================================================
# Embedding Provider Interface
# ============================================================================

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings (cloud)."""

    def __init__(self):
        self._client = None
        self._api_key = os.environ.get("OPENAI_API_KEY")
        self.model = "text-embedding-3-small"

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def embed(self, text: str) -> List[float]:
        cleaned = text.strip()
        if not cleaned:
            return []
        response = self.client.embeddings.create(
            model=self.model,
            input=cleaned
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        cleaned = [t.strip() for t in texts if t.strip()]
        if not cleaned:
            return []
        response = self.client.embeddings.create(
            model=self.model,
            input=cleaned
        )
        return [item.embedding for item in response.data]

    def is_available(self) -> bool:
        return bool(self._api_key)

    @property
    def dimension(self) -> int:
        return 1536  # text-embedding-3-small dimension

    @property
    def name(self) -> str:
        return "OpenAI Embeddings"


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embeddings using sentence-transformers (offline)."""

    def __init__(self):
        self.model_name = os.environ.get("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self._model = None
        self._dimension = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            # Cache the dimension
            self._dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed(self, text: str) -> List[float]:
        cleaned = text.strip()
        if not cleaned:
            return []
        embedding = self.model.encode(cleaned, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        cleaned = [t.strip() for t in texts if t.strip()]
        if not cleaned:
            return []
        embeddings = self.model.encode(cleaned, convert_to_numpy=True)
        return embeddings.tolist()

    def is_available(self) -> bool:
        try:
            from sentence_transformers import SentenceTransformer
            return True
        except ImportError:
            return False

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Trigger model loading to get dimension
            _ = self.model
        return self._dimension

    @property
    def name(self) -> str:
        return f"Local ({self.model_name})"


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embeddings (local server)."""

    def __init__(self):
        self.base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        self._dimension = None

    def _get_embedding(self, text: str) -> List[float]:
        import requests
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text}
        )
        response.raise_for_status()
        return response.json()["embedding"]

    def embed(self, text: str) -> List[float]:
        cleaned = text.strip()
        if not cleaned:
            return []
        return self._get_embedding(cleaned)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        cleaned = [t.strip() for t in texts if t.strip()]
        if not cleaned:
            return []
        # Ollama doesn't have batch API, so we call one by one
        return [self._get_embedding(t) for t in cleaned]

    def is_available(self) -> bool:
        import requests
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Get dimension by running a test embedding
            test_embedding = self.embed("test")
            self._dimension = len(test_embedding) if test_embedding else 768
        return self._dimension

    @property
    def name(self) -> str:
        return f"Ollama Embeddings ({self.model})"


# ============================================================================
# Provider Factory
# ============================================================================

_llm_provider: Optional[LLMProvider] = None
_embedding_provider: Optional[EmbeddingProvider] = None


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider (singleton)."""
    global _llm_provider

    if _llm_provider is not None:
        return _llm_provider

    provider_name = os.environ.get("LLM_PROVIDER", "openai").lower()

    if provider_name == "ollama":
        provider = OllamaProvider()
        if provider.is_available():
            _llm_provider = provider
            print(f"✓ Using LLM provider: {provider.name}")
            return _llm_provider
        else:
            print("⚠ Ollama not available, falling back to OpenAI")

    elif provider_name == "llamacpp":
        provider = LlamaCppProvider()
        if provider.is_available():
            _llm_provider = provider
            print(f"✓ Using LLM provider: {provider.name}")
            return _llm_provider
        else:
            print("⚠ LlamaCPP model not found, falling back to OpenAI")

    # Default to OpenAI
    _llm_provider = OpenAIProvider()
    if not _llm_provider.is_available():
        raise RuntimeError(
            "No LLM provider available. Set OPENAI_API_KEY, or configure "
            "LLM_PROVIDER=ollama with Ollama running, or LLM_PROVIDER=llamacpp "
            "with LLAMACPP_MODEL_PATH set."
        )
    print(f"✓ Using LLM provider: {_llm_provider.name}")
    return _llm_provider


def get_embedding_provider() -> EmbeddingProvider:
    """Get the configured embedding provider (singleton)."""
    global _embedding_provider

    if _embedding_provider is not None:
        return _embedding_provider

    provider_name = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()

    if provider_name == "local":
        provider = LocalEmbeddingProvider()
        if provider.is_available():
            _embedding_provider = provider
            print(f"✓ Using embedding provider: {provider.name}")
            return _embedding_provider
        else:
            print("⚠ sentence-transformers not installed, falling back to OpenAI")
            print("  Install with: pip install sentence-transformers")

    elif provider_name == "ollama":
        provider = OllamaEmbeddingProvider()
        if provider.is_available():
            _embedding_provider = provider
            print(f"✓ Using embedding provider: {provider.name}")
            return _embedding_provider
        else:
            print("⚠ Ollama not available, falling back to OpenAI")

    # Default to OpenAI
    _embedding_provider = OpenAIEmbeddingProvider()
    if not _embedding_provider.is_available():
        raise RuntimeError(
            "No embedding provider available. Set OPENAI_API_KEY, or configure "
            "EMBEDDING_PROVIDER=local with sentence-transformers installed, or "
            "EMBEDDING_PROVIDER=ollama with Ollama running."
        )
    print(f"✓ Using embedding provider: {_embedding_provider.name}")
    return _embedding_provider


def reset_providers():
    """Reset provider singletons (useful for testing)."""
    global _llm_provider, _embedding_provider
    _llm_provider = None
    _embedding_provider = None


# ============================================================================
# Convenience Functions (drop-in replacements)
# ============================================================================

def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> str:
    """Generate a chat completion using the configured provider."""
    provider = get_llm_provider()
    return provider.chat_completion(messages, model, temperature, max_tokens)


def get_embedding(text: str) -> List[float]:
    """Get embedding for a single text using the configured provider."""
    provider = get_embedding_provider()
    return provider.embed(text)


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Get embeddings for multiple texts using the configured provider."""
    provider = get_embedding_provider()
    return provider.embed_batch(texts)


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings from the configured provider."""
    provider = get_embedding_provider()
    return provider.dimension
