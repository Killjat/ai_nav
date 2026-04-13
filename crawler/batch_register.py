"""
批量注册账号，建立账号池
"""
import asyncio
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from account_manager import register, save_account, ACCOUNTS_FILE
from playwright.async_api import async_playwright

TARGET_URL = "https://115.190.169.243"
BATCH_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 5


async def main():
    print(f"批量注册 {BATCH_SIZE} 个账号...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

        success = 0
        for i in range(BATCH_SIZE):
            print(f"\n[{i+1}/{BATCH_SIZE}]")
            context = await browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            )
            result = await register(TARGET_URL, context)
            await context.close()

            if result["success"]:
                save_account(result)
                success += 1
                print(f"  ✅ {result['username']} / {result['password']}")
            else:
                print(f"  ❌ 失败: {result.get('error', '')}")

            # 避免频繁注册被封
            await asyncio.sleep(2)

        await browser.close()

    print(f"\n完成，成功注册 {success}/{BATCH_SIZE} 个账号")

    # 显示所有账号
    with open(ACCOUNTS_FILE) as f:
        accounts = json.load(f)
    site_accounts = [a for a in accounts if a["url"] == TARGET_URL and a.get("success")]
    print(f"该站点共有 {len(site_accounts)} 个账号")


asyncio.run(main())
