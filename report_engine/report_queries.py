import json
import sqlite3

DB_PATH = "report.db"


def get_report_data(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total_reports = conn.execute(
        """
        SELECT COUNT(*) AS total_reports
        FROM maintenance_reports
        """
    ).fetchone()["total_reports"]

    average_confidence = conn.execute(
        """
        SELECT ROUND(AVG(confidence), 3) AS average_confidence
        FROM maintenance_reports
        """
    ).fetchone()["average_confidence"]

    top_equipment = [
        dict(row)
        for row in conn.execute(
            """
            SELECT equipment_type, COUNT(*) AS report_count
            FROM maintenance_reports
            GROUP BY equipment_type
            ORDER BY report_count DESC
            LIMIT 5
            """
        ).fetchall()
    ]

    urgency_breakdown = [
        dict(row)
        for row in conn.execute(
            """
            SELECT urgency, COUNT(*) AS report_count
            FROM maintenance_reports
            GROUP BY urgency
            ORDER BY
                CASE urgency
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                END
            """
        ).fetchall()
    ]

    conn.close()

    return {
        "total_reports": total_reports,
        "average_confidence": average_confidence,
        "top_equipment": top_equipment,
        "urgency_breakdown": urgency_breakdown,
    }


if __name__ == "__main__":
    data = get_report_data(DB_PATH)

    print(json.dumps(data, indent=2))

    urgency_total = sum(
        row["report_count"]
        for row in data["urgency_breakdown"]
    )

    assert urgency_total == data["total_reports"]

    print(
        f"urgency_breakdown sums to total_reports "
        f"({urgency_total}) - OK"
    )