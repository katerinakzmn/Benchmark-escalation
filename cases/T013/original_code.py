def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    if not intervals:
        return []
    # интервалы не сортируются — баг при неотсортированном вводе
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last = merged[-1]
        if start < last[1]:  # неверное условие: < вместо <=
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return merged
