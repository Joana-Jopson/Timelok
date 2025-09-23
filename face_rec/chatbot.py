import json
from datetime import datetime, timedelta, date
from pathlib import Path
from django.utils.timezone import now
from django.utils import timezone
from rapidfuzz import fuzz
import dateparser
from transformers import pipeline
from calendar import day_name

from .models import (
    EmployeeMaster, EmployeeSchedule, EmployeeEventTransaction,
    EmployeeLeave, EmployeeShortPermission, Holiday,OrganizationSchedule,Schedule,GroupSchedule
)

# Load intents from JSON
INTENTS_PATH = Path(__file__).parent / 'intents.json'
with open(INTENTS_PATH) as f:
    INTENT_PHRASES = json.load(f)

INTENT_LABELS = list(INTENT_PHRASES.keys())

# Initialize transformers zero-shot classifier once
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def fuzzy_intent_match(query, intent_phrases, threshold=70):
    query = query.lower()
    best_intent = None
    best_score = 0
    for intent, phrases in intent_phrases.items():
        for phrase in phrases:
            score = fuzz.partial_ratio(query, phrase.lower())
            if score > best_score:
                best_score = score
                best_intent = intent
    if best_score >= threshold:
        return best_intent
    return None

def classify_intent_with_transformer(query):
    result = classifier(query, INTENT_LABELS)
    if result['scores'][0] > 0.6:
        return result['labels'][0]
    return None

def parse_date(text, base_date=None):
    base_date = base_date or datetime.today().date()
    parsed = dateparser.parse(text, settings={'RELATIVE_BASE': datetime.combine(base_date, datetime.min.time())})
    if parsed:
        return parsed.date()
    return None

def respond_to_query(user, query):
    # Basic greetings
    greetings = ['hi', 'hello', 'hey']
    if query.lower() in greetings:
        return "Hi! I'm your HR assistant. Ask me about schedule, punch-in/out, leave, permission, lateness, or holidays."

    # Try fuzzy first
    intent = fuzzy_intent_match(query, INTENT_PHRASES)

    # If fuzzy fails, try transformer zero-shot
    if intent is None:
        intent = classify_intent_with_transformer(query)

    if intent is None:
        return "Sorry, I didn't understand that. Please ask about schedule, punch-in/out, leave, permission, lateness, or holidays."

    # Handle intents:
    if intent == "greeting":
        return "Hi! I'm your HR assistant. How can I help?"

    if intent == "punch_in_today":
        return get_punch_time(user, "IN", datetime.today().date())

    if intent == "punch_out_today":
        return get_punch_time(user, "OUT", datetime.today().date())

    if intent == "punch_in_yesterday":
        return get_punch_time(user, "IN", datetime.today().date() - timedelta(days=1))

    if intent == "punch_out_yesterday":
        return get_punch_time(user, "OUT", datetime.today().date() - timedelta(days=1))

    if intent == "lateness":
        return check_lateness(user)

    if intent == "schedule":
        return get_schedule_for_employee(user)

    if intent == "leave_summary":
        # Extract if last month or this month from query for bonus accuracy
        if "last" in query.lower():
            date = datetime.today().date() - timedelta(days=30)
        else:
            date = datetime.today().date()
        return get_leave_summary(user, date.year, date.month)

    if intent == "permission_summary":
        return get_permission_summary(user)

    if intent in ["holiday_next", "holiday_this_month", "holiday_next_month", "holiday_last_month"]:
        return get_holiday_info(intent)

    if intent == "holiday_last":
        return get_last_holiday()

    return "Sorry, I am still learning to answer that."

def get_punch_time(user, punch_type, date):
    punches = EmployeeEventTransaction.objects.filter(
        employee_id=user,
        transaction_time__date=date,
        reason=punch_type
    ).order_by('transaction_time' if punch_type == "IN" else '-transaction_time')

    if not punches.exists():
        return f"No punch-{punch_type.lower()} record found for {date.strftime('%Y-%m-%d')}."

    punch = punches.first()
    time_str = punch.transaction_time.strftime('%I:%M %p')
    return f"You punched {punch_type.lower()} on {date.strftime('%Y-%m-%d')} at {time_str}."

def check_lateness(user):
    today = datetime.today().date()
    # Simplified lateness: official 9 AM start, 5 min flexible, 10 min grace
    official_start = datetime.combine(today, datetime.strptime("09:00", "%H:%M").time())
    flexible_min = 5
    grace_in_min = 10

    punch_ins = EmployeeEventTransaction.objects.filter(
        employee_id=user,
        transaction_time__date=today,
        reason='IN'
    ).order_by('transaction_time')

    if not punch_ins.exists():
        return "You have no punch-in record today."

    first_punch = punch_ins.first().transaction_time
    delta = (first_punch - official_start).total_seconds() / 60
    if delta <= flexible_min + grace_in_min:
        return "You are not late today. Good job!"
    else:
        late_minutes = int(delta - flexible_min)
        return f"You are {late_minutes} minutes late today."


