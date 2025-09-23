from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from django.http import FileResponse
from io import BytesIO

def generate_attendance_pdf(records):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    if not records:
        return FileResponse(buffer, as_attachment=True, filename="attendance_report.pdf")

    emp = records[0]

    # Header
    title = f"Attendance Report for: {emp.employee_id.emp_no}"
    org = f"Organization: {emp.employee_id.organization_id.organization_eng if emp.employee_id.organization_id else '-'}"
    desg = f"Designation: {emp.employee_id.designation_id.designation_eng if emp.employee_id.designation_id else '-'}"

    elements.append(Paragraph(title, styles['Heading2']))
    elements.append(Paragraph(org, styles['Normal']))
    elements.append(Paragraph(desg, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Table headers
    table_data = [["Date", "Punch In", "Punch Out", "Late", "Early", "Work Mins","Extra Mins", "Comment"]]

    # Table rows
    for row in records:
        time_in = row.time_in.strftime('%H:%M') if row.time_in else "-"
        time_out = row.time_out.strftime('%H:%M') if row.time_out else "-"
        table_data.append([
            row.Ddate.strftime('%Y-%m-%d') if row.Ddate else '-',
            time_in,
            time_out,
            str(row.late or 0),
            str(row.early or 0),
            str(row.workmts_row_timediff or 0),
            str(row.dailyextramts or 0),
            row.comment or "-"
        ])

    # Create and style table
    table = Table(table_data, colWidths=[1.0 * inch] * 8)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="attendance_report.pdf")

