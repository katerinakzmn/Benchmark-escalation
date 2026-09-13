"""Backend registry for benchmark runners."""

from backends.llm_backends import GeminiBackend, OpenAIBackend, MockBackend, PolzaBackend


def get_backend(name: str):
    backends = {
        "mock":   MockBackend,
        "openai": OpenAIBackend,
        "gemini": GeminiBackend,
        "polza":  PolzaBackend,  # Polza.ai — OpenAI-совместимый, оплата в рублях
    }
    try:
        return backends[name]()
    except KeyError as exc:
        raise ValueError(
            f"Unknown backend: {name!r}. "
            f"Допустимые значения: 'mock', 'openai', 'gemini', 'polza'."
        ) from exc