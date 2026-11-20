import asyncpg


async def get_gap_analysis(pool: asyncpg.Pool, lga_id: str) -> dict | None:
    row = await pool.fetchrow(
        """
        SELECT
            COUNT(db.id)                                                AS total_detected,
            COUNT(tr.id)                                                AS registered,
            COUNT(db.id) - COUNT(tr.id)                                 AS gap,
            COALESCE(SUM(COALESCE(tr2.annual_rate_ngn, 30000)), 0)      AS estimated_gap_ngn
        FROM detected_buildings db
        LEFT JOIN tax_roll tr
            ON ST_DWithin(db.footprint::geography, tr.geom::geography, 15)
        LEFT JOIN tax_rates tr2
            ON tr2.lga_id = db.lga_id AND tr2.property_type = db.property_type
        WHERE db.lga_id = $1
          AND db.verified = true
        """,
        lga_id,
    )
    if not row:
        return None
    total = row["total_detected"] or 0
    registered = row["registered"] or 0
    gap = row["gap"] or 0
    return {
        "lga_id": lga_id,
        "total_detected_buildings": total,
        "registered_tax_payers": registered,
        "unregistered_gap": gap,
        "estimated_annual_revenue_gap_ngn": float(row["estimated_gap_ngn"] or 0),
        "compliance_percentage": round((registered / total * 100) if total else 0, 2),
    }


async def get_daily_collections(pool: asyncpg.Pool, lga_id: str) -> list:
    rows = await pool.fetch(
        """
        SELECT
            DATE(ta.assessed_at)            AS day,
            COALESCE(SUM(ta.amount_paid), 0) AS total_ngn,
            COUNT(ta.id)                    AS paid_count
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        WHERE db.lga_id = $1
          AND ta.wa_status IN ('paid', 'partially_paid')
          AND ta.assessed_at >= NOW() - INTERVAL '30 days'
        GROUP BY day ORDER BY day DESC
        """,
        lga_id,
    )
    return [{"date": str(r["day"]), "total_ngn": float(r["total_ngn"]), "paid_count": r["paid_count"]} for r in rows]


async def get_monthly_collections(pool: asyncpg.Pool, lga_id: str) -> list:
    rows = await pool.fetch(
        """
        SELECT
            DATE_TRUNC('month', ta.payment_date) AS month,
            COALESCE(SUM(ta.amount_paid), 0)     AS total_ngn
        FROM tax_assessments ta
        JOIN detected_buildings db ON db.id = ta.building_id
        WHERE db.lga_id = $1
          AND ta.wa_status IN ('paid', 'partially_paid')
          AND ta.payment_date IS NOT NULL
        GROUP BY month ORDER BY month ASC
        """,
        lga_id,
    )
    return [{"month": str(r["month"])[:7], "total_ngn": float(r["total_ngn"])} for r in rows]


async def get_all_lga_benchmarks(pool: asyncpg.Pool) -> list:
    rows = await pool.fetch(
        """
        SELECT
            db.lga_id,
            COUNT(db.id)                                                        AS total_detected,
            COUNT(tr.id)                                                        AS registered,
            COALESCE(SUM(ta.amount_paid), 0)                                    AS total_collected_ngn,
            ROUND(
                (COUNT(tr.id)::numeric / NULLIF(COUNT(db.id), 0)) * 100, 2
            )                                                                   AS formalization_index
        FROM detected_buildings db
        LEFT JOIN tax_roll tr
            ON ST_DWithin(db.footprint::geography, tr.geom::geography, 15)
        LEFT JOIN tax_assessments ta ON ta.building_id = db.id
        WHERE db.verified = true
        GROUP BY db.lga_id
        ORDER BY formalization_index DESC NULLS LAST
        """
    )
    return [
        {
            "lga_id": r["lga_id"],
            "total_detected": r["total_detected"],
            "registered": r["registered"],
            "total_collected_ngn": float(r["total_collected_ngn"]),
            "formalization_index": float(r["formalization_index"] or 0),
        }
        for r in rows
    ]
