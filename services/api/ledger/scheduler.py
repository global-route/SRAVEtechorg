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
    _scheduler.add_job(
        _escalation_check,
        CronTrigger(hour=8, minute=0),
        args=[pool],
        id="escalation_check",
        replace_existing=True,
    )
    _scheduler.add_job(
        _anomaly_detection,
        CronTrigger(hour=7, minute=0),
        args=[pool],
        id="anomaly_detection",
        replace_existing=True,
    )
    _scheduler.add_job(
        _weekly_analytics_report,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        args=[pool],
        id="weekly_analytics_report",
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


async def _escalation_check(pool) -> None:
    """
    Flag assessments as escalated after 3 reminders unpaid (42 days since assessment).
    """
    result = await pool.execute(
        """
        UPDATE tax_assessments
        SET escalated = TRUE,
            escalated_at = NOW(),
            wa_status = 'escalated'
        WHERE wa_status = 'reminder_sent'
          AND assessed_at < NOW() - INTERVAL '42 days'
          AND escalated = FALSE
        """
    )
    log.info("escalation_check_complete", updated=result)


async def _anomaly_detection(pool) -> None:
    """
    Flag LGAs where monthly collections dropped >20% vs prior month.
    Writes to audit_log with action='anomaly_detected'.
    """
    from repository.gap import get_monthly_collections
    lga_rows = await pool.fetch("SELECT DISTINCT lga_id FROM detected_buildings")
    flagged = 0
    for row in lga_rows:
        lga_id = row["lga_id"]
        monthly = await get_monthly_collections(pool, lga_id)
        if len(monthly) < 2:
            continue
        current = monthly[-1]["total_ngn"]
        prior = monthly[-2]["total_ngn"]
        if prior > 0 and current < prior * 0.8:
            drop_pct = round((1 - current / prior) * 100, 1)
            await pool.execute(
                "INSERT INTO audit_log (actor, action, target_id, payload) VALUES ('system','anomaly_detected',$1,$2::jsonb)",
                lga_id,
                f'{{"drop_pct":{drop_pct},"current_ngn":{current},"prior_ngn":{prior}}}',
            )
            flagged += 1
    log.info("anomaly_detection_complete", flagged=flagged)


async def _weekly_analytics_report(pool) -> None:
    """
    Send weekly WhatsApp summary to all active municipal clients.
    """
    import os, httpx
    from repository.gap import get_daily_collections

    clients = await pool.fetch(
        "SELECT id, lga_id FROM clients WHERE scope='municipal' AND active=TRUE AND lga_id IS NOT NULL"
    )
    wa_url = f"https://graph.facebook.com/v19.0/{os.getenv('WA_PHONE_NUMBER_ID')}/messages"
    wa_token = os.getenv("WA_API_TOKEN", "")

    async with httpx.AsyncClient() as client:
        for c in clients:
            try:
                daily = await get_daily_collections(pool, c["lga_id"])
                this_week = sum(d["total_ngn"] for d in daily[:7])
                last_week = sum(d["total_ngn"] for d in daily[7:14])
                trend = "up" if this_week >= last_week else "down"
                msg = (
                    f"SRAVE Weekly Report — {c['lga_id']}\n"
                    f"This week: \u20a6{this_week:,.0f} ({trend} vs last week)\n"
                    f"Last week: \u20a6{last_week:,.0f}\n"
                    f"View full dashboard: https://dashboard.srave.io"
                )
                phone_row = await pool.fetchrow(
                    "SELECT owner_phone FROM tax_roll WHERE lga_id=$1 AND owner_phone IS NOT NULL LIMIT 1",
                    c["lga_id"],
                )
                if not phone_row:
                    continue
                await client.post(
                    wa_url,
                    json={"messaging_product": "whatsapp", "to": phone_row["owner_phone"],
                          "type": "text", "text": {"body": msg}},
                    headers={"Authorization": f"Bearer {wa_token}"},
                )
            except Exception as e:
                log.error("weekly_report_failed", lga_id=c["lga_id"], error=str(e))
    log.info("weekly_analytics_report_complete", clients=len(clients))
