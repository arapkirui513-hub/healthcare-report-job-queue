import os
import sqlite3
from datetime import datetime

from playwright.sync_api import sync_playwright

from .report_queries import get_report_data


DB_PATH = "report.db"


def build_html(data: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    top_equipment_rows = "\n".join(
        f"""
        <tr>
            <td>{row["equipment_type"]}</td>
            <td>{row["report_count"]}</td>
        </tr>
        """
        for row in data["top_equipment"]
    )

    urgency_rows = "\n".join(
        f"""
        <tr>
            <td>{row["urgency"]}</td>
            <td>{row["report_count"]}</td>
        </tr>
        """
        for row in data["urgency_breakdown"]
    )

    detail_rows = "\n".join(
        f"""
        <tr>
            <td>{row["equipment_type"]}</td>
            <td>{row["issue_type"]}</td>
            <td>{row["urgency"]}</td>
            <td>{row["assigned_team"]}</td>
            <td>{row["confidence"]:.3f}</td>
            <td>{row["created_at"]}</td>
        </tr>
        """
        for row in data["all_reports"]
    )

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">

    <style>
        @page {{
            size: A4;
            margin: 20mm 15mm;
        }}

        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11px;
            color: #1a1a1a;
            margin: 0;
        }}

        h1 {{
            font-size: 18px;
            margin: 0 0 4px 0;
        }}

        h2 {{
            font-size: 13px;
            margin: 22px 0 6px 0;
        }}

        .subtitle {{
            color: #555;
            margin-bottom: 18px;
        }}

        .disclosure {{
            font-size: 9px;
            color: #666;
            margin-top: 4px;
        }}

        .totals {{
            display: flex;
            gap: 24px;
            margin-bottom: 20px;
        }}

        .total-card {{
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 8px 14px;
            min-width: 120px;
        }}

        .label {{
            font-size: 10px;
            color: #666;
            margin-bottom: 3px;
        }}

        .value {{
            font-size: 16px;
            font-weight: bold;
        }}

        .summary-tables {{
            display: flex;
            gap: 4%;
            margin-bottom: 10px;
        }}

        .small-table {{
            width: 48%;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 12px;
        }}

        th,
        td {{
            border: 1px solid #ccc;
            padding: 4px 6px;
            text-align: left;
        }}

        th {{
            background: #f0f0f0;
            font-weight: bold;
        }}

        /*
         * Repeat the detail-table header on every printed page.
         */
        thead {{
            display: table-header-group;
        }}

        /*
         * Prevent individual report rows from being split
         * across page boundaries.
         */
        tr {{
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .detail-table {{
            font-size: 9px;
        }}

        .detail-table th,
        .detail-table td {{
            padding: 4px 5px;
        }}
    </style>
</head>

<body>

    <h1>Biomedical Equipment Maintenance Report</h1>

    <div class="subtitle">
        Generated {today}
    </div>

    <div class="disclosure">
        Synthetic demonstration data – seed assumptions are not production statistics.
    </div>

    <div class="totals">
        <div class="total-card">
            <div class="label">Total reports</div>
            <div class="value">{data["total_reports"]}</div>
        </div>

        <div class="total-card">
            <div class="label">Average confidence</div>
            <div class="value">{data["average_confidence"]}</div>
        </div>
    </div>

    <div class="summary-tables">

        <div class="small-table">
            <h2>Top 5 Equipment Types</h2>

            <table>
                <thead>
                    <tr>
                        <th>Equipment type</th>
                        <th>Report count</th>
                    </tr>
                </thead>

                <tbody>
                    {top_equipment_rows}
                </tbody>
            </table>
        </div>

        <div class="small-table">
            <h2>Reports by Urgency</h2>

            <table>
                <thead>
                    <tr>
                        <th>Urgency</th>
                        <th>Report count</th>
                    </tr>
                </thead>

                <tbody>
                    {urgency_rows}
                </tbody>
            </table>
        </div>

    </div>

    <h2>All Maintenance Reports</h2>

    <table class="detail-table">
        <thead>
            <tr>
                <th>Equipment type</th>
                <th>Issue type</th>
                <th>Urgency</th>
                <th>Assigned team</th>
                <th>Confidence</th>
                <th>Created at</th>
            </tr>
        </thead>

        <tbody>
            {detail_rows}
        </tbody>
    </table>

</body>
</html>
"""


def get_all_reports(db_path: str = DB_PATH) -> list[dict]:
    """
    Retrieve the detailed maintenance-report rows needed
    for the long PDF table.

    This intentionally stays separate from get_report_data()
    so the verified Stage 2 return shape remains unchanged.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            equipment_type,
            issue_type,
            urgency,
            assigned_team,
            confidence,
            created_at
        FROM maintenance_reports
        ORDER BY created_at DESC, rowid DESC
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def render_pdf(html: str, output_path: str) -> None:
    """
    Render HTML into an A4 PDF using Playwright's Sync API
    and the system-installed Google Chrome.
    """
    output_dir = os.path.dirname(output_path)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome"
        )

        page = browser.new_page()

        page.set_content(
            html,
            wait_until="load"
        )

        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
        )

        browser.close()

def generate_report(report_id: str, db_path: str = DB_PATH, reports_dir: str = "reports") -> dict:
    """
    Generate a PDF report for a specific background-job report ID.

    The report engine owns the query -> HTML -> PDF workflow.
    Inngest owns job execution, retries, idempotency, and status handling.
    """
    data = get_report_data(db_path)
    data["all_reports"] = get_all_reports(db_path)

    html = build_html(data)

    os.makedirs(reports_dir, exist_ok=True)

    output_path = os.path.join(
        reports_dir,
        f"{report_id}.pdf",
    )

    render_pdf(html, output_path)

    return {
        "report_id": report_id,
        "file": output_path,
        "total_reports": data["total_reports"],
        "average_confidence": data["average_confidence"],
    }
