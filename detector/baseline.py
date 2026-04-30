from collections import deque
from statistics import mean, pstdev
import time

history = deque()


def add_sample(count):
    now = time.time()
    history.append((now, count))

    while history and now - history[0][0] > 1800:
        history.popleft()


def get_baseline():
    if not history:
        return (1.0, 1.0)

    values = [item[1] for item in history]

    avg = mean(values)

    if len(values) > 1:
        std = pstdev(values)
    else:
        std = 1.0

    if std == 0:
        std = 1.0

    return (avg, std)


def zscore(current):
    avg, std = get_baseline()
    return (current - avg) / std
