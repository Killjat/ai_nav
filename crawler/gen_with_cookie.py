"""带 cookie 登录后生图"""
import asyncio, json, os
from playwright.async_api import async_playwright

os.makedirs("generated", exist_ok=True)

async def main():
    cookie_file = "generated/accounts/115.190.169.243_cookies.json"
    with open(cookie_file) as f:
        cookies = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 900}
        )
        # 注入 cookies
        await context.add_cookies(cookies)

        page = await context.new_page()
        await page.goto("https://115.190.169.243", timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # 关弹窗
        await page.evaluate("""
            document.querySelectorAll('.modal.show').forEach(m => {
                m.style.display='none'; m.classList.remove('show');
            });
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            document.body.classList.remove('modal-open');
        """)
        await page.wait_for_timeout(500)

        await page.screenshot(path="generated/115_loggedin.png")

        # 检查是否已登录
        content = await page.content()
        logged_in = any(kw in content for kw in ["退出", "logout", "个人中心", "我的", "用户名"])
        print(f"登录状态: {'✅ 已登录' if logged_in else '❌ 未登录'}")

        # 切换到文生图 tab
        tab = page.locator("button:has-text('文生图'), a:has-text('文生图')").first
        if await tab.count() > 0:
            await tab.click()
            await page.wait_for_timeout(1500)
            print("切换到文生图 tab")

        await page.screenshot(path="generated/115_loggedin_tab.png")

        # 找 prompt 输入框
        ta = page.locator("textarea[placeholder*='描述你想要生成的画面']").first
        if await ta.count() > 0:
            await ta.fill("a cute cat sitting on a wooden table, photorealistic, 4k")
            print("已填入 prompt")
        else:
            # 找所有可见 textarea
            tas = await page.locator("textarea:visible").all()
            print(f"可见 textarea: {len(tas)}")
            if tas:
                await tas[0].fill("a cute cat sitting on a wooden table, photorealistic, 4k")

        # 找生成按钮
        for kw in ["生成", "Generate", "立即生成", "开始生成"]:
            btn = page.locator(f"button:has-text('{kw}'):visible").first
            if await btn.count() > 0:
                print(f"点击: {kw}")
                await btn.click()
                break

        print("等待生成结果 (50s)...")
        await page.wait_for_timeout(50000)
        await page.screenshot(path="generated/115_generated.png")

        # 找结果图片
        imgs = await page.locator("img").all()
        for i, img in enumerate(imgs):
            src = await img.get_attribute("src") or ""
            if src and len(src) > 20 and "svg" not in src.lower():
                print(f"img[{i}]: {src[:100]}")

        await browser.close()

asyncio.run(main())
