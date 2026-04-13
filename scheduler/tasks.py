"""
所有定时任务的具体实现
"""
import asyncio
import json
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crawler.fofa_fetch import fetch as fofa_fetch, save_urls
from crawler.checker import check_all, normalize_url
from crawler.analyzer import analyze_all
from backend.database import SessionLocal, engine
from backend.models import Base, Site

Base.metadata.create_all(bind=engine)

logger = logging.getLogger("scheduler")

WORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── 工具函数 ──────────────────────────────────────────────

def get_db():
    return SessionLocal()


def _import_checked(data: list[dict]) -> int:
    """将 checker 结果写入数据库，返回新增数量"""
    from datetime import datetime as dt
    db = get_db()
    added = 0
    for item in data:
        if not item["is_active"]:
            continue
        if not any([item["text_to_image"], item["image_edit"], item["video_gen"]]):
            continue
        site_data = {k: v for k, v in item.items() if hasattr(Site, k)}
        if isinstance(site_data.get("last_checked"), str):
            site_data["last_checked"] = dt.fromisoformat(site_data["last_checked"])
        existing = db.query(Site).filter(Site.url == item["url"]).first()
        if existing:
            for k, v in site_data.items():
                setattr(existing, k, v)
        else:
            db.add(Site(**site_data))
            added += 1
    db.commit()
    db.close()
    return added


def _import_analysis(data: list[dict]):
    """将 analyzer 结果写入数据库"""
    db = get_db()
    for item in data:
        site = db.query(Site).filter(Site.url == item["url"]).first()
        if not site:
            continue
        site.has_api     = item.get("has_api", False)
        site.api_paths   = item.get("api_paths", [])
        site.swagger_url = item.get("swagger_url", "")
        site.confidence  = item.get("confidence", "low")
    db.commit()
    db.close()


def _sync_gateway(discovered: list[dict]):
    """将发现的可生图站点写入网关策略文件"""
    strategies_file = os.path.join(WORK_DIR, "gateway", "strategies.json")
    existing = {}
    if os.path.exists(strategies_file):
        with open(strategies_file) as f:
            existing = json.load(f)

    for site in discovered:
        if not site.get("success"):
            continue
        url = site["url"]
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]
        existing[domain] = {
            "name": domain,
            "url": url,
            "tab_text": site.get("tab", ""),
            "prompt_selector": site.get("prompt_sel", ""),
            "button_selector": site.get("button_sel", ""),
            "wait_ms": 40000,
            "force_show": True,
        }
        logger.info(f"新增网关站点: {domain}")

    os.makedirs(os.path.dirname(strategies_file), exist_ok=True)
    with open(strategies_file, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    # 通知网关热重载
    try:
        import httpx
        httpx.post("http://127.0.0.1:8001/admin/reload", timeout=5)
        logger.info("网关策略已热重载")
    except Exception:
        logger.warning("网关热重载失败（网关可能未启动）")


# ── 定时任务 ──────────────────────────────────────────────

async def task_full_discovery():
    """完整发现流程：FOFA → 检测 → 入库 → 分析 → 生图探测 → 同步网关"""
    logger.info("=== 开始完整发现流程 ===")

    email = os.getenv("FOFA_EMAIL", "")
    key   = os.getenv("FOFA_KEY", "")
    if not email or not key:
        logger.error("未配置 FOFA_EMAIL / FOFA_KEY")
        return

    # 1. FOFA 搜索
    logger.info("Step 1: FOFA 搜索...")
    from dotenv import load_dotenv
    load_dotenv(os.path.join(WORK_DIR, ".env"))

    try:
        results = fofa_fetch(email, key, size=500)
        urls = [r["url"] for r in results]
        logger.info(f"  获得 {len(urls)} 个 URL")
    except Exception as e:
        logger.error(f"  FOFA 搜索失败: {e}")
        return

    # 2. 存活检测
    logger.info("Step 2: 存活检测...")
    checked = await check_all(urls, concurrency=30)
    active = [c for c in checked if c["is_active"]]
    logger.info(f"  在线: {len(active)} / {len(checked)}")

    # 3. 入库
    logger.info("Step 3: 入库...")
    added = _import_checked(checked)
    logger.info(f"  新增: {added} 条")

    # 4. 深度分析
    logger.info("Step 4: 深度分析...")
    active_urls = [c["url"] for c in active]
    analyzed = await analyze_all(active_urls, concurrency=10)
    _import_analysis(analyzed)
    has_api = sum(1 for a in analyzed if a.get("has_api"))
    logger.info(f"  有 API: {has_api} 个")

    # 5. Playwright 生图探测
    logger.info("Step 5: 生图探测...")
    from crawler.discover import discover
    discovered = await discover(email, key)
    logger.info(f"  发现可生图站点: {len(discovered)} 个")

    # 6. 同步网关
    if discovered:
        logger.info("Step 6: 同步网关...")
        _sync_gateway(discovered)

    logger.info("=== 完整发现流程完成 ===")


async def task_health_check():
    """每小时检测已入库站点是否还在线"""
    logger.info("健康检查开始...")
    import aiohttp

    db = get_db()
    sites = db.query(Site).filter(Site.is_active == True).all()
    urls = [s.url for s in sites]
    db.close()

    if not urls:
        return

    checked = await check_all(urls, concurrency=20)
    checked_map = {c["url"]: c for c in checked}

    db = get_db()
    offline = 0
    for site in db.query(Site).all():
        result = checked_map.get(site.url)
        if result:
            site.is_active = result["is_active"]
            site.last_checked = datetime.utcnow()
            if not result["is_active"]:
                offline += 1
    db.commit()
    db.close()

    logger.info(f"健康检查完成，下线: {offline} 个")


def run_full_discovery():
    asyncio.run(task_full_discovery())


def run_health_check():
    asyncio.run(task_health_check())
