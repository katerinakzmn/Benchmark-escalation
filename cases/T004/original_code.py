# T004 — original buggy code

def reverse_words(text: str) -> str:
    words = text.split()
    return ' '.join(words)  # BUG
