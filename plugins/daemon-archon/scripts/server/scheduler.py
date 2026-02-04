"""
daemon-archon APScheduler 调度器

基于 APScheduler 实现定时任务调度，借鉴 OpenClaw 的优秀设计
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from .types import TaskMode, TaskStatus, CronScheduleKind
from .state_store import (
    load_task_config, save_task_config, list_active_tasks,
    get_task_status, set_task_status, append_log
)

logger = logging.getLogger(__name__)


class ArchonScheduler:
    """
    Archon 调度器

    负责管理所有定时任务的调度，包括：
    - Probe 模式：定时检查 Probe 状态
    - Cron 模式：定时执行 Cron 任务
    """

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.running = False
        self._probe_callback: Optional[Callable] = None
        self._cron_callback: Optional[Callable] = None

    def configure(
        self,
        probe_callback: Optional[Callable] = None,
        cron_callback: Optional[Callable] = None
    ):
        """
        配置调度器回调

        Args:
            probe_callback: Probe 检查回调函数
            cron_callback: Cron 执行回调函数
        """
        self._probe_callback = probe_callback
        self._cron_callback = cron_callback

    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return

        # 创建调度器
        self.scheduler = AsyncIOScheduler(
            jobstores={
                'default': MemoryJobStore()
            },
            executors={
                'default': AsyncIOExecutor()
            },
            job_defaults={
                'coalesce': True,  # 合并错过的任务
                'max_instances': 1,  # 同一任务最多一个实例
                'misfire_grace_time': 60  # 错过执行的宽限时间（秒）
            }
        )

        # 恢复所有活跃任务
        await self._restore_active_tasks()

        # 启动调度器
        self.scheduler.start()
        self.running = True
        logger.info("Archon 调度器已启动")

    async def stop(self):
        """停止调度器"""
        if not self.running:
            return

        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            self.scheduler = None

        self.running = False
        logger.info("Archon 调度器已停止")

    async def _restore_active_tasks(self):
        """恢复所有活跃任务"""
        active_tasks = list_active_tasks()
        logger.info(f"恢复 {len(active_tasks)} 个活跃任务")

        for task in active_tasks:
            task_id = task.get("task_id")
            mode = task.get("mode")

            try:
                if mode == "probe":
                    await self.add_probe_task(task_id, task)
                elif mode == "cron":
                    await self.add_cron_task(task_id, task)
            except Exception as e:
                logger.error(f"恢复任务失败 [{task_id}]: {e}")

    async def add_probe_task(self, task_id: str, config: Optional[Dict[str, Any]] = None):
        """
        添加 Probe 监控任务

        Args:
            task_id: 任务 ID
            config: 任务配置（可选，如果不提供则从存储加载）
        """
        if not self.scheduler:
            raise RuntimeError("调度器未启动")

        if config is None:
            config = load_task_config(task_id)
            if not config:
                raise ValueError(f"任务配置不存在: {task_id}")

        # 获取检查间隔
        interval_minutes = config.get("schedule", {}).get("check_interval_minutes", 5)

        # 创建定时任务
        job_id = f"probe_{task_id}"

        # 移除已存在的任务
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # 添加新任务
        self.scheduler.add_job(
            self._execute_probe_check,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            args=[task_id],
            name=f"Probe 检查: {task_id}",
            replace_existing=True
        )

        logger.info(f"已添加 Probe 监控任务: {task_id}, 间隔: {interval_minutes} 分钟")

    async def add_cron_task(self, task_id: str, config: Optional[Dict[str, Any]] = None):
        """
        添加 Cron 定时任务

        Args:
            task_id: 任务 ID
            config: 任务配置（可选，如果不提供则从存储加载）
        """
        if not self.scheduler:
            raise RuntimeError("调度器未启动")

        if config is None:
            config = load_task_config(task_id)
            if not config:
                raise ValueError(f"任务配置不存在: {task_id}")

        # 获取调度配置
        schedule = config.get("schedule", {})
        cron_expression = schedule.get("cron_expression")
        interval_minutes = schedule.get("check_interval_minutes", 60)

        job_id = f"cron_{task_id}"

        # 移除已存在的任务
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        # 根据配置创建触发器
        if cron_expression:
            # 使用 Cron 表达式
            trigger = CronTrigger.from_crontab(cron_expression)
            logger.info(f"已添加 Cron 任务: {task_id}, 表达式: {cron_expression}")
        else:
            # 使用间隔触发
            trigger = IntervalTrigger(minutes=interval_minutes)
            logger.info(f"已添加 Cron 任务: {task_id}, 间隔: {interval_minutes} 分钟")

        # 添加任务
        self.scheduler.add_job(
            self._execute_cron_task,
            trigger=trigger,
            id=job_id,
            args=[task_id],
            name=f"Cron 任务: {task_id}",
            replace_existing=True
        )

    async def remove_task(self, task_id: str, mode: str):
        """
        移除任务

        Args:
            task_id: 任务 ID
            mode: 任务模式 (probe/cron)
        """
        if not self.scheduler:
            return

        job_id = f"{mode}_{task_id}"

        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除任务: {job_id}")

    async def pause_task(self, task_id: str, mode: str):
        """暂停任务"""
        if not self.scheduler:
            return

        job_id = f"{mode}_{task_id}"

        if self.scheduler.get_job(job_id):
            self.scheduler.pause_job(job_id)
            logger.info(f"已暂停任务: {job_id}")

    async def resume_task(self, task_id: str, mode: str):
        """恢复任务"""
        if not self.scheduler:
            return

        job_id = f"{mode}_{task_id}"

        if self.scheduler.get_job(job_id):
            self.scheduler.resume_job(job_id)
            logger.info(f"已恢复任务: {job_id}")

    async def trigger_task(self, task_id: str, mode: str):
        """立即触发任务"""
        if mode == "probe":
            await self._execute_probe_check(task_id)
        elif mode == "cron":
            await self._execute_cron_task(task_id)

    async def _execute_probe_check(self, task_id: str):
        """执行 Probe 检查"""
        logger.info(f"执行 Probe 检查: {task_id}")
        append_log(task_id, "ACTION", "触发定时检查")

        # 检查任务状态
        status = get_task_status(task_id)
        if status != "active":
            logger.info(f"任务 {task_id} 状态为 {status}，跳过检查")
            return

        # 调用回调函数
        if self._probe_callback:
            try:
                await self._probe_callback(task_id)
            except Exception as e:
                logger.error(f"Probe 检查失败 [{task_id}]: {e}")
                append_log(task_id, "ERROR", f"检查失败: {e}")

    async def _execute_cron_task(self, task_id: str):
        """执行 Cron 任务"""
        logger.info(f"执行 Cron 任务: {task_id}")
        append_log(task_id, "ACTION", "触发定时执行")

        # 检查任务状态
        status = get_task_status(task_id)
        if status != "active":
            logger.info(f"任务 {task_id} 状态为 {status}，跳过执行")
            return

        # 调用回调函数
        if self._cron_callback:
            try:
                await self._cron_callback(task_id)
            except Exception as e:
                logger.error(f"Cron 任务执行失败 [{task_id}]: {e}")
                append_log(task_id, "ERROR", f"执行失败: {e}")

    def get_job_info(self, task_id: str, mode: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        if not self.scheduler:
            return None

        job_id = f"{mode}_{task_id}"
        job = self.scheduler.get_job(job_id)

        if not job:
            return None

        return {
            "job_id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "pending": job.pending
        }

    def list_jobs(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        if not self.scheduler:
            return []

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "job_id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "pending": job.pending
            })

        return jobs


# 全局调度器实例
_scheduler: Optional[ArchonScheduler] = None


def get_scheduler() -> ArchonScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ArchonScheduler()
    return _scheduler
