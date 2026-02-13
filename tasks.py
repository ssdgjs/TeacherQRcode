"""
定时任务 - 使用APScheduler
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建调度器
scheduler = AsyncIOScheduler()


# ==================== 定时任务 ====================
async def reset_daily_quotas_task():
    """
    每日重置免费额度
    每天凌晨0:00执行
    """
    try:
        from database import get_session
        from quota import reset_all_daily_quotas

        with next(get_session()) as session:
            count = reset_all_daily_quotas(session)
            logger.info(f"✅ 已重置 {count} 个用户的每日免费额度")

    except Exception as e:
        logger.error(f"❌ 重置免费额度失败: {e}")


async def cleanup_expired_homeworks_task():
    """
    清理过期作业
    每天凌晨1:00执行
    """
    try:
        from database import get_session
        from models import delete_expired_homeworks
        from pydantic_settings import BaseSettings

        class Settings(BaseSettings):
            data_retention_days: int = 30

        settings = Settings()

        with next(get_session()) as session:
            deleted_count = delete_expired_homeworks(session, days=settings.data_retention_days)
            logger.info(f"🗑️  已清理 {deleted_count} 条过期作业记录")

    except Exception as e:
        logger.error(f"❌ 清理过期作业失败: {e}")


# ==================== 调度器管理 ====================
def start_scheduler():
    """
    启动调度器
    """
    # 每日重置免费额度（每天0:00）
    scheduler.add_job(
        reset_daily_quotas_task,
        CronTrigger(hour=0, minute=0),
        id='reset_daily_quotas',
        name='重置每日免费额度',
        replace_existing=True
    )

    # 清理过期作业（每天1:00）
    scheduler.add_job(
        cleanup_expired_homeworks_task,
        CronTrigger(hour=1, minute=0),
        id='cleanup_expired_homeworks',
        name='清理过期作业',
        replace_existing=True
    )

    scheduler.start()
    logger.info("🕐 定时任务调度器已启动")


def stop_scheduler():
    """
    停止调度器
    """
    scheduler.shutdown()
    logger.info("🕐 定时任务调度器已停止")


def get_scheduler_info() -> dict:
    """
    获取调度器信息

    Returns:
        dict: 调度器状态和任务列表
    """
    jobs = scheduler.get_jobs()

    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
    }
