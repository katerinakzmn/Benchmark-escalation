def chunk_list(lst: list, size: int) -> list:
    if size <= 0:
        raise ValueError('size должен быть > 0')
    result = []
    for i in range(0, len(lst) - size, size):  # BUG
        result.append(lst[i:i + size])
    return result