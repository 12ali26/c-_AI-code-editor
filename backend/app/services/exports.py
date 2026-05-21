from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.models import ExportType, ModelRun, Triangle


def create_export(run: ModelRun, triangle: Triangle, export_type: ExportType, storage_root: str) -> str:
    root = Path(storage_root)
    root.mkdir(parents=True, exist_ok=True)
    if export_type == ExportType.excel:
        return _create_excel_export(run, triangle, root)
    if export_type == ExportType.pdf:
        return _create_pdf_export(run, triangle, root)
    raise ValueError(f"Unsupported export type: {export_type}")


def _create_excel_export(run: ModelRun, triangle: Triangle, root: Path) -> str:
    path = root / f"{run.id}.xlsx"
    triangle_frame = pd.DataFrame(triangle.values, columns=triangle.development_periods)
    triangle_frame.insert(0, "origin_period", triangle.origin_periods)

    result_frame = pd.DataFrame(
        {
            "origin_period": triangle.origin_periods,
            "latest": run.result.latest_diagonal,
            "ultimate": run.result.ultimate_by_origin,
            "ibnr": run.result.ibnr_by_origin,
        }
    )
    factors_frame = pd.DataFrame(
        {
            "from_development_period": triangle.development_periods[:-1],
            "to_development_period": triangle.development_periods[1:],
            "age_to_age_factor": run.result.age_to_age_factors,
        }
    )

    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        triangle_frame.to_excel(writer, sheet_name="Triangle", index=False)
        factors_frame.to_excel(writer, sheet_name="Factors", index=False)
        result_frame.to_excel(writer, sheet_name="Results", index=False)
    return str(path)


def _create_pdf_export(run: ModelRun, triangle: Triangle, root: Path) -> str:
    path = root / f"{run.id}.pdf"
    pdf = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, height - 72, "P&C Reserving Report")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(72, height - 96, f"Run ID: {run.id}")
    pdf.drawString(72, height - 112, f"Method: {run.method}")
    pdf.drawString(72, height - 128, f"Origins: {len(triangle.origin_periods)}")
    pdf.drawString(72, height - 152, f"Total latest: {run.result.total_latest:,.2f}")
    pdf.drawString(72, height - 168, f"Total ultimate: {run.result.total_ultimate:,.2f}")
    pdf.drawString(72, height - 184, f"Total IBNR: {run.result.total_ibnr:,.2f}")
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, height - 220, "Origin Period Results")
    pdf.setFont("Helvetica", 9)
    y = height - 244
    for origin, latest, ultimate, ibnr in zip(
        triangle.origin_periods,
        run.result.latest_diagonal,
        run.result.ultimate_by_origin,
        run.result.ibnr_by_origin,
        strict=True,
    ):
        pdf.drawString(72, y, f"{origin}: latest {latest:,.2f}, ultimate {ultimate:,.2f}, IBNR {ibnr:,.2f}")
        y -= 14
        if y < 72:
            pdf.showPage()
            y = height - 72
    pdf.save()
    return str(path)

