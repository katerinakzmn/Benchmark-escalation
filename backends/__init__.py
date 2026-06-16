from backends.mock_backend import MockBackend
from backends.openai_backend import OpenAIBackend

def get_backend(name: str):
    if name == "mock":
        return MockBackend()
    elif name == "openai":
        return OpenAIBackend()
    else:
        raise ValueError(f"Unknown backend: {name}. Use 'mock' or 'openai'.")