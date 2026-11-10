import asyncpg


async def get_metrics(pool: asyncpg.Pool, lga_id: str | None = None) -> dict:
    where = "WHERE db.lga_id = $1" if lga_id else ""
    args = [lga_id] if lga_id else []

    row = await pool.fetchrow(
        f"""
        SELECT
            COUNT(db.id)                                                            AS total,
            COUNT(CASE WHEN db.verified THEN 1 END)                                 AS verified,
            COALESCE(SUM(CASE WHEN ta.wa_status='paid' THEN ta.amount_due END), 0)  AS collected_current,
            COALESCE(SUM(CASE WHEN ta.wa_status='paid'
                AND ta.assessed_at < NOW() - INTERVAL '1 year'
                THEN ta.amount_due END), 0)                                         AS collected_prior
        FROM detected_buildings db
        LEFT JOIN tax_assessments ta ON ta.building_id = db.id
        {where}
        """,
        *args,
    )

    total = row["total"] or 0
    verified = row["verified"] or 0
    collected_current = float(row["collected_current"] or 0)
    collected_prior = float(row["collected_prior"] or 0)

    formalization_index = round(verified / total, 4) if total else 0.0
    igr_growth = round(
        (collected_current - collected_prior) / collected_prior, 4
    ) if collected_prior else 0.0

    chain_row = await pool.fetchrow(
        "SELECT ledger_entry_hash FROM audit_snapshots "
        + ("WHERE lga_id=$1 " if lga_id else "")
        + "ORDER BY snapshot_date DESC LIMIT 1",
        *args,
    )
    chain_head = chain_row["ledger_entry_hash"] if chain_row else "genesis"

    return {
        "property_formalization_index": formalization_index,
        "digitized_cadastral_records": total,
        "igr_growth_rate_yoy": igr_growth,
        "chain_head_hash": chain_head,
    }


async def get_ocds_export(pool: asyncpg.Pool, lga_id: str) -> list:
    rows = await pool.fetch(
        """
        SELECT ta.id, ta.amount_due, ta.wa_status, ta.assessed_at, db.lga_id, db.property_type
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        WHERE db.lga_id = $1
        """,
        lga_id,
    )
    return [
        {
            "ocid": f"ocds-srave-{r['lga_id']}-{r['id']}",
            "amount": {"amount": float(r["amount_due"]), "currency": "NGN"},
            "status": r["wa_status"],
            "date": r["assessed_at"].isoformat() if r["assessed_at"] else None,
            "property_type": r["property_type"],
        }
        for r in rows
    ]
