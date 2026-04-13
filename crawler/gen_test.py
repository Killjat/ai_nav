"""针对 42.193.219.6 实际生图测试"""
import asyncio, os, base64
from playwright.async_api import async_playwright

PROMPT = "a cute cat sitting on a wooden table, soft lighting, photorealistic, 4k"
URL = "https://42.193.219.6"
os.makedirs("generated", exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 先开有头模式看过程
        page = await browser.new_page(ignore_https_errors=True,
            viewport={"width": 1280, "height": 900})

        print(f"打开 {URL} ...")
        await page.goto(URL, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # 截图看初始状态
        await page.screenshot(path="generated/step1_init.png")
        print("初始截图已保存")

        # 找 textarea
        ta = page.locator("textarea").first
        await ta.click()
        await ta.fill(PROMPT)
        print(f"已填入 prompt: {PROMPT[:40]}...")

        await page.screenshot(path="generated/step2_filled.png")

        # 点击生成按钮
        btn = page.locator("button:has-text('生成')").first
        await btn.click()
        print("已点击生成，等待结果...")

        await page.screenshot(path="generated/step3_clicked.png")

        # 等待图片出现（最多 60 秒）
        try:
            # 等待页面上出现新的 img 元素或 loading 消失
            await page.wait_for_timeout(5000)
            await page.screenshot(path="generated/step4_waiting.png")

            await page.wait_for_timeout(15000)
            await page.screenshot(path="generated/step5_result.png")
            print("结果截图已保存: generated/step5_result.png")

            # 尝试找生成的图片
            imgs = page.locator("img")
            count = await imgs.count()
            print(f"页面共有 {count} 张图片")
            for i in range(min(count, 5)):
                src = await imgs.nth(i).get_attribute("src") or ""
                print(f"  img[{i}] src={src[:80]!r}")

        except Exception as e:
            print(f"等待失败: {e}")

        await browser.close()

asyncio.run(main())
