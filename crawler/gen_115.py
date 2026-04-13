"""针对 115.190.169.243 生图测试"""
import asyncio, os
from playwright.async_api import async_playwright

os.makedirs("generated", exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(ignore_https_errors=True, viewport={"width": 1280, "height": 900})

        url = "https://115.190.169.243"
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # 关掉可能的弹窗
        for dismiss in ["今日不再提示", "我已知晓", "关闭", "×"]:
            try:
                btn = page.locator(f"button:has-text('{dismiss}')").first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(500)
                    print(f"关闭弹窗: {dismiss}")
            except Exception:
                pass

        await page.screenshot(path="generated/115_init.png")

        # 点击"文生图" tab
        tab = page.locator("button:has-text('文生图')").first
        if await tab.count() > 0:
            await tab.click()
            await page.wait_for_timeout(1500)
            print("切换到文生图 tab")

        await page.screenshot(path="generated/115_tab.png")

        # 填 prompt
        ta = page.locator("textarea[placeholder*='描述你想要生成的画面']").first
        await ta.fill("a cute cat sitting on a wooden table, photorealistic, 4k")
        print("已填入 prompt")

        await page.screenshot(path="generated/115_filled.png")

        # 找生成按钮（文生图 tab 下的生成按钮）
        # 先看看有哪些按钮
        btns = await page.locator("button").all()
        for btn in btns:
            try:
                txt = (await btn.inner_text()).strip()
                visible = await btn.is_visible()
                if visible and txt:
                    print(f"  可见按钮: {repr(txt[:30])}")
            except Exception:
                pass

        # 找生成相关按钮
        for kw in ["生成", "Generate", "立即生成", "开始"]:
            btn = page.locator(f"button:has-text('{kw}')").first
            if await btn.count() > 0 and await btn.is_visible():
                print(f"点击: {kw}")
                await btn.click()
                break

        print("等待生成结果 (45s)...")
        await page.wait_for_timeout(45000)
        await page.screenshot(path="generated/115_result.png")

        imgs = await page.locator("img").all()
        for i, img in enumerate(imgs):
            src = await img.get_attribute("src") or ""
            if src and len(src) > 20 and "svg" not in src:
                print(f"img[{i}]: {src[:100]}")

        await browser.close()

asyncio.run(main())
