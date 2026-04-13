"""
功能检测器：对 URL 列表做并发检测，识别支持的 AI 功能
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

FEATURES = {
    "text_to_image": [
        "文生图", "文本生图", "text to image", "txt2img",
        "generate image", "输入提示词", "生成图片", "AI绘图",
    ],
    "image_edit": [
        "图生图", "img2img", "图片编辑", "inpaint", "局部重绘",
        "图片修改", "edit image", "垫图",
    ],
    "video_gen": [
        "生成视频", "文生视频", "图生视频", "video generation",
        "text to video", "视频生成", "AI视频",
    ],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    )
}


async def check_one(session: aiohttp.ClientSession, url: str) -> dict:
    result = {
        "url": url,
        "title": "",
        "description": "",
        "is_active": False,
        "text_to_image": False,
        "image_edit": False,
        "video_gen": False,
        "last_checked": datetime.utcnow().isoformat(),
    }
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=12), ssl=False, headers=HEADERS
        ) as resp:
            if resp.status != 200:
                return result
            result["is_active"] = True
            html = await resp.text(errors="ignore")
            soup = BeautifulSoup(html, "html.parser")

            # 标题
            if soup.title:
                result["title"] = soup.title.string.strip()

            # description meta
            meta = soup.find("meta", attrs={"name": "description"})
            if meta:
                result["description"] = meta.get("content", "")

            # 功能匹配
            text = html.lower()
            for feature, keywords in FEATURES.items():
                if any(kw.lower() in text for kw in keywords):
                    result[feature] = True

    except Exception:
        pass
    return result


async def check_all(urls: list[str], concurrency: int = 20) -> list[dict]:
    connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return ""
    if not raw.startswith("http"):
        raw = "https://" + raw
    return raw


def load_urls(filepath: str) -> list[str]:
    with open(filepath) as f:
        return [u for line in f if (u := normalize_url(line))]


if __name__ == "__main__":
    import sys, json

    path = sys.argv[1] if len(sys.argv) > 1 else "urls.txt"
    urls = load_urls(path)
    print(f"检测 {len(urls)} 个站点...")
    results = asyncio.run(check_all(urls))

    with open("checked.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("结果已写入 checked.json")
