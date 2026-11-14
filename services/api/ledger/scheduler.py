import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = structlog.get_logger()
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
    _scheduler.add_job(
        _payment_reminders,
        CronTrigger(hour=9, minute=0),
        args=[pool],
        id="payment_reminders",
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler


async def _daily_snapshot(pool) -> None:
    from ledger.chain import append_snapshot
    await append_snapshot(pool, lga_id=None)
    log.info("daily_snapshot_complete")


async def _payment_reminders(pool) -> None:
    """
    Re-send WhatsApp demand notice for assessments delivered but unpaid after 14 days.
    Updates wa_status to 'reminder_sent'.
    """
    import os, httpx
    rows = await pool.fetch(
        """
        SELECT ta.id, ta.owner_phone, ta.amount_due, ta.payment_ref,
               tr.owner_name, tr.address, db.lga_id
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        LEFT JOIN tax_roll tr ON tr.owner_phone = ta.owner_phone AND tr.lga_id = db.lga_id
        WHERE ta.wa_status = 'delivered'
          AND ta.assessed_at < NOW() - INTERVAL '14 days'
        LIMIT 500
        """
    )
    if not rows:
        return

    wa_url = f"https://graph.facebook.com/v19.0/{os.getenv('WA_PHONE_NUMBER_ID')}/messages"
    wa_token = os.getenv("WA_API_TOKEN", "")
    sent = 0

    async with httpx.AsyncClient() as client:
        for row in rows:
            try:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": row["owner_phone"],
                    "type": "template",
                    "template": {
                        "name": "tax_payment_reminder",
                        "language": {"code": "en"},
                        "components": [{
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": row["owner_name"] or "Property Owner"},
                                {"type": "text", "text": row["address"] or row["lga_id"]},
                                {"type": "text", "text": f"{float(row['amount_due']):,.0f}"},
                                {"type": "text", "text": row["payment_ref"] or ""},
                            ],
                        }],
                    },
                }
                r = await client.post(wa_url, json=payload,
                                      headers={"Authorization": f"Bearer {wa_token}"})
                if r.status_code == 200:
                    await pool.execute(
                        "UPDATE tax_assessments SET wa_status='reminder_sent' WHERE id=$1",
                        row["id"],
                    )
                    sent += 1
            except Exception as e:
                log.error("reminder_send_failed", assessment_id=row["id"], error=str(e))

    log.info("payment_reminders_complete", sent=sent, total=len(rows))
