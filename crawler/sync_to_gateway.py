"""
把 discovered_sites.json 中成功的站点同步到网关的 site_pool
自动生成 SITE_STRATEGIES 配置
"""
import json, sys, os
sys.path.append("..")

DISCOVERED_FILE = "discovered_sites.json"
STRATEGIES_FILE = "gateway/strategies.json"


def sync():
    if not os.path.exists(DISCOVERED_FILE):
        print("未找到 discovered_sites.json，请先运行 discover.py")
        return

    with open(DISCOVERED_FILE) as f:
        data = json.load(f)

    success = [d for d in data if d.get("success")]
    print(f"发现 {len(success)} 个可用站点")

    strategies = {}
    for site in success:
        url = site["url"]
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        strategies[domain] = {
            "name": site.get("title", domain),
            "url": url,
            "tab_text": site.get("tab", ""),
            "prompt_selector": site.get("prompt_sel", ""),
            "button_selector": site.get("button_sel", ""),
            "wait_ms": 40000,
            "force_show": True,
        }
        print(f"  + {domain}")

    os.makedirs("gateway", exist_ok=True)
    with open(STRATEGIES_FILE, "w") as f:
        json.dump(strategies, f, ensure_ascii=False, indent=2)

    print(f"\n已写入 {STRATEGIES_FILE}")
    print("重启网关后生效")


if __name__ == "__main__":
    sync()
