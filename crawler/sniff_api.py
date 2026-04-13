"""
抓包分析 115.190.169.243 的视频生成接口
用 Playwright 拦截所有网络请求
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright

os.makedirs("generated/sniff", exist_ok=True)

URL = "https://115.190.169.243"

with open("accounts.json") as f:
    accounts = json.load(f)
account = [a for a in accounts if a["url"] == URL and a.get("success")][-1]

with open(f"generated/accounts/115.190.169.243_cookies.json") as f:
    cookies = json.load(f)


async def main():
    captured = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 900}
        )
        await context.add_cookies(cookies)

        page = await context.new_page()

        # 拦截所有 XHR / fetch 请求
        async def on_request(request):
            if request.resource_type in ("xhr", "fetch"):
                captured.append({
                    "type": "request",
                    "method": request.method,
                    "url": request.url,
                    "post_data": request.post_data,
                    "headers": dict(request.headers),
                })

        async def on_response(response):
            if response.request.resource_type in ("xhr", "fetch"):
                try:
                    body = await response.text()
                    captured.append({
                        "type": "response",
                        "url": response.url,
                        "status": response.status,
                        "body": body[:500],
                    })
                except Exception:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)

        await page.goto(URL, timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # 关弹窗
        await page.evaluate("""
            document.querySelectorAll('.modal.show').forEach(m => {
                m.style.display='none'; m.classList.remove('show');
            });
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            document.body.classList.remove('modal-open');
        """)

        # 截图看页面有哪些功能
        await page.screenshot(path="generated/sniff/home.png", full_page=True)

        # 找所有导航 tab
        nav_items = await page.locator("a, button, li, [role=tab]").all()
        print("可见导航项:")
        for item in nav_items:
            try:
                txt = (await item.inner_text()).strip()
                visible = await item.is_visible()
                if visible and txt and len(txt) < 20:
                    href = await item.get_attribute("href") or ""
                    print(f"  {repr(txt)}  href={repr(href)}")
            except Exception:
                pass

        # 点击视频相关 tab
        for kw in ["视频", "文生视频", "图生视频", "Video", "生成视频"]:
            el = page.locator(f"text={kw}").first
            if await el.count() > 0 and await el.is_visible():
                print(f"\n点击: {kw}")
                await el.click()
                await page.wait_for_timeout(2000)
                await page.screenshot(path=f"generated/sniff/tab_{kw}.png")
                break

        # 找视频生成的输入框和按钮
        print("\n当前页面输入框:")
        inputs = await page.locator("input:visible, textarea:visible").all()
        for inp in inputs:
            t = await inp.get_attribute("type") or "textarea"
            ph = await inp.get_attribute("placeholder") or ""
            nm = await inp.get_attribute("name") or ""
            print(f"  [{t}] name={repr(nm)} placeholder={repr(ph[:40])}")

        print("\n当前页面按钮:")
        btns = await page.locator("button:visible").all()
        for btn in btns[:10]:
            txt = (await btn.inner_text()).strip()
            if txt:
                print(f"  {repr(txt)}")

        # 尝试触发视频生成，捕获接口
        print("\n尝试触发视频生成...")
        ta = page.locator("textarea:visible").first
        if await ta.count() > 0:
            await ta.fill("a cat walking in the forest, cinematic")

        for kw in ["生成", "Generate", "生成视频", "开始"]:
            btn = page.locator(f"button:has-text('{kw}'):visible").first
            if await btn.count() > 0:
                print(f"点击: {kw}")
                await btn.click()
                await page.wait_for_timeout(5000)
                break

        await browser.close()

    # 输出捕获的请求
    print(f"\n捕获到 {len(captured)} 个网络请求:")
    api_calls = [c for c in captured if c["type"] == "request" and c["method"] == "POST"]
    for req in api_calls:
        print(f"\n  POST {req['url']}")
        if req.get("post_data"):
            print(f"  body: {req['post_data'][:200]}")

    with open("generated/sniff/captured.json", "w") as f:
        json.dump(captured, f, ensure_ascii=False, indent=2)
    print("\n完整请求已保存: generated/sniff/captured.json")


asyncio.run(main())
