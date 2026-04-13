"""
用 Playwright 模拟用户操作，在 SD WebUI / ComfyUI 页面上生图
自动识别页面类型，填入 prompt，点击生成，等待结果，保存图片
"""
import asyncio
import base64
import os
from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

PROMPT = "a cute cat sitting on a wooden table, soft lighting, photorealistic, 4k"
OUTPUT_DIR = "generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 各类页面的选择器策略
STRATEGIES = [
    {
        "name": "SD WebUI (Gradio)",
        "prompt_selector": [
            "#txt2img_prompt textarea",
            "textarea[placeholder*='prompt']",
            ".prompt textarea",
        ],
        "button_selector": [
            "#txt2img_generate",
            "button:has-text('Generate')",
            "button:has-text('生成')",
        ],
        "result_selector": [
            "#txt2img_gallery img",
            ".output-image img",
            ".gallery img",
        ],
    },
    {
        "name": "ComfyUI",
        "prompt_selector": [
            ".comfy-multiline-input",
            "textarea.comfy-multiline-input",
        ],
        "button_selector": [
            "button:has-text('Queue Prompt')",
            "#queue-button",
        ],
        "result_selector": [
            ".comfy-image-preview img",
            "canvas",
        ],
    },
    {
        "name": "通用生图页面",
        "prompt_selector": [
            "textarea[name='prompt']",
            "textarea[id='prompt']",
            "textarea[placeholder*='描述']",
            "textarea[placeholder*='输入']",
            "textarea[placeholder*='prompt']",
            "input[name='prompt']",
        ],
        "button_selector": [
            "button:has-text('生成')",
            "button:has-text('Generate')",
            "button:has-text('Create')",
            "button:has-text('立即生成')",
            "button:has-text('开始生成')",
            "button:has-text('Draw')",
        ],
        "result_selector": [
            "img.result",
            "img.output",
            "img.generated",
            ".result img",
            ".output img",
        ],
    },
]


async def try_fill_and_generate(page: Page, strategy: dict) -> str | None:
    """尝试一种策略，返回图片 base64 或 None"""
    # 找 prompt 输入框
    prompt_el = None
    for sel in strategy["prompt_selector"]:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                prompt_el = el
                break
        except Exception:
            continue

    if not prompt_el:
        return None

    # 填入 prompt
    try:
        await prompt_el.click()
        await prompt_el.fill(PROMPT)
    except Exception:
        return None

    # 找生成按钮
    btn = None
    for sel in strategy["button_selector"]:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                btn = el
                break
        except Exception:
            continue

    if not btn:
        return None

    print(f"    找到策略: {strategy['name']}，点击生成...")
    await btn.click()

    # 等待图片出现（最多 60 秒）
    for sel in strategy["result_selector"]:
        try:
            await page.wait_for_selector(sel, timeout=60000)
            el = page.locator(sel).first
            # 截图这个元素
            img_bytes = await el.screenshot()
            return base64.b64encode(img_bytes).decode()
        except PWTimeout:
            continue
        except Exception:
            continue

    return None


async def generate_on_site(url: str) -> dict:
    result = {"url": url, "success": False, "strategy": "", "image_path": ""}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = await context.new_page()

        try:
            print(f"  打开 {url} ...")
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)  # 等 JS 渲染

            for strategy in STRATEGIES:
                img_b64 = await try_fill_and_generate(page, strategy)
                if img_b64:
                    # 保存图片
                    fname = url.replace("https://", "").replace("/", "_").replace(":", "_") + ".png"
                    fpath = os.path.join(OUTPUT_DIR, fname)
                    with open(fpath, "wb") as f:
                        f.write(base64.b64decode(img_b64))
                    result["success"] = True
                    result["strategy"] = strategy["name"]
                    result["image_path"] = fpath
                    print(f"    ✅ 生图成功！保存至 {fpath}")
                    break

            if not result["success"]:
                # 截一张页面截图方便调试
                shot_path = os.path.join(OUTPUT_DIR, "debug_" + url.replace("https://", "").replace("/", "_") + ".png")
                await page.screenshot(path=shot_path, full_page=False)
                print(f"    ❌ 未能生图，页面截图: {shot_path}")

        except Exception as e:
            print(f"    ❌ 异常: {e}")
        finally:
            await browser.close()

    return result


async def main():
    import json

    # 取有生图功能的站点
    with open("checked.json") as f:
        data = json.load(f)

    # 优先取高置信度的
    try:
        with open("analyzed.json") as f:
            analyzed = {r["url"]: r for r in json.load(f)}
    except Exception:
        analyzed = {}

    candidates = [
        d["url"] for d in data
        if d.get("is_active") and d.get("text_to_image")
    ]

    # 按置信度排序
    candidates.sort(key=lambda u: {"high": 0, "medium": 1, "low": 2}.get(
        analyzed.get(u, {}).get("confidence", "low"), 2))

    print(f"共 {len(candidates)} 个候选站点，开始逐个尝试生图...\n")

    results = []
    for url in candidates[:20]:  # 先试前 20 个
        print(f"[{candidates.index(url)+1}] {url}")
        r = await generate_on_site(url)
        results.append(r)
        if r["success"]:
            print(f"\n🎉 成功找到可生图站点: {url}\n")
            break  # 找到一个就停

    success = [r for r in results if r["success"]]
    print(f"\n结果: 尝试 {len(results)} 个，成功 {len(success)} 个")
    if success:
        for r in success:
            print(f"  ✅ {r['url']} -> {r['image_path']}")


if __name__ == "__main__":
    asyncio.run(main())
