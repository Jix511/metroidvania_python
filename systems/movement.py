"""Frame-rate independent movement helpers."""


def approach(current, target, amount):
    amount = max(0.0, float(amount))
    if current < target:
        return min(target, current + amount)
    if current > target:
        return max(target, current - amount)
    return target
