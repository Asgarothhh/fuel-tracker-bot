# src/app/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime, timedelta, timezone
import logging
from src.app.config import DATABASE_URL  # или путь к вашей БД
from src.app.jobs import run_import_job  # функция, описанная ниже

_scheduler = None

def init_scheduler():
    global _scheduler
    if _scheduler:
        return _scheduler
    jobstores = {
        'default': SQLAlchemyJobStore(url=DATABASE_URL)
    }
    _scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
    _scheduler.start()
    logging.getLogger(__name__).info("Scheduler started")
    return _scheduler

def schedule_daily_import(name: str, hour_utc: int, minute: int):
    """
    Добавляет/обновляет ежедневную задачу в планировщике.
    hour_utc/minute — время в UTC, job запускает run_import_job()
    """
    sched = init_scheduler()
    job_id = f"job_{name}"
    # удаляем старую задачу если есть
    try:
        sched.remove_job(job_id)
    except Exception:
        pass
    sched.add_job(run_import_job, 'cron', hour=hour_utc, minute=minute, id=job_id, args=[name], replace_existing=True)
    logging.getLogger(__name__).info("Scheduled job %s at %02d:%02d UTC", job_id, hour_utc, minute)

def remove_schedule(name: str):
    sched = init_scheduler()
    job_id = f"job_{name}"
    try:
        sched.remove_job(job_id)
    except Exception:
        pass
