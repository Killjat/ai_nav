"""
115.190.169.243 完整 API 客户端
支持：文生图、即梦视频、Veo视频、Wan视频、文本转语音
额度耗尽自动注册新账号
"""
import asyncio
import httpx
import json
import os
import re
import time
from playwright.async_api import async_playwright

BASE = "https://115.190.169.243"
ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "..", "accounts.json")
COOKIES_DIR   = os.path.join(os.path.dirname(__file__), "..", "generated", "accounts")

# 额度耗尽的关键词
QUOTA_EXHAUSTED = ["额度不足", "余额不足", "积分不足", "次数已用完",
                   "quota", "insufficient", "limit exceeded", "no credits",
                   "积分不足", "Insufficient points"]

# 积分消耗估算（用于提前判断是否需要换号）
COST_MAP = {
    "/api.php_tts":        25,
    "/api.php_text-to-image": 10,
    "/api_video.php":      100,
    "/api_veo.php":        150,
    "/api_wan.php":        80,
}


def _load_cookies(url: str) -> dict:
    slug = url.replace("https://", "").replace("http://", "").replace("/", "_")
    path = os.path.join(COOKIES_DIR, f"{slug}_cookies.json")
    if os.path.exists(path):
        with open(path) as f:
            return {c["name"]: c["value"] for c in json.load(f)}
    return {}


def _is_quota_error(text: str) -> bool:
    return any(kw in text.lower() for kw in QUOTA_EXHAUSTED)


async def _auto_register_and_login() -> dict:
    """自动注册新账号并返回 cookies"""
    from account_manager import ensure_logged_in
    cookies_list = await ensure_logged_in(BASE)
    return {c["name"]: c["value"] for c in cookies_list}


