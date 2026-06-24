def most_frequent(items: list):
    if not items:
        return None
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return min(counts, key=counts.get)