def get_schedule_for_employee(employee):
    today = now().date()
    weekday = day_name[today.weekday()].lower()  # e.g., 'monday'
    results = []

    # 1. Check Employee Schedule
    emp_schedule = (
        EmployeeSchedule.objects
        .filter(employee_id=employee, from_date__date__lte=today, to_date__date__gte=today)
        .first()
    )
    if emp_schedule:
        schedule = getattr(emp_schedule, f"{weekday}_schedule_id", None)
        if schedule:
            results.append(f"🧍 Your personal schedule today is from {schedule.in_time.strftime('%I:%M %p')} to {schedule.out_time.strftime('%I:%M %p')}.")

    # 2. Check Group Schedule
    if hasattr(employee, 'employee_group_id') and employee.employee_group_id:
        group_schedule = (
            GroupSchedule.objects
            .filter(employee_group_id=employee.employee_group_id, from_date__date__lte=today, to_date__date__gte=today)
            .first()
        )
        if group_schedule:
            schedule = getattr(group_schedule, f"{weekday}_schedule_id", None)
            if schedule:
                results.append(f"👥 Your group schedule today is from {schedule.in_time.strftime('%I:%M %p')} to {schedule.out_time.strftime('%I:%M %p')}.")

    # 3. Check Organization Schedule
    org_schedule = (
        OrganizationSchedule.objects
        .filter(organization_id=employee.organization_id, from_date__date__lte=today, to_date__date__gte=today)
        .first()
    )
    if org_schedule:
        schedule = getattr(org_schedule, f"{weekday}_schedule_id", None)
        if schedule:
            results.append(f"🏢 Your organization schedule today is from {schedule.in_time.strftime('%I:%M %p')} to {schedule.out_time.strftime('%I:%M %p')}.")

    if not results:
        return "No schedule found for you today."

    return "\n".join(results)



def get_leave_summary(user, year, month):
    leaves = EmployeeLeave.objects.filter(
        employee_id=user,
        from_date__year=year,
        from_date__month=month
    )
    count = leaves.count()
    return f"You have applied for {count} leave(s) in {year}-{month:02d}."

def get_permission_summary(user):
    perms = EmployeeShortPermission.objects.filter(employee_id=user)
    count = perms.count()
    return f"You have applied for {count} permission(s)."

def get_holiday_info(intent):
    today = timezone.now().date()
    current_year = today.year
    current_month = today.month

    # 1. Check if today is a holiday
    today_holiday = Holiday.objects.filter(from_date__lte=today, to_date__gte=today).first()

    # 2. All holidays this year
    holidays_this_year = Holiday.objects.filter(from_date__year=current_year).order_by('from_date')

    # 3. Holidays from this month to end of year
    upcoming_holidays = holidays_this_year.filter(from_date__gte=today)

    # 4. Find the next upcoming holiday (after today)
    next_holiday = upcoming_holidays.first()

    response_parts = []

    if today_holiday:
        response_parts.append(f"🎉 Today is a holiday: **{today_holiday.holiday_eng}** ({today_holiday.from_date.strftime('%d-%b-%Y')})")
    else:
        if next_holiday:
            response_parts.append(f"⏭️ The next holiday is **{next_holiday.holiday_eng}** on {next_holiday.from_date.strftime('%d-%b-%Y')}.")

    # Add upcoming holidays from current month to year end
    if upcoming_holidays.exists():
        response_parts.append("\n📅 Upcoming holidays from this month to year end:")
        for hol in upcoming_holidays:
            response_parts.append(f"- {hol.holiday_eng} ({hol.from_date.strftime('%d-%b-%Y')})")
    else:
        response_parts.append("📅 No upcoming holidays found for the rest of the year.")

    # Add all holidays of the year
    if holidays_this_year.exists():
        response_parts.append("\n📘 All holidays this year:")
        for hol in holidays_this_year:
            response_parts.append(f"- {hol.holiday_eng} ({hol.from_date.strftime('%d-%b-%Y')})")

    return "\n".join(response_parts)

def get_last_holiday():
    today = date.today()
    last_holiday = Holiday.objects.filter(to_date__lt=today).order_by('-to_date').first()
    ongoing_holidays = Holiday.objects.filter(from_date__lte=today, to_date__gte=today)
    holidays_this_year = Holiday.objects.filter(from_date__year=today.year)
    start_of_month = today.replace(day=1)
    end_of_year = date(today.year, 12, 31)
    upcoming_holidays = Holiday.objects.filter(from_date__gte=start_of_month, from_date__lte=end_of_year)

    msg = []

    if ongoing_holidays.exists():
        msg.append("🎉 Ongoing Holidays:")
        for hol in ongoing_holidays:
            msg.append(f"- {hol.holiday_eng} ({hol.from_date.strftime('%d-%b-%Y')} to {hol.to_date.strftime('%d-%b-%Y')})")

    if last_holiday:
        msg.append(f"\n🕓 Last Holiday: {last_holiday.holiday_eng} ({last_holiday.from_date.strftime('%d-%b-%Y')})")

    if upcoming_holidays.exists():
        msg.append("\n📅 Upcoming Holidays:")
        for hol in upcoming_holidays:
            msg.append(f"- {hol.holiday_eng} ({hol.from_date.strftime('%d-%b-%Y')})")

    if holidays_this_year.exists():
        msg.append("\n📘 All Holidays This Year:")
        for hol in holidays_this_year:
            msg.append(f"- {hol.holiday_eng} ({hol.from_date.strftime('%d-%b-%Y')})")

    return "\n".join(msg)
