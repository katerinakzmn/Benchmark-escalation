# T013 original buggy code

def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    if not intervals:
        return []
    merged = [intervals[0]]  # BUG: нет sorted(intervals)
    for start, end in intervals[1:]:
        last = merged[-1]
        if start <= last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return merged
