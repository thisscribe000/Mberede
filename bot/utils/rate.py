import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict

from core.config import config


class RateLimiter:
    def __init__(self):
        self._attempts: Dict[int, list] = defaultdict(list)

    def record_attempt(self, user_id: int):
        self._attempts[user_id].append(datetime.utcnow())

    def get_attempts(self, user_id: int) -> int:
        cutoff = datetime.utcnow() - timedelta(minutes=15)
        self._attempts[user_id] = [
            t for t in self._attempts[user_id] if t > cutoff
        ]
        return len(self._attempts[user_id])

    def is_locked(self, user_id: int) -> bool:
        return self.get_attempts(user_id) >= config.max_pin_attempts

    def clear(self, user_id: int):
        self._attempts[user_id] = []

    def wait_time(self, user_id: int) -> int:
        attempts = self.get_attempts(user_id)
        if attempts > 0:
            return min(attempts * config.progressive_delay_seconds, 30)
        return 0


from collections import defaultdict
rate_limiter = RateLimiter()
