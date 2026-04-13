"""
自动发现可操作的生图站点
流程：FOFA 搜索 → Playwright 探测页面结构 → 尝试生图 → 记录成功的选择器
"""
import asyncio
import json
import os
import httpx
import base64
from datetime import datetime
from playwright.async_api import async_playwright, Page

# FOFA 搜索关键词组合
FOFA_QUERIES = [
    '"Stable Diffusion" && country="CN" && port="443" && status_code="200"',
    '"ComfyUI" && country="CN" && port="443" && status_code="200"',
    '"AI绘图" && country="CN" && port="443" && status_code="200"',
    '"文生图" && country="CN" && port="443" && status_code="200"',
    '"生图" && country="CN" && port="443" && status_code="200"',
]

TEST_PROMPT = "a cute cat, photorealistic, 4k"
RESULTS_FILE = "discovered_sites.json"
os.makedirs("generated/discovery", exist_ok=True)


# ── FOFA 搜索 ─────────────────────────────────────────────
def fofa_search(query: str, email: str, key: str, size: int = 200) -> list[str]:
    qb64 = base64.b64encode(query.encode()).decode()
    try:
        r = httpx.get("https://fofa.info/api/v1/search/all", params={
            "email": email, "key": key, "qbase64": qb64,
            "fields": "host,title", "size": size,
        }, timeout=15)
        data = r.json()
        if data.get("error"):
            return []
        INVALID = {"0.0.0.0", "127.0.0.1", "localhost"}
        results = []
        for row in data.get("results", []):
            host = row[0]
            if not host.startswith("http"):
                host = "https://" + host
            clean = host.replace("https://", "").replace("http://", "").split("/")[0]
            if not any(clean.startswith(inv) for inv in INVALID):
                results.append(host)
        return results
    except Exception as e:
        print(f"  FOFA 搜索失败: {e}")
        return []


# ── 页面结构探测 ──────────────────────────────────────────
async def probe_page_structure(page: Page, url: str) -> dict:
    """探测页面中所有可能的 prompt 输入框和生成按钮"""
    structure = {
        "url": url,
        "prompt_candidates": [],
        "button_candidates": [],
        "tabs": [],
        "needs_tab": False,
    }

    # 找所有 textarea
    tas = await page.locator("textarea").all()
    for ta in tas:
        try:
            ph = await ta.get_attribute("placeholder") or ""
            nm = await ta.get_attribute("name") or ""
            cls = await ta.get_attribute("class") or ""
            visible = await ta.is_visible()
            sel = f"textarea"
            if nm:
                sel = f"textarea[name='{nm}']"
            elif ph:
                sel = f"textarea[placeholder*='{ph[:20]}']"
            structure["prompt_candidates"].append({
                "selector": sel, "placeholder": ph, "visible": visible
            })
        except Exception:
            pass

    # 找所有按钮
    btns = await page.locator("button").all()
    for btn in btns:
        try:
            txt = (await btn.inner_text()).strip()
            onclick = await btn.get_attribute("onclick") or ""
            visible = await btn.is_visible()
            if txt:
                structure["button_candidates"].append({
                    "text": txt, "onclick": onclick, "visible": visible,
                    "selector": f"button[onclick='{onclick}']" if onclick else f"button:has-text('{txt[:20]}')"
                })
        except Exception:
            pass

    # 找导航 tab
    nav_items = await page.locator("a, li, [role=tab]").all()
    for item in nav_items[:30]:
        try:
            txt = (await item.inner_text()).strip()
            visible = await item.is_visible()
            if visible and txt and any(kw in txt for kw in ["生图", "绘图", "AI图", "Generate", "Draw", "Image"]):
                structure["tabs"].append(txt)
        except Exception:
            pass

    # 如果有 tab 且 prompt 不可见，说明需要先切 tab
    visible_prompts = [p for p in structure["prompt_candidates"] if p["visible"]]
    if structure["tabs"] and not visible_prompts:
        structure["needs_tab"] = True

    return structure


