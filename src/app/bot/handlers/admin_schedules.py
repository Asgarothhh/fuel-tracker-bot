from aiogram import types
from aiogram.filters import Command

from src.app.db import get_db_session
from src.app.models import Schedule
from src.app.permissions import require_permission
from src.app.bot.utils import extract_args


@require_permission("admin:manage")
async def cmd_schedule_get(message: types.Message):
    with get_db_session() as db:
        rows = db.query(
            Schedule.name,
            Schedule.cron_hour,
            Schedule.cron_minute,
            Schedule.enabled,
            Schedule.last_run,
        ).order_by(Schedule.name).all()

        if not rows:
            await message.reply("Расписаний нет.")
            return

        lines = []
        for name, cron_hour, cron_minute, enabled, last_run in rows:
            last = last_run.isoformat() if last_run else "—"
            lines.append(
                f"{name}: {cron_hour:02d}:{cron_minute:02d} UTC — "
                f"{'вкл' if enabled else 'выкл'} (last_run: {last})"
            )

    await message.reply("\n".join(lines))


@require_permission("admin:manage")
async def cmd_schedule_set(message: types.Message):
    args = extract_args(message)
    parts = args.split()
    if len(parts) < 2:
        await message.reply("Использование: /schedule_set <name> <HH:MM UTC>")
        return
    name = parts[0]
    try:
        hh, mm = parts[1].split(":")
        hour = int(hh)
        minute = int(mm)
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError
    except Exception:
        await message.reply("Неверное время. Формат HH:MM (UTC).")
        return

    with get_db_session() as db:
        sched = db.query(Schedule).filter_by(name=name).first()
        if not sched:
            sched = Schedule(name=name, cron_hour=hour, cron_minute=minute, enabled=True)
            db.add(sched)
        else:
            sched.cron_hour = hour
            sched.cron_minute = minute
            sched.enabled = True
        db.commit()

    from src.app.scheduler import schedule_daily_import

    schedule_daily_import(name, hour, minute)
    await message.reply(f"Расписание {name} установлено на {hour:02d}:{minute:02d} UTC")


@require_permission("admin:manage")
async def cmd_schedule_remove(message: types.Message):
    args = extract_args(message).strip()
    if not args:
        await message.reply("Использование: /schedule_remove <name>")
        return
    name = args
    with get_db_session() as db:
        sched = db.query(Schedule).filter_by(name=name).first()
        if sched:
            db.delete(sched)
            db.commit()
    from src.app.scheduler import remove_schedule

    remove_schedule(name)
    await message.reply(f"Расписание {name} удалено.")


def register_schedule_handlers(dp):
    dp.message.register(cmd_schedule_get, Command(commands=["schedule_get"]))
    dp.message.register(cmd_schedule_set, Command(commands=["schedule_set"]))
    dp.message.register(cmd_schedule_remove, Command(commands=["schedule_remove"]))
