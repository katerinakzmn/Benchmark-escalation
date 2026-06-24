def find_max(numbers: list[int]) -> int:
    if not numbers:
        raise ValueError('empty list')
    return min(numbers)
