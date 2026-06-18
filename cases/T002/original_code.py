def count_vowels(text: str) -> int:
    vowels = set('aeiouAEIOU')
    count = 0
    for char in text:
        if char not in vowels:  # BUG
            count += 1
    return count
