"""
daemon-archon FastAPI 服务入口

提供 HTTP API 和定时任务调度
"""

import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# 使用相对导入（需要以模块方式运行: python -m server.main）
from .scheduler import ArchonScheduler, get_scheduler
from .state_store import (
    load_global_settings, save_global_settings,
    load_task_config, list_all_tasks, list_active_tasks,
    get_task_status, set_task_status, read_log,
    ensure_base_dir
)
from .probe_executor import ProbeExecutor, probe_check_callback
from .cron_executor import CronExecutor, cron_execute_callback
from .stuck_detector import run_stuck_detection, handle_stuck_tasks
from .notifier import notify_service_status

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PID 文件路径
PID_FILE = Path.home() / ".claude" / "daemon-archon" / "archon.pid"


# ============ Pydantic 模型 ============

class ProbeCreateRequest(BaseModel):
    """创建 Probe 任务请求"""
    initial_prompt: str
    project_path: str
    name: Optional[str] = None
    description: Optional[str] = None
    check_interval_minutes: int = 5
    max_auto_corrections: int = 3


class CronCreateRequest(BaseModel):
    """创建 Cron 任务请求"""
    name: str
    description: str
    project_path: str
    task_content: str
    workflow_content: str
    cron_expression: Optional[str] = None
    check_interval_minutes: int = 60
    timeout_minutes: int = 10


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    mode: str
    name: str
    status: str
    created_at: str


class StatusResponse(BaseModel):
    """状态响应"""
    running: bool
    tasks_count: int
    active_tasks_count: int
    scheduler_jobs: List[Dict[str, Any]]


# ============ 生命周期管理 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Archon 服务启动中...")

    # 确保工作目录存在
    ensure_base_dir()

    # 写入 PID 文件
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

    # 配置并启动调度器
    scheduler = get_scheduler()
    scheduler.configure(
        probe_callback=probe_check_callback,
        cron_callback=cron_execute_callback
    )
    await scheduler.start()

    # 启动卡住检测定时任务
    asyncio.create_task(stuck_detection_loop())

    notify_service_status("已启动", f"PID: {os.getpid()}")
    logger.info("Archon 服务已启动")

    yield

    # 关闭时
    logger.info("Archon 服务关闭中...")
    await scheduler.stop()

    # 删除 PID 文件
    if PID_FILE.exists():
        PID_FILE.unlink()

    notify_service_status("已停止")
    logger.info("Archon 服务已停止")


async def stuck_detection_loop():
    """卡住检测循环"""
    while True:
        try:
            await asyncio.sleep(300)  # 每 5 分钟检测一次
            stuck_tasks = run_stuck_detection()
            if stuck_tasks:
                await handle_stuck_tasks(stuck_tasks)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"卡住检测失败: {e}")


# ============ FastAPI 应用 ============

app = FastAPI(
    title="daemon-archon",
    description="Claude Code 守护进程执政官",
    version="1.0.0",
    lifespan=lifespan
)


# ============ API 路由 ============

