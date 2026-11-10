from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: AsyncIOScheduler | None = None


def start_scheduler(pool) -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _daily_snapshot,
        CronTrigger(hour=23, minute=0),
        args=[pool],
        id="daily_snapshot",
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler


async def _daily_snapshot(pool) -> None:
    from ledger.chain import append_snapshot
    await append_snapshot(pool, lga_id=None)
