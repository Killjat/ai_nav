"""针对 42.193.219.6 找到 tab 并生图"""
import asyncio, os
from playwright.async_api import async_playwright

os.makedirs("generated", exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(ignore_https_errors=True, viewport={"width": 1280, "height": 900})

        await page.goto("https://42.193.219.6", timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # 找所有可见的导航/tab 元素
        nav_items = await page.locator("a, li, [role=tab], .tab, .nav-item, .menu-item").all()
        print(f"导航元素 {len(nav_items)} 个:")
        for item in nav_items[:20]:
            try:
                txt = (await item.inner_text()).strip()
                visible = await item.is_visible()
                href = await item.get_attribute("href") or ""
                if txt and visible:
                    print(f"  visible text={repr(txt[:30])} href={repr(href)}")
            except Exception:
                pass

        await page.screenshot(path="generated/42_init.png", full_page=True)
        print("截图: generated/42_init.png")

        # 尝试找包含"生图"或"AI"的导航项并点击
        for keyword in ["生图", "AI绘图", "文生图", "图片生成", "AI图片"]:
            try:
                el = page.locator(f"text={keyword}").first
                if await el.count() > 0 and await el.is_visible():
                    print(f"找到导航: {keyword}，点击...")
                    await el.click()
                    await page.wait_for_timeout(2000)
                    break
            except Exception:
                pass

        # 现在找 generateAiImage 按钮
        btn = page.locator("button[onclick='generateAiImage()']")
        if await btn.count() > 0:
            # 用 JS 强制显示父容器
            await page.evaluate("""
                const btn = document.querySelector("button[onclick='generateAiImage()']");
                if (btn) {
                    let el = btn;
                    while (el) {
                        el.style.display = 'block';
                        el.style.visibility = 'visible';
                        el.style.opacity = '1';
                        el = el.parentElement;
                        if (el === document.body) break;
                    }
                }
            """)
            await page.wait_for_timeout(500)

            # 填 prompt
            ta = page.locator("textarea[placeholder*='生成的图片']")
            await ta.evaluate("el => { el.style.display='block'; el.style.visibility='visible'; }")
            await ta.fill("a cute cat, photorealistic, 4k")
            print("已填入 prompt")

            await btn.click()
            print("已点击生成，等待 30 秒...")
            await page.wait_for_timeout(30000)

            await page.screenshot(path="generated/42_result.png", full_page=True)
            print("结果截图: generated/42_result.png")

            # 找生成的图片
            imgs = page.locator("img")
            count = await imgs.count()
            print(f"页面共 {count} 张图片")
            for i in range(min(count, 8)):
                src = await imgs.nth(i).get_attribute("src") or ""
                if src and not src.startswith("data:image/svg"):
                    print(f"  img[{i}] src={repr(src[:80])}")

        await browser.close()

asyncio.run(main())
