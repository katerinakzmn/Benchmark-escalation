"""Backend registry for benchmark runners."""

from backends.llm_backends import GeminiBackend, OpenAIBackend
from backends.mock_backend import MockBackend


def get_backend(name: str):
    backends = {
        "mock": MockBackend,
        "openai": OpenAIBackend,
        "gemini": GeminiBackend,
    }
    try:
        return backends[name]()
    except KeyError as exc:
        raise ValueError(
            f"Unknown backend: {name}. Use 'mock', 'openai', or 'gemini'."
        ) from exc