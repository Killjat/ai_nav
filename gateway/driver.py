"""
Playwright 驱动：操作具体站点生图
每个站点有自己的操作策略
"""
import asyncio
import httpx
from playwright.async_api import async_playwright, Page, BrowserContext

import json
import os
import logging

logger = logging.getLogger(__name__)

# 从文件加载策略（discover.py 自动更新）
_STRATEGIES_FILE = os.path.join(os.path.dirname(__file__), "strategies.json")

def load_strategies() -> dict:
    if os.path.exists(_STRATEGIES_FILE):
        with open(_STRATEGIES_FILE) as f:
            return json.load(f)
    return {}

def reload_strategies():
    """热重载策略，无需重启网关"""
    new = load_strategies()
    SITE_STRATEGIES.update(new)
    logger.info(f"策略已重载，共 {len(SITE_STRATEGIES)} 个站点")

# 内置已知可用站点
SITE_STRATEGIES: dict = {
    "42.193.219.6": {
        "name": "ISUX AI生图",
        "tab_text": "生图",
        "prompt_selector": "textarea[placeholder*='生成的图片']",
        "button_selector": "button[onclick='generateAiImage()']",
        "result_selector": "img",
        "wait_ms": 35000,
        "force_show": True,
    },
    "115.190.169.243": {
        "name": "AI生图站",
        "tab_text": "文生图",
        "prompt_selector": "textarea:visible",
        "button_selector": "button:has-text('生成'):visible",
        "result_selector": "img",
        "wait_ms": 50000,
        "force_show": False,
        "needs_login": True,
        "dismiss_modal": True,
    },
    **load_strategies(),
}

# 通用策略（fallback）
GENERIC_STRATEGY = {
    "prompt_selectors": [
        "textarea[placeholder*='prompt']",
        "textarea[placeholder*='描述']",
        "textarea[placeholder*='输入']",
        "textarea[name='prompt']",
        "#prompt",
    ],
    "button_selectors": [
        "button:has-text('生成图片')",
        "button:has-text('Generate')",
        "button:has-text('生成')",
        "button:has-text('Create')",
    ],
    "wait_ms": 40000,
}


async def _force_show(page: Page, selector: str):
    """强制显示隐藏元素"""
    await page.evaluate(f"""
        const el = document.querySelector("{selector}");
        if (el) {{
            let cur = el;
            while (cur && cur !== document.body) {{
                cur.style.display = 'block';
                cur.style.visibility = 'visible';
                cur.style.opacity = '1';
                cur = cur.parentElement;
            }}
        }}
    """)


async def generate_on_site(url: str, prompt: str, context: BrowserContext) -> dict:
    """在指定站点生图，返回 image_url 或 error"""
    page = await context.new_page()
    result = {"success": False, "image_url": "", "error": ""}

    try:
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        strategy = SITE_STRATEGIES.get(domain)

        if strategy:
            # 关弹窗
            if strategy.get("dismiss_modal"):
                await page.evaluate("""
                    document.querySelectorAll('.modal.show').forEach(m => {
                        m.style.display='none'; m.classList.remove('show');
                    });
                    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                    document.body.classList.remove('modal-open');
                """)
                await page.wait_for_timeout(400)

            # 切 tab
            if strategy.get("tab_text"):
                try:
                    await page.locator(f"text={strategy['tab_text']}").first.click()
                    await page.wait_for_timeout(1000)
                except Exception:
                    pass

            if strategy.get("force_show"):
                await _force_show(page, strategy["prompt_selector"])
                await _force_show(page, strategy["button_selector"])

            ta = page.locator(strategy["prompt_selector"])
            await ta.evaluate("el => { el.style.display='block'; el.style.visibility='visible'; }")
            await ta.fill(prompt)

            btn = page.locator(strategy["button_selector"])
            await btn.click()
            await page.wait_for_timeout(strategy["wait_ms"])

            # 找结果图片（排除 svg 和小图标）
            imgs = await page.locator("img").all()
            for img in imgs:
                src = await img.get_attribute("src") or ""
                if src and not src.startswith("data:image/svg") and len(src) > 20:
                    if any(ext in src for ext in [".webp", ".png", ".jpg", ".jpeg", "cdn", "image"]):
                        result["image_url"] = src
                        result["success"] = True
                        break

        else:
            # 通用策略
            for sel in GENERIC_STRATEGY["prompt_selectors"]:
                ta = page.locator(sel).first
                if await ta.count() > 0 and await ta.is_visible():
                    await ta.fill(prompt)
                    break
            else:
                result["error"] = "未找到 prompt 输入框"
                return result

            for sel in GENERIC_STRATEGY["button_selectors"]:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    break
            else:
                result["error"] = "未找到生成按钮"
                return result

            await page.wait_for_timeout(GENERIC_STRATEGY["wait_ms"])

            imgs = await page.locator("img").all()
            for img in imgs:
                src = await img.get_attribute("src") or ""
                if src and not src.startswith("data:image/svg") and len(src) > 20:
                    result["image_url"] = src
                    result["success"] = True
                    break

        if not result["success"]:
            result["error"] = "生成超时或未找到结果图片"

    except Exception as e:
        result["error"] = str(e)
    finally:
        await page.close()

    return result


class PlaywrightDriver:
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._contexts: dict[str, BrowserContext] = {}  # 每个站点独立 context（带 cookie）

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

    async def _get_context(self, url: str) -> BrowserContext:
        """获取站点对应的 context，自动注入 cookie"""
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        if domain not in self._contexts:
            ctx = await self._browser.new_context(
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
                viewport={"width": 1280, "height": 900},
            )
            # 尝试注入已保存的 cookie
            from crawler.account_manager import load_cookies, ensure_logged_in
            cookies = load_cookies(url)
            if not cookies:
                # 没有 cookie，尝试自动注册登录
                logger.info(f"站点 {domain} 无 cookie，尝试自动登录...")
                cookies = await ensure_logged_in(url)
            if cookies:
                await ctx.add_cookies(cookies)
                logger.info(f"站点 {domain} 注入 {len(cookies)} 个 cookie")
            self._contexts[domain] = ctx
        return self._contexts[domain]

    async def stop(self):
        for ctx in self._contexts.values():
            await ctx.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def generate(self, url: str, prompt: str) -> dict:
        context = await self._get_context(url)
        return await generate_on_site(url, prompt, context)
