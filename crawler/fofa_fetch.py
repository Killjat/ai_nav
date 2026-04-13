"""
FOFA API 搜索，查询生图相关站点
文档: https://fofa.info/api
"""
import httpx
import base64
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

FOFA_API = "https://fofa.info/api/v1/search/all"
QUERY = '生图 && country="CN" && port="443" && status_code="200"'


def fetch(email: str, api_key: str, size: int = 500) -> list[str]:
    qb64 = base64.b64encode(QUERY.encode()).decode()
    params = {
        "email": email,
        "key": api_key,
        "qbase64": qb64,
        "fields": "host,title",
        "size": size,
        "full": "false",
    }
    resp = httpx.get(FOFA_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("error"):
        raise RuntimeError(f"FOFA 错误: {data.get('errmsg')}")

    # results 是 [[host, title], ...]，host 已含协议
    INVALID = {"0.0.0.0", "127.0.0.1", "localhost", "::1"}
    results = []
    for row in data.get("results", []):
        host, title = row[0], row[1] if len(row) > 1 else ""
        if not host.startswith("http"):
            host = "https://" + host
        # 过滤无效地址
        clean = host.replace("https://", "").replace("http://", "").split("/")[0]
        if any(clean.startswith(inv) for inv in INVALID):
            continue
        results.append({"url": host, "title": title})
    print(f"FOFA 返回 {len(results)} 条结果")
    return results


def save_urls(results: list[dict], path: str = "urls.txt"):
    with open(path, "w") as f:
        for r in results:
            f.write(r["url"] + "\n")
    print(f"已写入 {path}")


if __name__ == "__main__":
    email   = os.getenv("FOFA_EMAIL", "")
    api_key = os.getenv("FOFA_KEY", "")
    if not email or not api_key:
        print("请先在 .env 文件中配置 FOFA_EMAIL 和 FOFA_KEY")
        raise SystemExit(1)
    hosts = fetch(email, api_key)
    save_urls(hosts, "urls.txt")