class SiteClient:
    def __init__(self):
        self._cookies: dict = {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._cookies = _load_cookies(BASE)
        self._client = httpx.AsyncClient(
            base_url=BASE,
            cookies=self._cookies,
            verify=False,
            timeout=120,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
                "Referer": BASE + "/",
            }
        )
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()

    async def _post(self, endpoint: str, data: dict, retry: bool = True) -> dict:
        """发送请求，自动处理额度耗尽"""
        r = await self._client.post(endpoint, data=data)
        text = r.text

        # 检查是否需要重新登录
        if r.status_code in (401, 403) or "login" in text.lower() or "Unauthorized" in text:
            print("  session 失效，重新登录...")
            new_cookies = await _auto_register_and_login()
            # 重建 client 注入新 cookie
            await self._client.aclose()
            self._cookies = new_cookies
            self._client = httpx.AsyncClient(
                base_url=BASE, cookies=self._cookies, verify=False, timeout=120,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
                    "Referer": BASE + "/",
                }
            )
            r = await self._client.post(endpoint, data=data)
            text = r.text

        # 检查额度
        if _is_quota_error(text) and retry:
            print("  额度耗尽，切换账号...")
            # 标记当前账号耗尽
            from account_manager import mark_exhausted, get_account
            current = get_account(BASE)
            if current:
                mark_exhausted(BASE, current.get("username", ""))
            new_cookies = await _auto_register_and_login()
            await self._client.aclose()
            self._cookies = new_cookies
            self._client = httpx.AsyncClient(
                base_url=BASE, cookies=self._cookies, verify=False, timeout=120,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
                    "Referer": BASE + "/",
                }
            )
            return await self._post(endpoint, data, retry=False)

        try:
            return r.json()
        except Exception:
            return {"raw": text, "status": r.status_code}

    async def _poll_task(self, endpoint: str, task_id: str,
                         interval: int = 3, timeout: int = 300) -> dict:
        """轮询任务状态直到完成"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            await asyncio.sleep(interval)
            r = await self._client.post(endpoint, data={
                "action": "get_task", "task_id": task_id
            })
            try:
                data = r.json()
            except Exception:
                continue

            status = data.get("status", "")
            print(f"  任务状态: {status}")

            if status in ("completed", "succeed", "success", "done", "finished"):
                return data
            if status in ("failed", "error"):
                return {"error": data.get("message", "任务失败"), "data": data}

        return {"error": "超时"}

    # ── 文生图 ────────────────────────────────────────────
    async def text_to_image(self, prompt: str, size: str = "1024x1024",
                             model: str = "doubao_image", count: int = 1) -> dict:
        print(f"[文生图] {prompt[:40]}...")
        return await self._post("/api.php", {
            "model": model,
            "type": "text-to-image",
            "size": size,
            "count": str(count),
            "prompt": prompt,
        })

    # ── 即梦视频 ──────────────────────────────────────────
    async def jimeng_video(self, prompt: str, duration: int = 5,
                            aspect_ratio: str = "16:9") -> dict:
        print(f"[即梦视频] {prompt[:40]}...")
        resp = await self._post("/api_video.php", {
            "action": "create_task",
            "model": "doubao-seedance-1-5-pro-251215",
            "type": "text-to-video",
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
        })
        task_id = resp.get("task_id") or resp.get("data", {}).get("task_id")
        if not task_id:
            return resp
        print(f"  task_id: {task_id}，开始轮询...")
        return await self._poll_task("/api_video.php", task_id)

    # ── Veo 视频 ──────────────────────────────────────────
    async def veo_video(self, prompt: str, aspect_ratio: str = "16:9",
                         model: str = "veo3.1") -> dict:
        print(f"[Veo视频] {prompt[:40]}...")
        resp = await self._post("/api_veo.php", {
            "action": "create_task",
            "model": model,
            "type": "text-to-video",
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "enhance_prompt": "0",
            "enable_upsample": "0",
        })
        task_id = resp.get("task_id") or resp.get("data", {}).get("task_id")
        if not task_id:
            return resp
        print(f"  task_id: {task_id}，开始轮询...")
        return await self._poll_task("/api_veo.php", task_id)

    # ── Wan 视频 ──────────────────────────────────────────
    async def wan_video(self, prompt: str, duration: int = 5,
                         aspect_ratio: str = "16:9", model: str = "wan2.6") -> dict:
        print(f"[Wan视频] {prompt[:40]}...")
        resp = await self._post("/api_wan.php", {
            "action": "create_task",
            "type": "text-to-video",
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": str(duration),
        })
        task_id = resp.get("task_id") or resp.get("data", {}).get("task_id")
        if not task_id:
            return resp
        print(f"  task_id: {task_id}，开始轮询...")
        return await self._poll_task("/api_wan.php", task_id)

    # ── 文本转语音 ────────────────────────────────────────
    async def text_to_speech(self, text: str, voice: str = "tongtong") -> dict:
        print(f"[文本转语音] {text[:40]}...")
        return await self._post("/api.php", {
            "action": "tts",
            "text": text,
            "voice": voice,
        })


# ── 测试 ──────────────────────────────────────────────────
async def main():
    os.makedirs("generated/results", exist_ok=True)

    async with SiteClient() as client:
        # 1. 文生图
        print("\n--- 文生图 ---")
        r = await client.text_to_image("a cute cat on a wooden table, photorealistic, 4k")
        print(json.dumps(r, ensure_ascii=False, indent=2)[:300])

        # 2. 即梦视频
        print("\n--- 即梦视频 ---")
        r = await client.jimeng_video("a cat walking in the forest, cinematic")
        print(json.dumps(r, ensure_ascii=False, indent=2)[:300])

        # 3. Veo 视频
        print("\n--- Veo 视频 ---")
        r = await client.veo_video("a cat walking in the forest, cinematic")
        print(json.dumps(r, ensure_ascii=False, indent=2)[:300])

        # 4. Wan 视频
        print("\n--- Wan 视频 ---")
        r = await client.wan_video("a cat walking in the forest, cinematic")
        print(json.dumps(r, ensure_ascii=False, indent=2)[:300])

        # 5. 文本转语音
        print("\n--- 文本转语音 ---")
        r = await client.text_to_speech("你好，这是一段测试语音")
        print(json.dumps(r, ensure_ascii=False, indent=2)[:300])

    with open("generated/results/test.json", "w") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
