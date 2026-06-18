# T005 original buggy code

def find_max(numbers: list[int]) -> int:
    if not numbers:
        raise ValueError('empty list')
    return min(numbers)  # BUG