@app.get("/")
async def root():
    """根路由"""
    return {
        "name": "daemon-archon",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """获取服务状态"""
    scheduler = get_scheduler()
    all_tasks = list_all_tasks()
    active_tasks = list_active_tasks()

    return StatusResponse(
        running=scheduler.running,
        tasks_count=len(all_tasks),
        active_tasks_count=len(active_tasks),
        scheduler_jobs=scheduler.list_jobs()
    )


@app.get("/tasks")
async def list_tasks(mode: Optional[str] = None, status: Optional[str] = None):
    """列出所有任务"""
    tasks = list_all_tasks()

    if mode:
        tasks = [t for t in tasks if t.get("mode") == mode]

    if status:
        tasks = [t for t in tasks if t.get("state", {}).get("status") == status]

    return {"tasks": tasks}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    config = load_task_config(task_id)
    if not config:
        raise HTTPException(status_code=404, detail="任务不存在")

    return config


@app.get("/tasks/{task_id}/logs")
async def get_task_logs(task_id: str, lines: int = 100):
    """获取任务日志"""
    logs = read_log(task_id, lines)
    return {"logs": logs}


# ============ Probe 模式 API ============

@app.post("/probe/create")
async def create_probe(request: ProbeCreateRequest, background_tasks: BackgroundTasks):
    """创建 Probe 任务"""
    # 生成任务 ID
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_probe"

    executor = ProbeExecutor(task_id)

    try:
        config = await executor.start_probe(
            initial_prompt=request.initial_prompt,
            project_path=request.project_path,
            name=request.name or "",
            description=request.description or "",
            check_interval_minutes=request.check_interval_minutes,
            max_auto_corrections=request.max_auto_corrections
        )

        # 添加到调度器
        scheduler = get_scheduler()
        await scheduler.add_probe_task(task_id, config)

        return TaskResponse(
            task_id=task_id,
            mode="probe",
            name=config.get("name", ""),
            status="active",
            created_at=config.get("created_at", "")
        )

    except Exception as e:
        logger.error(f"创建 Probe 任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/probe/{task_id}/check")
async def check_probe(task_id: str):
    """手动检查 Probe 状态"""
    config = load_task_config(task_id)
    if not config or config.get("mode") != "probe":
        raise HTTPException(status_code=404, detail="Probe 任务不存在")

    executor = ProbeExecutor(task_id)
    result = await executor.check_probe()

    return {
        "task_id": task_id,
        "status": result.status,
        "summary": result.summary,
        "issues": result.issues,
        "progress": result.progress
    }


@app.post("/probe/{task_id}/stop")
async def stop_probe(task_id: str):
    """停止 Probe 任务"""
    config = load_task_config(task_id)
    if not config or config.get("mode") != "probe":
        raise HTTPException(status_code=404, detail="Probe 任务不存在")

    executor = ProbeExecutor(task_id)
    success = await executor.stop_probe()

    if success:
        # 从调度器移除
        scheduler = get_scheduler()
        await scheduler.remove_task(task_id, "probe")

    return {"success": success, "task_id": task_id}


# ============ Cron 模式 API ============

@app.post("/cron/create")
async def create_cron(request: CronCreateRequest):
    """创建 Cron 任务"""
    # 生成任务 ID
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_cron"

    executor = CronExecutor(task_id)

    try:
        config = await executor.create_cron_task(
            name=request.name,
            description=request.description,
            project_path=request.project_path,
            task_content=request.task_content,
            workflow_content=request.workflow_content,
            cron_expression=request.cron_expression,
            check_interval_minutes=request.check_interval_minutes,
            timeout_minutes=request.timeout_minutes
        )

        # 添加到调度器
        scheduler = get_scheduler()
        await scheduler.add_cron_task(task_id, config)

        return TaskResponse(
            task_id=task_id,
            mode="cron",
            name=config.get("name", ""),
            status="active",
            created_at=config.get("created_at", "")
        )

    except Exception as e:
        logger.error(f"创建 Cron 任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cron/{task_id}/execute")
async def execute_cron(task_id: str):
    """手动执行 Cron 任务"""
    config = load_task_config(task_id)
    if not config or config.get("mode") != "cron":
        raise HTTPException(status_code=404, detail="Cron 任务不存在")

    executor = CronExecutor(task_id)
    result = await executor.execute_cron()

    return {
        "task_id": task_id,
        "status": result.status,
        "summary": result.summary,
        "findings": result.findings,
        "metrics": result.metrics
    }


@app.post("/cron/{task_id}/stop")
async def stop_cron(task_id: str):
    """停止 Cron 任务"""
    config = load_task_config(task_id)
    if not config or config.get("mode") != "cron":
        raise HTTPException(status_code=404, detail="Cron 任务不存在")

    executor = CronExecutor(task_id)
    success = await executor.stop_cron()

    if success:
        # 从调度器移除
        scheduler = get_scheduler()
        await scheduler.remove_task(task_id, "cron")

    return {"success": success, "task_id": task_id}


@app.post("/cron/{task_id}/pause")
async def pause_cron(task_id: str):
    """暂停 Cron 任务"""
    config = load_task_config(task_id)
    if not config or config.get("mode") != "cron":
        raise HTTPException(status_code=404, detail="Cron 任务不存在")

    executor = CronExecutor(task_id)
    success = await executor.pause_cron()

    if success:
        scheduler = get_scheduler()
        await scheduler.pause_task(task_id, "cron")

    return {"success": success, "task_id": task_id}


@app.post("/cron/{task_id}/resume")
async def resume_cron(task_id: str):
    """恢复 Cron 任务"""
    config = load_task_config(task_id)
    if not config or config.get("mode") != "cron":
        raise HTTPException(status_code=404, detail="Cron 任务不存在")

    executor = CronExecutor(task_id)
    success = await executor.resume_cron()

    if success:
        scheduler = get_scheduler()
        await scheduler.resume_task(task_id, "cron")

    return {"success": success, "task_id": task_id}


# ============ 设置 API ============

@app.get("/settings")
async def get_settings():
    """获取全局设置"""
    return load_global_settings()


@app.put("/settings")
async def update_settings(settings: Dict[str, Any]):
    """更新全局设置"""
    success = save_global_settings(settings)
    if not success:
        raise HTTPException(status_code=500, detail="保存设置失败")
    return {"success": True}


# ============ 卡住检测 API ============

@app.get("/stuck")
async def check_stuck():
    """检查卡住的任务"""
    stuck_tasks = run_stuck_detection()
    return {
        "stuck_count": len(stuck_tasks),
        "stuck_tasks": [
            {
                "task_id": s.task_id,
                "task_mode": s.task_mode.value,
                "stuck_type": s.stuck_type,
                "stuck_duration_minutes": s.stuck_duration_minutes,
                "details": s.details
            }
            for s in stuck_tasks
        ]
    }


# ============ 入口点 ============

def main():
    """主入口"""
    import uvicorn

    # 获取配置
    settings = load_global_settings()
    host = os.environ.get("ARCHON_HOST", "127.0.0.1")
    port = int(os.environ.get("ARCHON_PORT", "8765"))

    logger.info(f"启动 Archon 服务: {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
