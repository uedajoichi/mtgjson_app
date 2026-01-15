import time
from typing import Callable


def retry(func: Callable, times: int = 3, delay: float = 0.5):
    for i in range(times):
        try:
            return func()
        except Exception:
            if i == times - 1:
                raise
            time.sleep(delay)
