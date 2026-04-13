"""
分析站点的注册/登录流程
"""
import asyncio
import os
from playwright.async_api import async_playwright

os.makedirs("generated/login", exist_ok=True)

SITES = [
    "https://115.190.169.243",
    "https://42.193.219.6",   # 已知可用，作为对照
]

async def inspect_site(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 900}
        )
        slug = url.replace("https://", "").replace("/", "_")

        print(f"\n{'='*60}")
        print(f"站点: {url}")

        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"generated/login/{slug}_home.png")

        # 找登录/注册入口
        for kw in ["登录", "注册", "Login", "Sign up", "Sign in", "Register"]:
            els = await page.locator(f"text={kw}").all()
            for el in els[:3]:
                try:
                    visible = await el.is_visible()
                    tag = await el.evaluate("el => el.tagName")
                    href = await el.get_attribute("href") or ""
                    if visible:
                        print(f"  [{kw}] tag={tag} href={href!r}")
                except Exception:
                    pass

        # 尝试点击注册
        for kw in ["注册", "Sign up", "Register", "免费注册"]:
            btn = page.locator(f"text={kw}").first
            if await btn.count() > 0 and await btn.is_visible():
                print(f"\n点击注册: {kw}")
                await btn.click()
                await page.wait_for_timeout(2000)
                await page.screenshot(path=f"generated/login/{slug}_register.png")

                # 分析注册表单
                inputs = await page.locator("input").all()
                print("注册表单字段:")
                for inp in inputs:
                    try:
                        t = await inp.get_attribute("type") or "text"
                        ph = await inp.get_attribute("placeholder") or ""
                        nm = await inp.get_attribute("name") or ""
                        visible = await inp.is_visible()
                        if visible:
                            print(f"  input[{t}] name={nm!r} placeholder={ph!r}")
                    except Exception:
                        pass
                break

        await browser.close()

async def main():
    for url in SITES:
        await inspect_site(url)

asyncio.run(main())
