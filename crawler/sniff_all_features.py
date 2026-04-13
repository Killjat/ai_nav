"""
逐个访问每个功能页面，触发请求，抓取完整接口参数
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright

os.makedirs("generated/sniff", exist_ok=True)

BASE = "https://115.190.169.243"

PAGES = [
    {"name": "即梦视频",   "url": f"{BASE}/video.php"},
    {"name": "Veo视频",    "url": f"{BASE}/veo_video.php"},
    {"name": "Wan视频",    "url": f"{BASE}/wan_video.php"},
    {"name": "文本转语音", "url": f"{BASE}/tts.php"},
    {"name": "文生图",     "url": f"{BASE}/index.php"},
]

with open("generated/accounts/115.190.169.243_cookies.json") as f:
    cookies = json.load(f)


async def sniff_page(context, page_info: dict) -> dict:
    name = page_info["name"]
    url  = page_info["url"]
    captured_requests = []
    captured_responses = []

    page = await context.new_page()

    async def on_request(req):
        if req.resource_type in ("xhr", "fetch"):
            try:
                captured_requests.append({
                    "method": req.method,
                    "url": req.url,
                    "post_data": req.post_data or "",
                    "headers": {k: v for k, v in req.headers.items()
                                if k.lower() not in ("cookie",)},
                })
            except Exception:
                pass

    async def on_response(resp):
        if resp.request.resource_type in ("xhr", "fetch"):
            try:
                body = await resp.text()
                captured_responses.append({
                    "url": resp.url,
                    "status": resp.status,
                    "body": body[:800],
                })
            except Exception:
                pass

    page.on("request", on_request)
    page.on("response", on_response)

    print(f"\n{'='*50}")
    print(f"[{name}] {url}")

    try:
        await page.goto(url, timeout=15000, wait_until="domcontentloaded")
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

        await page.screenshot(path=f"generated/sniff/{name}.png")

        # 分析表单
        inputs = await page.locator("input:visible, textarea:visible, select:visible").all()
        print("表单字段:")
        for inp in inputs:
            tag = await inp.evaluate("el => el.tagName.toLowerCase()")
            t   = await inp.get_attribute("type") or tag
            nm  = await inp.get_attribute("name") or ""
            ph  = await inp.get_attribute("placeholder") or ""
            val = await inp.get_attribute("value") or ""
            print(f"  [{t}] name={repr(nm)} placeholder={repr(ph[:30])} value={repr(val[:20])}")

        # 找隐藏的 input（包含 model/type 等关键参数）
        hidden_inputs = await page.locator("input[type='hidden']").all()
        print("隐藏字段:")
        for inp in hidden_inputs:
            nm  = await inp.get_attribute("name") or ""
            val = await inp.get_attribute("value") or ""
            print(f"  [hidden] name={repr(nm)} value={repr(val)}")

        # 填写并提交
        ta = page.locator("textarea:visible").first
        if await ta.count() > 0:
            await ta.fill("a cat walking in the forest, cinematic style")

        # 找提交按钮
        for kw in ["生成", "Generate", "提交", "开始", "转换", "合成"]:
            btn = page.locator(f"button:has-text('{kw}'):visible").first
            if await btn.count() > 0:
                print(f"点击: {kw}")
                await btn.click()
                await page.wait_for_timeout(4000)
                break

        # 等待响应
        await page.wait_for_timeout(3000)

    except Exception as e:
        print(f"  异常: {e}")
    finally:
        await page.close()

    # 整理结果
    post_requests = [r for r in captured_requests if r["method"] == "POST"]
    print(f"\n捕获 POST 请求 {len(post_requests)} 个:")
    for req in post_requests:
        print(f"  {req['url']}")
        print(f"  body: {req['post_data'][:300]}")

    return {
        "name": name,
        "url": url,
        "requests": post_requests,
        "responses": captured_responses,
    }


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        )
        await context.add_cookies(cookies)

        all_results = []
        for page_info in PAGES:
            result = await sniff_page(context, page_info)
            all_results.append(result)

        await browser.close()

    with open("generated/sniff/all_apis.json", "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print("\n\n完整结果已保存: generated/sniff/all_apis.json")

    # 汇总
    print("\n\n=== API 汇总 ===")
    for r in all_results:
        print(f"\n[{r['name']}]")
        for req in r["requests"]:
            print(f"  POST {req['url']}")
            # 解析 FormData
            body = req["post_data"]
            import re
            params = re.findall(r'name="(\w+)"\r\n\r\n([^\r\n-]+)', body)
            for k, v in params:
                print(f"    {k} = {repr(v)}")


asyncio.run(main())