# ── 尝试生图 ──────────────────────────────────────────────
async def try_generate(page: Page, structure: dict) -> dict:
    result = {"success": False, "image_url": "", "prompt_sel": "", "button_sel": "", "tab": ""}

    # 如果需要切 tab，先点
    if structure["needs_tab"] and structure["tabs"]:
        for tab_text in structure["tabs"]:
            try:
                await page.locator(f"text={tab_text}").first.click()
                await page.wait_for_timeout(1500)
                result["tab"] = tab_text
                break
            except Exception:
                continue

    # 强制显示所有隐藏元素（针对 tab 切换后仍隐藏的情况）
    await page.evaluate("""
        document.querySelectorAll('textarea, button').forEach(el => {
            let cur = el;
            while (cur && cur !== document.body) {
                if (getComputedStyle(cur).display === 'none') {
                    cur.style.display = 'block';
                }
                cur = cur.parentElement;
            }
        });
    """)
    await page.wait_for_timeout(500)

    # 找可用的 prompt 输入框
    prompt_el = None
    prompt_sel = ""
    for candidate in structure["prompt_candidates"]:
        try:
            el = page.locator(candidate["selector"]).first
            if await el.count() > 0:
                await el.fill(TEST_PROMPT)
                prompt_el = el
                prompt_sel = candidate["selector"]
                break
        except Exception:
            continue

    if not prompt_el:
        return result

    # 找生成按钮（优先找生图相关的）
    btn_el = None
    btn_sel = ""
    priority_keywords = ["生成图片", "AI生图", "generateAiImage", "txt2img", "Generate Image"]
    normal_keywords = ["生成", "Generate", "Create", "Draw", "立即生成"]

    for keywords in [priority_keywords, normal_keywords]:
        for candidate in structure["button_candidates"]:
            if any(kw in candidate["text"] or kw in candidate["onclick"] for kw in keywords):
                try:
                    el = page.locator(candidate["selector"]).first
                    if await el.count() > 0:
                        await el.click()
                        btn_el = el
                        btn_sel = candidate["selector"]
                        break
                except Exception:
                    continue
        if btn_el:
            break

    if not btn_el:
        return result

    # 等待生成结果（最多 50 秒）
    print(f"    点击生成，等待结果...")
    await page.wait_for_timeout(45000)

    # 找结果图片
    imgs = await page.locator("img").all()
    for img in imgs:
        try:
            src = await img.get_attribute("src") or ""
            if src and len(src) > 30 and not src.startswith("data:image/svg"):
                if any(ext in src.lower() for ext in [".webp", ".png", ".jpg", ".jpeg", "cdn", "/image", "generated"]):
                    result["success"] = True
                    result["image_url"] = src
                    result["prompt_sel"] = prompt_sel
                    result["button_sel"] = btn_sel
                    break
        except Exception:
            pass

    return result


# ── 主流程 ────────────────────────────────────────────────
async def discover(email: str, api_key: str):
    # 加载已有结果
    existing = {}
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            for item in json.load(f):
                existing[item["url"]] = item

    # 从多个关键词搜索 URL
    all_urls = set()
    for query in FOFA_QUERIES:
        print(f"搜索: {query[:50]}...")
        urls = fofa_search(query, email, api_key, size=100)
        all_urls.update(urls)
        print(f"  获得 {len(urls)} 个 URL")

    # 过滤已处理的
    new_urls = [u for u in all_urls if u not in existing]
    print(f"\n共 {len(all_urls)} 个 URL，其中 {len(new_urls)} 个未处理\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )

        success_sites = []

        for i, url in enumerate(new_urls):
            print(f"[{i+1}/{len(new_urls)}] {url}")
            page = await context.new_page()
            record = {"url": url, "success": False, "checked_at": datetime.now().isoformat()}

            try:
                await page.goto(url, timeout=15000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                structure = await probe_page_structure(page, url)
                has_prompt = len(structure["prompt_candidates"]) > 0
                has_button = len(structure["button_candidates"]) > 0

                print(f"  prompt:{len(structure['prompt_candidates'])} btn:{len(structure['button_candidates'])} tab:{structure['tabs']}")

                if has_prompt and has_button:
                    gen_result = await try_generate(page, structure)
                    record.update(gen_result)
                    record["structure"] = structure

                    if gen_result["success"]:
                        print(f"  ✅ 生图成功！{gen_result['image_url'][:60]}")
                        success_sites.append(record)
                        # 保存截图
                        shot = f"generated/discovery/{url.replace('https://','').replace('/','_')}.png"
                        await page.screenshot(path=shot)
                    else:
                        print(f"  ❌ 未能生图")
                else:
                    print(f"  ⏭ 跳过（无输入框或按钮）")

            except Exception as e:
                print(f"  ❌ 异常: {str(e)[:60]}")
                record["error"] = str(e)
            finally:
                await page.close()

            existing[url] = record

            # 每处理 10 个保存一次
            if (i + 1) % 10 == 0:
                with open(RESULTS_FILE, "w") as f:
                    json.dump(list(existing.values()), f, ensure_ascii=False, indent=2)

        await browser.close()

    # 最终保存
    with open(RESULTS_FILE, "w") as f:
        json.dump(list(existing.values()), f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"发现 {len(success_sites)} 个可生图站点:")
    for s in success_sites:
        print(f"  ✅ {s['url']}")
        print(f"     prompt: {s.get('prompt_sel','')}")
        print(f"     button: {s.get('button_sel','')}")
        if s.get("tab"):
            print(f"     tab:    {s.get('tab','')}")

    return success_sites


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    email = os.getenv("FOFA_EMAIL", "")
    key = os.getenv("FOFA_KEY", "")
    if not email or not key:
        print("请配置 .env 中的 FOFA_EMAIL 和 FOFA_KEY")
        raise SystemExit(1)

    asyncio.run(discover(email, key))
