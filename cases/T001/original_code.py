def sum_positive(numbers: list[int]) -> int:
    total = 0
    for i in range(len(numbers) - 1):
        if numbers[i] > 0:
            total += numbers[i]
    return total
