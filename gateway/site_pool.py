"""
站点池：管理可用的生图站点，支持轮询、失败降级
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class Site:
    url: str
    name: str = ""
    fail_count: int = 0
    last_fail: datetime = field(default_factory=lambda: datetime.min)
    in_use: bool = False

    def is_available(self) -> bool:
        if self.in_use:
            return False
        # 失败超过 3 次，冷却 10 分钟
        if self.fail_count >= 3:
            return datetime.now() - self.last_fail > timedelta(minutes=10)
        return True

    def mark_fail(self):
        self.fail_count += 1
        self.last_fail = datetime.now()

    def mark_success(self):
        self.fail_count = 0


class SitePool:
    def __init__(self):
        self._sites: list[Site] = []
        self._lock = asyncio.Lock()
        self._index = 0

    def add(self, url: str, name: str = ""):
        self._sites.append(Site(url=url, name=name))

    async def acquire(self) -> Site | None:
        async with self._lock:
            available = [s for s in self._sites if s.is_available()]
            if not available:
                return None
            site = available[self._index % len(available)]
            self._index += 1
            site.in_use = True
            return site

    async def release(self, site: Site, success: bool):
        async with self._lock:
            site.in_use = False
            if success:
                site.mark_success()
            else:
                site.mark_fail()

    def status(self) -> list[dict]:
        return [{
            "url": s.url,
            "name": s.name,
            "available": s.is_available(),
            "fail_count": s.fail_count,
            "in_use": s.in_use,
        } for s in self._sites]
