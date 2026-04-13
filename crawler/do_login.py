"""直接登录 115.190.169.243 并生图"""
import asyncio, json, os
from playwright.async_api import async_playwright

os.makedirs("generated/accounts", exist_ok=True)

# 上次注册的账号（从 accounts.json 读）
with open("accounts.json") as f:
    accounts = json.load(f)
account = accounts[-1]
print(f"使用账号: {account}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True, viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()

        # 打开登录页
        await page.goto("https://115.190.169.243/login.php", timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await page.screenshot(path="generated/accounts/login_page.png")

        # 分析登录表单
        inputs = await page.locator("input:visible").all()
        for inp in inputs:
            t = await inp.get_attribute("type") or "text"
            nm = await inp.get_attribute("name") or ""
            ph = await inp.get_attribute("placeholder") or ""
            print(f"  input[{t}] name={nm!r} placeholder={ph!r}")

        # 填登录表单
        username_filled = False
        for sel in ["input[name='username']", "input[type='text']:visible", "input[name='email']"]:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible():
                await el.fill(account.get("username", account["email"].split("@")[0]))
                username_filled = True
                print(f"填用户名: {account['email'].split('@')[0]}")
                break

        for sel in ["input[type='password']:visible"]:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.fill(account["password"])
                print(f"填密码: {account['password']}")

        await page.screenshot(path="generated/accounts/login_filled.png")

        # 提交
        for sel in ["button[type='submit']", "input[type='submit']",
                    "button:has-text('登录')", "button:has-text('Login')"]:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                print("提交登录...")
                await page.wait_for_timeout(3000)
                break

        await page.screenshot(path="generated/accounts/login_result.png")

        # 检查登录状态
        content = await page.content()
        logged_in = any(kw in content for kw in ["退出", "logout", "个人中心", "我的账户"])
        print(f"登录状态: {'✅ 已登录' if logged_in else '❌ 未登录'}")
        print(f"当前 URL: {page.url}")

        if logged_in:
            # 保存新 cookies
            cookies = await context.cookies()
            with open("generated/accounts/115.190.169.243_cookies.json", "w") as f:
                json.dump(cookies, f)
            print("cookies 已更新")

            # 关弹窗
            await page.evaluate("""
                document.querySelectorAll('.modal.show').forEach(m => {
                    m.style.display='none'; m.classList.remove('show');
                });
                document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
                document.body.classList.remove('modal-open');
            """)

            # 切文生图 tab
            tab = page.locator("button:has-text('文生图')").first
            if await tab.count() > 0:
                await tab.click()
                await page.wait_for_timeout(1500)

            # 填 prompt 并生成
            ta = page.locator("textarea:visible").first
            if await ta.count() > 0:
                await ta.fill("a cute cat, photorealistic, 4k")
                print("已填入 prompt")

            for kw in ["生成", "Generate"]:
                btn = page.locator(f"button:has-text('{kw}'):visible").first
                if await btn.count() > 0:
                    await btn.click()
                    print(f"点击生成，等待 50s...")
                    await page.wait_for_timeout(50000)
                    break

            await page.screenshot(path="generated/115_with_login.png")

            imgs = await page.locator("img").all()
            for i, img in enumerate(imgs):
                src = await img.get_attribute("src") or ""
                if src and len(src) > 20 and "svg" not in src.lower():
                    print(f"img[{i}]: {src[:100]}")

        await browser.close()

asyncio.run(main())
