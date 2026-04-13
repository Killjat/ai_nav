"""
账号管理器：自动注册、登录、维护各站点的 cookie
"""
import asyncio
import json
import os
import random
import string
import httpx
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Page, BrowserContext

ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), "..", "accounts.json")
COOKIES_DIR   = os.path.join(os.path.dirname(__file__), "..", "generated", "accounts")
os.makedirs(COOKIES_DIR, exist_ok=True)


# ── 临时邮箱 ──────────────────────────────────────────────
class TempMail:
    BASE = "https://api.mail.tm"

    def __init__(self):
        self.address = ""
        self.password = ""
        self.token = ""

    async def create(self) -> str:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{self.BASE}/domains", timeout=10)
            domain = r.json()["hydra:member"][0]["domain"]
            username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
            self.address  = f"{username}@{domain}"
            self.password = "".join(random.choices(string.ascii_letters + string.digits, k=12))
            await c.post(f"{self.BASE}/accounts",
                         json={"address": self.address, "password": self.password}, timeout=10)
            r = await c.post(f"{self.BASE}/token",
                             json={"address": self.address, "password": self.password}, timeout=10)
            self.token = r.json().get("token", "")
        return self.address

    async def wait_code(self, timeout: int = 60) -> str:
        import re
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient() as c:
            for _ in range(timeout // 3):
                await asyncio.sleep(3)
                r = await c.get(f"{self.BASE}/messages", headers=headers, timeout=10)
                msgs = r.json().get("hydra:member", [])
                if msgs:
                    r2 = await c.get(f"{self.BASE}/messages/{msgs[0]['id']}",
                                     headers=headers, timeout=10)
                    body = r2.json().get("text", "") + r2.json().get("html", "")
                    codes = re.findall(r'\b\d{4,8}\b', body)
                    if codes:
                        return codes[0]
        return ""


# ── 工具函数 ──────────────────────────────────────────────
def _slug(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("/", "_")


def _cookie_path(url: str) -> str:
    return os.path.join(COOKIES_DIR, f"{_slug(url)}_cookies.json")


def load_accounts() -> list[dict]:
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE) as f:
            return json.load(f)
    return []


def save_account(record: dict):
    accounts = load_accounts()
    # 更新已有记录
    for i, a in enumerate(accounts):
        if a["url"] == record["url"]:
            accounts[i] = record
            break
    else:
        accounts.append(record)
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def get_account(url: str) -> dict | None:
    for a in load_accounts():
        if a["url"] == url and a.get("success"):
            return a
    return None


def load_cookies(url: str) -> list[dict]:
    path = _cookie_path(url)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def save_cookies(url: str, cookies: list[dict]):
    with open(_cookie_path(url), "w") as f:
        json.dump(cookies, f)


async def dismiss_modals(page: Page):
    for sel in [".modal .btn-close", "button:has-text('今日不再提示')",
                "button:has-text('我已知晓')", ".modal-footer button"]:
        try:
            el = page.locator(sel).first
            if await el.count() > 0 and await el.is_visible():
                await el.click()
                await page.wait_for_timeout(400)
        except Exception:
            pass
    await page.evaluate("""
        document.querySelectorAll('.modal.show').forEach(m => {
            m.style.display='none'; m.classList.remove('show');
        });
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
    """)


# ── 注册 ──────────────────────────────────────────────────
async def register(url: str, context: BrowserContext) -> dict:
    """自动注册，返回账号信息"""
    result = {"url": url, "success": False, "email": "", "password": "", "username": ""}
    temp_mail = TempMail()
    page = await context.new_page()

    try:
        email    = await temp_mail.create()
        password = "Pass" + "".join(random.choices(string.digits, k=8)) + "!"
        username = "user" + "".join(random.choices(string.digits, k=6))

        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await dismiss_modals(page)

        # 找注册入口
        for kw in ["注册", "Sign up", "Register", "免费注册"]:
            el = page.locator(f"text={kw}").first
            if await el.count() > 0 and await el.is_visible():
                href = await el.get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = url.rstrip("/") + "/" + href.lstrip("/")
                if href:
                    await page.goto(href, timeout=10000)
                else:
                    await el.click()
                await page.wait_for_timeout(1500)
                break

        # 填表单
        inputs = await page.locator("input:visible").all()
        filled = False
        for inp in inputs:
            t  = await inp.get_attribute("type") or "text"
            nm = (await inp.get_attribute("name") or "").lower()
            ph = (await inp.get_attribute("placeholder") or "").lower()
            key = nm or ph

            if t in ("hidden", "submit", "button", "checkbox"):
                continue
            if t == "email" or "email" in key or "邮箱" in key or "mail" in key:
                await inp.fill(email); filled = True
            elif "username" in key or "用户名" in key or "user" in key or "昵称" in key:
                await inp.fill(username); filled = True
            elif "confirm" in key or "确认" in key or "repeat" in key:
                await inp.fill(password)
            elif t == "password" or "password" in key or "密码" in key:
                await inp.fill(password); filled = True
            elif "phone" in key or "手机" in key or "mobile" in key:
                return result  # 需要手机号，跳过

        if not filled:
            return result

        # 提交
        for sel in ["button[type='submit']", "input[type='submit']",
                    "button:has-text('注册')", "button:has-text('Register')",
                    "button:has-text('Sign up')"]:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                await page.wait_for_timeout(3000)
                break

        # 处理邮箱验证码
        content = await page.content()
        if any(kw in content for kw in ["验证", "verify", "confirm", "激活"]):
            code = await temp_mail.wait_code(60)
            if code:
                for sel in ["input[name='code']", "input[placeholder*='验证码']",
                            "input[maxlength='6']", "input[maxlength='4']"]:
                    el = page.locator(sel).first
                    if await el.count() > 0 and await el.is_visible():
                        await el.fill(code)
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(2000)
                        break

        result.update({"success": True, "email": email,
                        "password": password, "username": username})

    except Exception as e:
        result["error"] = str(e)
    finally:
        await page.close()

    return result


# ── 登录 ──────────────────────────────────────────────────
async def login(url: str, account: dict, context: BrowserContext) -> list[dict]:
    """登录并返回 cookies"""
    page = await context.new_page()
    cookies = []
    try:
        # 找登录页
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await dismiss_modals(page)

        for kw in ["登录", "Login", "Sign in"]:
            el = page.locator(f"text={kw}").first
            if await el.count() > 0 and await el.is_visible():
                href = await el.get_attribute("href") or ""
                if href and not href.startswith("http"):
                    href = url.rstrip("/") + "/" + href.lstrip("/")
                if href:
                    await page.goto(href, timeout=10000)
                else:
                    await el.click()
                await page.wait_for_timeout(1500)
                break

        # 填登录表单
        inputs = await page.locator("input:visible").all()
        for inp in inputs:
            t  = await inp.get_attribute("type") or "text"
            nm = (await inp.get_attribute("name") or "").lower()
            ph = (await inp.get_attribute("placeholder") or "").lower()
            key = nm or ph

            if t == "email" or "email" in key or "邮箱" in key:
                await inp.fill(account["email"])
            elif "username" in key or "用户名" in key or "user" in key:
                await inp.fill(account.get("username", account["email"]))
            elif t == "password" or "password" in key or "密码" in key:
                await inp.fill(account["password"])

        for sel in ["button[type='submit']", "button:has-text('登录')",
                    "button:has-text('Login')", "input[type='submit']"]:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click()
                await page.wait_for_timeout(3000)
                break

        cookies = await context.cookies()

    except Exception as e:
        print(f"  登录异常: {e}")
    finally:
        await page.close()

    return cookies


# ── 主入口 ────────────────────────────────────────────────
async def ensure_logged_in(url: str) -> list[dict]:
    """确保站点已登录，返回有效 cookies"""
    account = get_account(url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )

        if not account:
            print(f"  自动注册 {url}...")
            account = await register(url, context)
            if account["success"]:
                save_account(account)
                print(f"  注册成功: {account['username']}")
            else:
                await browser.close()
                return []

        print(f"  登录 {url}...")
        cookies = await login(url, account, context)
        if cookies:
            save_cookies(url, cookies)
            print(f"  登录成功，保存 {len(cookies)} 个 cookie")

        await browser.close()
        return cookies


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://115.190.169.243"
    cookies = asyncio.run(ensure_logged_in(url))
    print(f"获得 {len(cookies)} 个 cookie")
