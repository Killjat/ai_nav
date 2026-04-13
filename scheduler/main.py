"""
定时任务调度器
"""
import logging
import os
import sys
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scheduler.log"),
    ]
)
logger = logging.getLogger("scheduler")

from tasks import run_full_discovery, run_health_check

scheduler = BlockingScheduler(timezone="Asia/Shanghai")

# 每天凌晨 2 点：完整发现流程
scheduler.add_job(
    run_full_discovery,
    CronTrigger(hour=2, minute=0),
    id="full_discovery",
    name="完整发现流程",
    max_instances=1,
    misfire_grace_time=3600,
)

# 每小时：健康检查
scheduler.add_job(
    run_health_check,
    IntervalTrigger(hours=1),
    id="health_check",
    name="站点健康检查",
    max_instances=1,
    misfire_grace_time=300,
)

if __name__ == "__main__":
    logger.info("调度器启动")
    logger.info("  - 完整发现: 每天 02:00")
    logger.info("  - 健康检查: 每小时")

    # 启动时立即跑一次健康检查
    run_health_check()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("调度器停止")
