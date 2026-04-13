"""
自动注册 + 登录，使用临时邮箱
支持：邮箱注册、手机号注册（跳过）
临时邮箱服务：mail.tm (免费API，无需key)
"""
import asyncio
import httpx
import random
import string
import json
import os
from playwright.async_api import async_playwright, Page

os.makedirs("generated/accounts", exist_ok=True)
ACCOUNTS_FILE = "accounts.json"


# ── 临时邮箱 mail.tm ──────────────────────────────────────
class TempMail:
    BASE = "https://api.mail.tm"

    def __init__(self):
        self.address = ""
        self.password = ""
        self.token = ""

    async def create(self) -> str:
        """创建临时邮箱，返回地址"""
        async with httpx.AsyncClient() as client:
            # 获取可用域名
            r = await client.get(f"{self.BASE}/domains", timeout=10)
            domain = r.json()["hydra:member"][0]["domain"]

            # 生成随机用户名
            username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            self.address = f"{username}@{domain}"
            self.password = "".join(random.choices(string.ascii_letters + string.digits, k=12))

            # 注册邮箱
            r = await client.post(f"{self.BASE}/accounts", json={
                "address": self.address,
                "password": self.password,
            }, timeout=10)

            # 获取 token
            r = await client.post(f"{self.BASE}/token", json={
                "address": self.address,
                "password": self.password,
            }, timeout=10)
            self.token = r.json().get("token", "")

        print(f"  临时邮箱: {self.address}")
        return self.address

    async def wait_for_code(self, timeout: int = 60) -> str:
        """等待验证码邮件，返回验证码"""
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as client:
            for _ in range(timeout // 3):
                await asyncio.sleep(3)
                r = await client.get(f"{self.BASE}/messages", headers=headers, timeout=10)
                messages = r.json().get("hydra:member", [])
                if messages:
                    msg_id = messages[0]["id"]
                    r = await client.get(f"{self.BASE}/messages/{msg_id}", headers=headers, timeout=10)
                    body = r.json().get("text", "") + r.json().get("html", "")
                    # 提取6位数字验证码
                    import re
                    codes = re.findall(r'\b\d{4,8}\b', body)
                    if codes:
                        print(f"  收到验证码: {codes[0]}")
                        return codes[0]
        return ""


# ── 自动注册 ──────────────────────────────────────────────
async def dismiss_modals(page: Page):
    """关闭所有弹窗"""
    for sel in [
        "#homeNoticeModal .btn-close",
        ".modal .btn-close",
        "button:has-text('今日不再提示')",
        "button:has-text('我已知晓')",
        "button:has-text('关闭')",
        ".modal-footer button",
    ]:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible():
                await el.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

    # 用 JS 强制关闭所有 modal
    await page.evaluate("""
        document.querySelectorAll('.modal.show, .modal.fade.show').forEach(m => {
            m.style.display = 'none';
            m.classList.remove('show');
        });
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
    """)
    await page.wait_for_timeout(300)


async def register_site(url: str) -> dict:
    """自动注册站点，返回账号信息"""
    result = {"url": url, "success": False, "email": "", "password": "", "cookies": []}
    temp_mail = TempMail()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()
        slug = url.replace("https://", "").replace("/", "_")

        try:
            # 创建临时邮箱
            email = await temp_mail.create()
            password = "Test" + "".join(random.choices(string.digits, k=8)) + "!"

            # 打开站点
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await dismiss_modals(page)

            # 找注册链接
            register_url = None
            for kw in ["注册", "Sign up", "Register", "免费注册", "立即注册"]:
                el = page.locator(f"text={kw}").first
                if await el.count() > 0 and await el.is_visible():
                    href = await el.get_attribute("href") or ""
                    if href:
                        register_url = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
                    await el.click()
                    await page.wait_for_timeout(2000)
                    break

            await page.screenshot(path=f"generated/accounts/{slug}_register.png")

            # 分析注册表单
            inputs = await page.locator("input:visible").all()
            form_fields = {}
            for inp in inputs:
                t = await inp.get_attribute("type") or "text"
                nm = await inp.get_attribute("name") or ""
                ph = (await inp.get_attribute("placeholder") or "").lower()
                if t in ("hidden", "submit", "button"):
                    continue
                form_fields[nm or ph] = {"type": t, "element": inp}

            print(f"  表单字段: {list(form_fields.keys())}")

            # 填写表单
            filled = False
            for key, field in form_fields.items():
                t = field["type"]
                el = field["element"]
                key_lower = key.lower()

                if t == "email" or "email" in key_lower or "邮箱" in key_lower or "mail" in key_lower:
                    await el.fill(email)
                    filled = True
                elif t == "password" or "password" in key_lower or "密码" in key_lower:
                    await el.fill(password)
                    filled = True
                elif "confirm" in key_lower or "确认" in key_lower or "repeat" in key_lower:
                    await el.fill(password)
                elif "username" in key_lower or "用户名" in key_lower or "昵称" in key_lower or "user" in key_lower:
                    uname = "user" + "".join(random.choices(string.digits, k=6))
                    await el.fill(uname)
                    result["username"] = uname
                    filled = True
                elif "phone" in key_lower or "手机" in key_lower or "mobile" in key_lower:
                    print("  ⚠️ 需要手机号，跳过")
                    await browser.close()
                    return result

            await page.screenshot(path=f"generated/accounts/{slug}_filled.png")

            # 提交注册
            for sel in ["button[type='submit']", "input[type='submit']",
                        "button:has-text('注册')", "button:has-text('Register')",
                        "button:has-text('Sign up')", "button:has-text('提交')"]:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    print("  提交注册...")
                    await page.wait_for_timeout(3000)
                    break

            await page.screenshot(path=f"generated/accounts/{slug}_submitted.png")

            # 检查是否需要邮箱验证
            page_text = await page.content()
            needs_verify = any(kw in page_text for kw in ["验证", "verify", "confirm", "激活", "activate"])

            if needs_verify:
                print("  等待验证码邮件...")
                code = await temp_mail.wait_for_code(timeout=60)
                if code:
                    # 找验证码输入框
                    for sel in ["input[name='code']", "input[placeholder*='验证码']",
                                "input[placeholder*='code']", "input[maxlength='6']"]:
                        el = page.locator(sel).first
                        if await el.count() > 0 and await el.is_visible():
                            await el.fill(code)
                            await page.keyboard.press("Enter")
                            await page.wait_for_timeout(2000)
                            break

            # 保存 cookies
            cookies = await context.cookies()

            # 如果 cookie 里没有 session，尝试登录
            session_keys = ["session", "token", "auth", "PHPSESSID", "laravel_session"]
            has_session = any(
                any(k.lower() in c["name"].lower() for k in session_keys)
                for c in cookies
            )

            if not has_session:
                print("  未检测到 session，尝试登录...")
                await page.goto(url, timeout=15000)
                await page.wait_for_timeout(1000)
                await dismiss_modals(page)

                # 找登录入口
                for kw in ["登录", "Login", "Sign in"]:
                    el = page.locator(f"text={kw}").first
                    if await el.count() > 0 and await el.is_visible():
                        await el.click()
                        await page.wait_for_timeout(1500)
                        break

                # 填登录表单
                for sel, val in [
                    ("input[name='username'], input[type='text']:visible", result.get("username", email)),
                    ("input[type='password']:visible", password),
                ]:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.fill(val)

                # 提交
                for sel in ["button[type='submit']", "button:has-text('登录')", "button:has-text('Login')"]:
                    btn = page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        break

                cookies = await context.cookies()

            result["cookies"] = cookies
            result["email"] = email
            result["password"] = password
            result["success"] = True
            print(f"  ✅ 注册成功！email={email}")

            await page.screenshot(path=f"generated/accounts/{slug}_done.png")

        except Exception as e:
            print(f"  ❌ 注册失败: {e}")
        finally:
            await browser.close()

    return result


def save_account(result: dict):
    accounts = []
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE) as f:
            accounts = json.load(f)
    accounts.append({k: v for k, v in result.items() if k != "cookies"})
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


async def main():
    sites = ["https://115.190.169.243"]
    for url in sites:
        print(f"\n注册: {url}")
        result = await register_site(url)
        if result["success"]:
            save_account(result)
            # 保存 cookies 供后续使用
            cookie_file = f"generated/accounts/{url.replace('https://','').replace('/','_')}_cookies.json"
            with open(cookie_file, "w") as f:
                json.dump(result["cookies"], f)
            print(f"  cookies 已保存: {cookie_file}")

asyncio.run(main())
