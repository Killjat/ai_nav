"""
AI 生图 API 网关
POST /generate  → 生图
GET  /status    → 站点池状态
GET  /health    → 健康检查
"""
import asyncio
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .site_pool import SitePool
from .driver import PlaywrightDriver

# ── 站点池初始化 ──────────────────────────────────────────
pool = SitePool()
pool.add("https://42.193.219.6",      "ISUX AI生图")
pool.add("https://115.190.169.243",   "AI生图站")
# 后续发现更多可用站点，继续 pool.add(...)

driver = PlaywrightDriver()

# 任务存储（生产环境换 Redis）
tasks: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await driver.start()
    yield
    await driver.stop()


app = FastAPI(title="AI生图网关", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求/响应模型 ─────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 512
    height: int = 512


class GenerateResponse(BaseModel):
    task_id: str
    status: str          # pending / processing / done / failed
    image_url: str = ""
    error: str = ""


# ── 后台生图任务 ──────────────────────────────────────────
async def run_generate(task_id: str, prompt: str):
    tasks[task_id]["status"] = "processing"

    site = await pool.acquire()
    if not site:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = "暂无可用站点，请稍后重试"
        return

    try:
        result = await driver.generate(site.url, prompt)
        await pool.release(site, result["success"])

        if result["success"]:
            tasks[task_id]["status"] = "done"
            tasks[task_id]["image_url"] = result["image_url"]
        else:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = result["error"]
    except Exception as e:
        await pool.release(site, False)
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)


# ── 路由 ──────────────────────────────────────────────────
@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {"status": "pending", "image_url": "", "error": ""}
    background_tasks.add_task(run_generate, task_id, req.prompt)
    return GenerateResponse(task_id=task_id, status="pending")


@app.get("/task/{task_id}", response_model=GenerateResponse)
async def get_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "任务不存在")
    t = tasks[task_id]
    return GenerateResponse(
        task_id=task_id,
        status=t["status"],
        image_url=t.get("image_url", ""),
        error=t.get("error", ""),
    )


@app.post("/admin/reload")
async def reload_strategies():
    """热重载站点策略，discover 发现新站点后调用"""
    from .driver import reload_strategies as _reload
    _reload()
    return {"status": "ok", "sites": len(pool.status())}


@app.get("/status")
async def status():
    return {"sites": pool.status()}


@app.get("/health")
async def health():
    available = sum(1 for s in pool.status() if s["available"])
    return {"status": "ok", "available_sites": available}
