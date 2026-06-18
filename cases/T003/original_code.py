# T003 original buggy code

def is_palindrome(s: str) -> bool:
    return s == s[::-1]  # BUG
