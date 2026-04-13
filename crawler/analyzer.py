"""
深度分析站点：
1. 是否真实支持生图（不只是关键词，而是找到实际的生成入口）
2. 是否有开放 API（探测常见 API 路径）
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup

# 常见 API 路径探测
API_PATHS = [
    "/api/generate",
    "/api/v1/generate",
    "/api/txt2img",
    "/api/img2img",
    "/api/image/generate",
    "/v1/images/generations",   # OpenAI 兼容
    "/api/v1/text-to-image",
    "/sdapi/v1/txt2img",        # Stable Diffusion WebUI
    "/api/draw",
    "/api/create",
    "/api/inference",
    "/docs",                    # FastAPI / Swagger
    "/swagger",
    "/openapi.json",
    "/api/docs",
]

# 页面中有这些元素说明真的有生图功能
REAL_FEATURE_SIGNALS = {
    "has_prompt_input": [
        'placeholder="prompt"',
        'placeholder="输入提示词"',
        'placeholder="描述你想要的图片"',
        'name="prompt"',
        'id="prompt"',
        'class="prompt"',
        "textarea",
    ],
    "has_generate_button": [
        "生成", "Generate", "Create", "Draw", "立即生成", "开始生成",
    ],
    "has_image_output": [
        'class="result"', 'id="result"', 'class="output"',
        'class="generated"', "canvas", "result-image",
    ],
}

# API 响应特征（说明是真实 API）
API_RESPONSE_SIGNALS = [
    "application/json",
    '"model"',
    '"images"',
    '"data"',
    '"url"',
    "swagger",
    "openapi",
    "ReDoc",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}


async def probe_api(session: aiohttp.ClientSession, base_url: str) -> dict:
    """探测站点是否有可用 API"""
    found_paths = []
    swagger_url = ""

    for path in API_PATHS:
        url = base_url.rstrip("/") + path
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6), ssl=False, headers=HEADERS) as resp:
                if resp.status in (200, 405, 422):  # 405/422 说明路由存在但方法不对
                    content_type = resp.headers.get("content-type", "")
                    body = await resp.text(errors="ignore")

                    is_api = (
                        "json" in content_type or
                        any(s.lower() in body.lower() for s in API_RESPONSE_SIGNALS)
                    )
                    if is_api:
                        found_paths.append(path)
                        if path in ("/docs", "/swagger", "/openapi.json", "/api/docs"):
                            swagger_url = url
        except Exception:
            continue

    return {
        "has_api": len(found_paths) > 0,
        "api_paths": found_paths,
        "swagger_url": swagger_url,
    }


async def deep_check_features(session: aiohttp.ClientSession, url: str) -> dict:
    """深度检测页面是否真的有生图功能"""
    result = {
        "has_prompt_input": False,
        "has_generate_button": False,
        "has_image_output": False,
        "confidence": "low",  # low / medium / high
    }
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), ssl=False, headers=HEADERS) as resp:
            if resp.status != 200:
                return result
            html = await resp.text(errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            text = html.lower()

            # 检测 prompt 输入框
            for signal in REAL_FEATURE_SIGNALS["has_prompt_input"]:
                if signal.lower() in text:
                    result["has_prompt_input"] = True
                    break

            # 检测生成按钮
            buttons = soup.find_all(["button", "input", "a"])
            for btn in buttons:
                btn_text = btn.get_text(strip=True)
                if any(s in btn_text for s in REAL_FEATURE_SIGNALS["has_generate_button"]):
                    result["has_generate_button"] = True
                    break

            # 检测图片输出区域
            for signal in REAL_FEATURE_SIGNALS["has_image_output"]:
                if signal.lower() in text:
                    result["has_image_output"] = True
                    break

            # 综合置信度
            score = sum([
                result["has_prompt_input"],
                result["has_generate_button"],
                result["has_image_output"],
            ])
            result["confidence"] = ["low", "low", "medium", "high"][score]

    except Exception:
        pass
    return result


async def analyze_one(session: aiohttp.ClientSession, url: str) -> dict:
    feature_task = deep_check_features(session, url)
    api_task = probe_api(session, url)
    features, api = await asyncio.gather(feature_task, api_task)
    return {"url": url, **features, **api}


async def analyze_all(urls: list[str], concurrency: int = 10) -> list[dict]:
    connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [analyze_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)


if __name__ == "__main__":
    import json, sys

    # 从数据库或 checked.json 读取在线站点
    input_file = sys.argv[1] if len(sys.argv) > 1 else "checked.json"
    with open(input_file) as f:
        data = json.load(f)

    urls = [d["url"] for d in data if d.get("is_active")]
    print(f"深度分析 {len(urls)} 个在线站点...")

    results = asyncio.run(analyze_all(urls))

    # 统计
    has_api    = [r for r in results if r["has_api"]]
    high_conf  = [r for r in results if r["confidence"] == "high"]
    mid_conf   = [r for r in results if r["confidence"] == "medium"]

    print(f"\n高置信度生图站点: {len(high_conf)}")
    print(f"中置信度生图站点: {len(mid_conf)}")
    print(f"有开放 API 的站点: {len(has_api)}")

    print("\n=== 有 API 的站点 ===")
    for r in has_api:
        print(f"  {r['url']}")
        print(f"    路径: {r['api_paths']}")
        if r['swagger_url']:
            print(f"    文档: {r['swagger_url']}")

    with open("analyzed.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n结果已写入 analyzed.json")
