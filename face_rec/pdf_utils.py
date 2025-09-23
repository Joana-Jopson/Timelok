from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import timedelta, datetime
from .models import *


def generate_monthly_attendance_pdf(buffer, employee):
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, f"Monthly Attendance Report")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, height - 80, f"Employee ID: {employee.employee_id}")
    p.drawString(100, height - 100, f"Employee Name: {employee.name_english}")
    p.drawString(100, height - 120, f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

    # Sample mock data — replace with actual attendance data
    p.drawString(100, height - 160, "Date       |  Punch In   |  Punch Out")
    y = height - 180
    for i in range(1, 6):  # Replace with dynamic loop over real data
        p.drawString(100, y, f"2025-07-0{i}   |  09:00 AM  |  06:00 PM")
        y -= 20

    p.showPage()
    p.save()

