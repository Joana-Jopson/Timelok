from django.shortcuts import render,redirect,get_object_or_404
import json
import io
from django.utils.timezone import localdate
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse, HttpResponseBadRequest
from django.http import HttpResponse
from face_rec.models import SecUser,OrganizationType,EmployeeMaster,Organization, Country, Grade, Designation, EmployeeType, Location, ContractorCompany,EmployeeEventTransaction,PermissionType,LeaveType,EmployeeGroup,EmployeeGroupMember,Schedule,OrganizationSchedule,GroupSchedule,EmployeeSchedule,EmployeeLeave,EmployeeShortPermission,ChatMessage,SecPrivilegeGroup, SecModule, SecSubModule, SecUserRole, SecRole, SecRolePrivilege,DailyMove,DailyEmployeeAttendanceDetails,Holiday
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required,user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q,Sum,Min, Max,F,Count
from django.utils.timezone import now
from datetime import timedelta,date
from django.utils import timezone
from dateutil import parser
from django.utils.dateparse import parse_date
from collections import OrderedDict
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
import os
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1, MTCNN
from django.conf import settings
from django.core.files.base import ContentFile
import pygame
from django.contrib import messages
from django.urls import reverse_lazy
import threading
import time
import base64
from datetime import datetime, time
from django.db import IntegrityError
from django.contrib import messages
from PIL import Image
import cv2
from .face_utils import capture_webcam_image, get_embedding, compare_faces
import base64
from io import BytesIO
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from django.core.files.storage import FileSystemStorage
from django.templatetags.static import static
from .forms import ChatMessageForm
from .nlp_utils import is_offensive
from .chatbot import respond_to_query
import logging
from django.http import FileResponse, Http404
from .utils import generate_attendance_pdf 
from collections import defaultdict
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from django.db.models.functions import ExtractHour
from calendar import day_name,monthrange
from django.utils.timezone import make_aware, is_naive,now



# Create your views here.
def index(request):
    return render(request, 'index.html')

def custom_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = SecUser.objects.get(login=username, password=password)
            employee = user.employee_id

            request.session['user_id'] = user.user_id
            request.session['employee_id'] = employee.employee_id

            # Determine punch status for today
            today = now().date()
            punched_in = EmployeeEventTransaction.objects.filter(
                employee_id=employee,
                transaction_time__date=today,
                reason='IN'
            ).exists()
            punched_out = EmployeeEventTransaction.objects.filter(
                employee_id=employee,
                transaction_time__date=today,
                reason='OUT'
            ).exists()

            # Decide popup message and action options based on punch status
            if not punched_in:
                # First login of the day - ask Punch In
                popup_message = "Do you want to Punch In?"
                # action param for face_recognize will be 'in' or 'no'
                return render(request, 'login_popup.html', {
                    'popup_message': popup_message,
                    'employee_name': employee.firstname_eng,
                    'action_options': ['in', 'no']
                })
            elif punched_in and not punched_out:
                # Already punched in but not out - ask Punch In again or Punch Out
                popup_message = "You already punched in. Punch In again or Punch Out?"
                # action options: 'in' (punch in again), 'out' (punch out)
                return render(request, 'login_popup.html', {
                    'popup_message': popup_message,
                    'employee_name': employee.firstname_eng,
                    'action_options': ['in', 'out']
                })
            else:
                # Already punched in and out today - ask Punch In or No
                popup_message = "You already punched out today. Do you want to Punch In again?"
                return render(request, 'login_popup.html', {
                    'popup_message': popup_message,
                    'employee_name': employee.firstname_eng,
                    'action_options': ['in', 'no']
                })

        except SecUser.DoesNotExist:
            messages.error(request, 'Invalid username or password')

    return render(request, 'login.html')


@custom_login_required
def verify_face_page(request):
    # Get action from query params or default to no
    action = request.GET.get('action', 'no')
    return render(request, 'face_recognize.html', {'action': action})


@csrf_exempt
def verify_face(request):
    if request.method == 'POST':
        try:
            image_data = request.POST.get('image')
            action = request.POST.get('action', 'no')  # 'in', 'out', or 'no'

            if not image_data:
                return JsonResponse({'status': 'fail', 'redirect': True, 'message': 'No image received'})

            format, imgstr = image_data.split(';base64,')
            image_bytes = base64.b64decode(imgstr)
            img = Image.open(BytesIO(image_bytes))

            employee_id = request.session.get('employee_id')
            if not employee_id:
                return JsonResponse({'status': 'fail', 'redirect': True, 'message': 'Session expired. Please log in again.'})

            employee = EmployeeMaster.objects.get(pk=employee_id)
            stored_img_path = os.path.join(settings.MEDIA_ROOT, str(employee.photo_file_name))

            if not os.path.exists(stored_img_path):
                return JsonResponse({'status': 'fail', 'redirect': True, 'message': 'Stored image not found'})

            stored_img = Image.open(stored_img_path)
            stored_embedding = get_embedding(stored_img)
            live_embedding = get_embedding(img)

            if not compare_faces(stored_embedding, live_embedding):
                return JsonResponse({'status': 'fail', 'redirect': True, 'message': 'Face not recognized.'})

            # Proceed based on action
            today = now().date()
            last_event = EmployeeEventTransaction.objects.filter(
                employee_id=employee,
                transaction_time__date=today
            ).order_by('-transaction_time').first()

            if action == 'in':
                if last_event is None or last_event.reason == 'OUT':
                    # Allow punch in
                    EmployeeEventTransaction.objects.create(
                        employee_id=employee,
                        transaction_time=now(),
                        reason="IN",
                        remarks="Punch In via face",
                        reader_id=1,
                        user_entry_flag=0,
                        created_id=employee.created_id,
                        last_updated_id=employee.employee_id,
                        created_date=now(),
                        last_updated_date=now(),
                    )
                # Else already IN, do not duplicate

                redirect_url = reverse('admin_dashboard') if employee.firstname_eng == 'Administrator' else reverse('employee_dashboard')
                return JsonResponse({'status': 'success', 'redirect_url': redirect_url})

            elif action == 'out':
                if last_event and last_event.reason == 'IN':
                    # Allow punch out
                    EmployeeEventTransaction.objects.create(
                        employee_id=employee,
                        transaction_time=now(),
                        reason="OUT",
                        remarks="Punch Out via face",
                        reader_id=1,
                        user_entry_flag=0,
                        created_id=employee.created_id,
                        last_updated_id=employee.employee_id,
                        created_date=now(),
                        last_updated_date=now(),
                    )
                    return JsonResponse({'status': 'success', 'redirect_url': reverse('login')})
                else:
                    return JsonResponse({'status': 'fail', 'redirect': False, 'message': 'You must punch in before punching out.'})

            else:
                # action == 'no'
                redirect_url = reverse('admin_dashboard') if employee.firstname_eng == 'Administrator' else reverse('employee_dashboard')
                return JsonResponse({'status': 'success', 'redirect_url': redirect_url})

        except Exception as e:
            return JsonResponse({'status': 'fail', 'redirect': True, 'message': str(e)})

    return JsonResponse({'status': 'fail', 'redirect': True, 'message': 'Invalid request'})

@csrf_exempt
def logout_face(request):
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')
            employee_id = request.session.get('employee_id')

            if not user_id or not employee_id:
                return JsonResponse({'status': 'fail', 'redirect': True, 'message': 'Session expired. Please log in again.'})

            employee = EmployeeMaster.objects.get(pk=employee_id)
            today = date.today()

            # Get last punch of the day
            last_event = EmployeeEventTransaction.objects.filter(
                employee_id=employee,
                transaction_time__date=today
            ).order_by('-transaction_time').first()

            if not last_event or last_event.reason != 'IN':
                return JsonResponse({'status': 'fail', 'redirect': True, 'message': 'You must punch in before logging out.'})

            # Save logout
            EmployeeEventTransaction.objects.create(
                employee_id=employee,
                transaction_time=now(),
                reason="OUT",
                remarks="Logout via face",
                reader_id=1,
                user_entry_flag=0,
                created_id=employee.created_id,
                last_updated_id=employee.employee_id,
                created_date=now(),
                last_updated_date=now(),
            )

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'fail', 'redirect': False, 'message': str(e)})

    return JsonResponse({'status': 'fail', 'redirect': False, 'message': 'Invalid request'})


@custom_login_required
def verify_logout_page(request):
    return render(request, 'face_logout.html') 

#--------------------------------------------------------------------------------
@custom_login_required
def chat_dashboard(request):
    user = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    users = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=users).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass

    
    recent_messages = ChatMessage.objects.filter(
        Q(sender_id=user) | Q(receiver_id=user)
    ).order_by('-timestamp')

    recent_chat_partners = []
    seen_ids = set()

    for msg in recent_messages:
        partner = msg.receiver_id if msg.sender_id == user else msg.sender_id
        if partner.employee_id not in seen_ids:
            recent_chat_partners.append(partner)
            seen_ids.add(partner.employee_id)

    return render(request, "chat_message.html", {
        'recent_chats': recent_chat_partners,
        'user': user,
        'receiver': None,
        'form': None,
        'messages': [],
        'users': manager,
        'manage_employee_access': access,
        'manage_designation_access': manage_designation_access
    })

@custom_login_required
def chat_view(request, receiver_id):
    user = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])
    receiver = get_object_or_404(EmployeeMaster, employee_id=receiver_id)

    # Get all messages between the user and the receiver
    messages_qs = ChatMessage.objects.filter(
        Q(sender_id=user, receiver_id=receiver) |
        Q(sender_id=receiver, receiver_id=user)
    ).order_by("timestamp")

    # Build recent chat partners manually (SQL Server can't use distinct on field)
    recent_messages = ChatMessage.objects.filter(
        Q(sender_id=user) | Q(receiver_id=user)
    ).order_by('-timestamp')

    recent_chat_partners = []
    seen_ids = set()

    for msg in recent_messages:
        partner = msg.receiver_id if msg.sender_id == user else msg.sender_id
        if partner.employee_id not in seen_ids:
            recent_chat_partners.append(partner)
            seen_ids.add(partner.employee_id)

    if request.method == "POST":
        form = ChatMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender_id = user
            msg.receiver_id = receiver
            msg.file_type = detect_file_type(msg.file_path.name) if msg.file_path else None
            msg.is_bad_content = is_offensive(msg.message_text)
            if msg.is_bad_content:
                messages.error(request, "Message contains offensive content and was blocked.")
            else:
                msg.save()
                return redirect('chat_view', receiver_id=receiver.employee_id)
    else:
        form = ChatMessageForm()

    return render(request, "chat_message.html", {
        'messages': messages_qs,
        'receiver': receiver,
        'form': form,
        'user': user,
        'recent_chats': recent_chat_partners
    })


def detect_file_type(filename):
    ext = filename.split('.')[-1].lower()
    if ext in ['jpg', 'jpeg', 'png']:
        return "image"
    elif ext == "pdf":
        return "pdf"
    elif ext == "docx":
        return "docx"
    return "unknown"

def employee_search(request):
    term = request.GET.get("q", "")
    results = []
    if term:
        employees = EmployeeMaster.objects.filter(
            Q(firstname_eng__icontains=term) | Q(lastname_eng__icontains=term)
        )[:10]
        for emp in employees:
            results.append({
                'employee_id': emp.employee_id,
                'name': f"{emp.firstname_eng} {emp.lastname_eng}",
                'photo': request.build_absolute_uri(emp.photo_file_name.url) if emp.photo_file_name else '',
            })
    return JsonResponse(results, safe=False)

def chatbot_view(request):
    if request.method == "POST":
        user_id = request.session.get('employee_id')
        message = request.POST.get("message")
        if not user_id:
            return JsonResponse({"response": "User session expired. Please login again."})

        user = EmployeeMaster.objects.filter(employee_id=user_id).first()
        if not user:
            return JsonResponse({"response": "User not found."})

        response = respond_to_query(user, message)
        return JsonResponse({"response": response})

    return render(request, "chatbot.html")

#--------------------------------ADMIN-----------------
@custom_login_required
def admin_dashboard(request):
    total_employees = EmployeeMaster.objects.filter(active_flag=1).count()

    today = timezone.now().date()
    past_30_days = today - timedelta(days=30)

    # Punched in count
    punched_in = EmployeeEventTransaction.objects.filter(
        reason='IN', transaction_time__date=today
    ).values('employee_id').distinct().count()

    # Punched out count
    punched_out = EmployeeEventTransaction.objects.filter(
        reason='OUT', transaction_time__date=today
    ).values('employee_id').distinct().count()

    # Recently joined employees
    recent_joins = EmployeeMaster.objects.order_by('-join_date')[:5]
    for emp in recent_joins:
        emp.employee_name = f"{emp.firstname_eng} {emp.lastname_eng}"
    print(EmployeeMaster.objects.filter(
    active_flag=1,
    join_date__year=today.year,
    join_date__month=today.month).query)

    # Anomalies: Punched in multiple times without punch out
    anomalies = []
    for emp in EmployeeMaster.objects.filter(active_flag=1):
        punches_today = EmployeeEventTransaction.objects.filter(
            employee_id=emp, transaction_time__date=today
        ).order_by('transaction_time')
        
                

        ins = punches_today.filter(reason='IN').count()
        outs = punches_today.filter(reason='OUT').count()

        if ins > outs:
            anomalies.append(emp)

    # Attendance trend last 7 days
    seven_days_ago = today - timedelta(days=6)
    trend_data = DailyEmployeeAttendanceDetails.objects.filter(Ddate__range=[seven_days_ago, today]) \
    .values('Ddate').annotate(count=Count('daily_EmployeeAttendanceDetails_id')).order_by('Ddate')
    trend_labels = [entry['Ddate'].strftime('%Y-%m-%d') for entry in trend_data]
    trend_counts = [entry['count'] for entry in trend_data]
    
    # Designation distribution
    designation_data = EmployeeMaster.objects.values(name=F('designation_id__designation_eng')) \
        .annotate(count=Count('employee_id')).order_by('-count')
    designation_labels = [entry['name'] for entry in designation_data]
    designation_counts = [entry['count'] for entry in designation_data]
    
    # 3. Department (Organization) Distribution
    department_data = EmployeeMaster.objects.values(name=F('organization_id__organization_eng')) \
        .annotate(count=Count('employee_id')).order_by('-count')
    department_labels = [entry['name'] for entry in department_data]
    department_counts = [entry['count'] for entry in department_data]
   
    # 4. Contractor-wise Distribution
    contractor_data = EmployeeMaster.objects.values(
        'contract_company_id__contract_company_eng'
    ).annotate(count=Count('employee_id'))
    contractor_labels = [entry['contract_company_id__contract_company_eng'] or 'Unknown' for entry in contractor_data]
    contractor_counts = [entry['count'] for entry in contractor_data]
    
    # 5. Hourly Punch-In Distribution (today)
    hourly_punch = (
        EmployeeEventTransaction.objects.filter(reason='IN', transaction_time__date=today)
        .annotate(hour=ExtractHour('transaction_time'))
        .values('hour')
        .annotate(count=Count('transaction_id'))
        .order_by('hour')
    )
    punch_hours = [f"{entry['hour']:02d}:00" for entry in hourly_punch]
    punch_counts = [entry['count'] for entry in hourly_punch]

    
    
    # Late punches today (based on grace + flexible min)
    late_today = []
    punch_ins_today = EmployeeEventTransaction.objects.filter(
        reason='IN',
        transaction_time__date=today
    ).select_related('employee_id')

    for punch in punch_ins_today:
        emp = punch.employee_id
        emp_schedule = (
            EmployeeSchedule.objects.filter(employee_id=emp, from_date__lte=today, to_date__gte=today).first()
            or GroupSchedule.objects.filter(
                employee_group_id__in=EmployeeGroupMember.objects.filter(employee_id=emp).values('employee_group_id'),
                from_date__lte=today, to_date__gte=today
            ).first()
            or OrganizationSchedule.objects.filter(
                organization_id=emp.organization_id,
                from_date__lte=today, to_date__gte=today
            ).first()
        )

        if emp_schedule:
            weekday = today.weekday()  
            schedule = None
            
            if isinstance(emp_schedule, EmployeeSchedule):
                schedule_field_map = {
                    0: emp_schedule.monday_schedule_id,
                    1: emp_schedule.tuesday_schedule_id,
                    2: emp_schedule.wednesday_schedule_id,
                    3: emp_schedule.thursday_schedule_id,
                    4: emp_schedule.friday_schedule_id,
                    5: emp_schedule.saturday_schedule_id,
                    6: emp_schedule.sunday_schedule_id,
                    }
                schedule = schedule_field_map.get(weekday)
            elif isinstance(emp_schedule, GroupSchedule):
                schedule_field_map = {
                    0: emp_schedule.monday_schedule_id,
                    1: emp_schedule.tuesday_schedule_id,
                    2: emp_schedule.wednesday_schedule_id,
                    3: emp_schedule.thursday_schedule_id,
                    4: emp_schedule.friday_schedule_id,
                    5: emp_schedule.saturday_schedule_id,
                    6: emp_schedule.sunday_schedule_id,
                    }
                schedule = schedule_field_map.get(weekday)
            elif isinstance(emp_schedule, OrganizationSchedule):
                schedule_field_map = {
                    0: emp_schedule.monday_schedule_id,
                    1: emp_schedule.tuesday_schedule_id,
                    2: emp_schedule.wednesday_schedule_id,
                    3: emp_schedule.thursday_schedule_id,
                    4: emp_schedule.friday_schedule_id,
                    5: emp_schedule.saturday_schedule_id,
                    6: emp_schedule.sunday_schedule_id,
                    }
                schedule = schedule_field_map.get(weekday)
        if schedule and schedule.in_time:
            shift_in = schedule.in_time.time()
            punch_time = punch.transaction_time.time()
            grace = schedule.grace_in_min or 0
            flex = schedule.flexible_min or 0
            allowed_minutes = grace + flex
            
            punch_minutes = (datetime.combine(today, punch_time) - datetime.combine(today, shift_in)).total_seconds() / 60
            if punch_minutes > allowed_minutes:
                late_today.append({
                    "firstname_eng": emp.firstname_eng,
                    "late": int(punch_minutes - allowed_minutes)
                    })

    # Frequent latecomers in last 3 days
    frequent_late = DailyEmployeeAttendanceDetails.objects.filter(
        Ddate__gte=today - timedelta(days=3),
        late=True
    ).values(employee_name=F('employee_id__firstname_eng')) \
     .annotate(late_days=Count('Ddate')) \
     .order_by('-late_days')[:5]

    context = {
        "total_employees": total_employees,
        "punched_in": punched_in,
        "punched_out": punched_out,
        "trend_data": list(trend_data),
        'designation_labels': designation_labels,
        'designation_counts': designation_counts,
        'department_labels': department_labels,
        'department_counts': department_counts,
        'contractor_labels': json.dumps(contractor_labels),
        'contractor_counts': json.dumps(contractor_counts),
        'punch_hours': punch_hours,
        'punch_counts': punch_counts,
        "recent_joins": recent_joins,
        "late_today": late_today,
        "frequent_late": list(frequent_late),
        "anomalies": anomalies,
        'trend_labels': trend_labels,
        'trend_counts': trend_counts,
        
    }

    return render(request, 'admin_dashboard.html', context)



@custom_login_required
def organization_type_view(request):
    search_query = request.GET.get('search', '')
    org_types = OrganizationType.objects.all()

    if search_query:
        org_types = org_types.filter(organization_type_eng__icontains=search_query)

    org_types = org_types.order_by('OrgTypeLevel')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'add':
            name = request.POST.get('organization_type_eng')
            level = request.POST.get('OrgTypeLevel')

            if name and level:
                OrganizationType.objects.create(
                    organization_type_eng=name,
                    organization_type_arb=name,  
                    OrgTypeLevel=int(level),
                    created_id=1,
                    last_updated_id=1,
                    created_date=now(),
                    last_updated_date=now()
                )
        elif form_type == 'update':
            total = int(request.POST.get('total', 0))
            for i in range(1, total + 1):
                name = request.POST.get(f'organization_type_eng_{i}')
                level = request.POST.get(f'OrgTypeLevel_{i}')

                if name and level:
                    try:
                        org = OrganizationType.objects.get(organization_type_eng=name)
                        org.OrgTypeLevel = int(level)
                        org.last_updated_id = 1
                        org.last_updated_date = now()
                        org.save()
                    except OrganizationType.DoesNotExist:
                        continue  # Skip if entry not found

        return redirect('organization_type_view')

    return render(request, 'organization_type_view.html', {
        'organization_types': org_types
    })

@custom_login_required
def employee_manage_view(request):
    if 'user_id' in request.session:
        user_id = request.session['user_id']
        admin = EmployeeMaster.objects.get(employee_id=user_id)
        search = request.GET.get('search', '')
        employees = EmployeeMaster.objects.select_related(
            'organization_id',
            'passport_issue_country_id',
            'work_location_id',
            'designation_id',
            'employee_type_id',
            'grade_id'
            ).all()
        if search:
            employees = employees.filter(
            Q(emp_no__icontains=search) |
            Q(firstname_eng__icontains=search) |
            Q(lastname_eng__icontains=search))
        
        managers = EmployeeMaster.objects.filter(active_flag=1, manager_flag='Y')
        context = {
        'employees': employees,
        'organizations': Organization.objects.all(),
        'countries': Country.objects.all(),
        'designations': Designation.objects.all(),
        'employee_types': EmployeeType.objects.all(),
        'locations': Location.objects.all(),
        'contractor_companies': ContractorCompany.objects.all(),
        'search': search,
        'grades': Grade.objects.all(),
        'managers': managers,
        'admin':admin
        }
        return render(request, 'admin_employee_manage.html', context)
    
    return redirect('login')





@custom_login_required
def employee_add_view(request):
    if request.method == 'POST':
        data = request.POST
        emp_no = data.get('emp_no')
        firstname_eng = data.get('firstname_eng')
        lastname_eng = data.get('lastname_eng')
        organization = data.get('organization_id')
        designation = data.get('designation_id')
        passport_issue_country = data.get('passport_issue_country')
        employee_type = data.get('employee_type_id')
        work_location = data.get('work_location_id')
        contract_company = data.get('contract_company_id')
        grade = data.get('grade_id')
        active_date = data.get('active_date')
        join_date = data.get('join_date')
        open_shift_flag = int(data.get('open_shift_flag', 0))
        overtime_flag = int(data.get('overtime_flag', 0))
        manager_flag = data.get('manager_flag')
        remarks = data.get('remarks')
        file = request.FILES.get('photo_file_name')
        manager_id = data.get('manager_id')

        required_fields = [emp_no, firstname_eng, lastname_eng, passport_issue_country, active_date, join_date, manager_flag, file, manager_id]
        if not all(required_fields):
            return render(request, 'admin_employee_manage.html', {
                "error": "All required fields must be filled.",
                "form_data": data,
                "employees": EmployeeMaster.objects.all(),
                "organizations": Organization.objects.all(),
                "designations": Designation.objects.all(),
                "countries": Country.objects.all(),
                "employee_types": EmployeeType.objects.all(),
                "locations": Location.objects.all(),
                "contractor_companies": ContractorCompany.objects.all(),
                "grades": Grade.objects.all(),
                "managers": EmployeeMaster.objects.filter(active_flag=1, manager_flag='Y')
            })

        if EmployeeMaster.objects.filter(emp_no=emp_no).exists():
            return render(request, 'admin_employee_manage.html', {
                "error": "Employee number already exists. Please choose a different one.",
                "form_data": data,
                "employees": EmployeeMaster.objects.all(),
                "organizations": Organization.objects.all(),
                "designations": Designation.objects.all(),
                "countries": Country.objects.all(),
                "employee_types": EmployeeType.objects.all(),
                "locations": Location.objects.all(),
                "contractor_companies": ContractorCompany.objects.all(),
                "grades": Grade.objects.all(),
                "managers": EmployeeMaster.objects.filter(active_flag=1, manager_flag='Y')
            })

        try:
            manager_instance = EmployeeMaster.objects.get(employee_id=manager_id)
        except EmployeeMaster.DoesNotExist:
            return render(request, 'admin_employee_manage.html', {
                "error": "Selected manager does not exist.",
                "form_data": data,
                "employees": EmployeeMaster.objects.all(),
                "organizations": Organization.objects.all(),
                "designations": Designation.objects.all(),
                "countries": Country.objects.all(),
                "employee_types": EmployeeType.objects.all(),
                "locations": Location.objects.all(),
                "contractor_companies": ContractorCompany.objects.all(),
                "grades": Grade.objects.all(),
                "managers": EmployeeMaster.objects.filter(active_flag=1, manager_flag='Y')
            })

        new_emp = EmployeeMaster(
            emp_no=emp_no,
            firstname_eng=firstname_eng,
            lastname_eng=lastname_eng,
            firstname_arb=firstname_eng,
            lastname_arb=lastname_eng,
            organization_id=Organization.objects.get(organization_id=organization),
            designation_id=Designation.objects.get(designation_id=designation) if designation else None,
            employee_type_id=EmployeeType.objects.get(employee_type_id=employee_type) if employee_type else None,
            grade_id=Grade.objects.get(grade_id=grade) if grade else None,
            contract_company_id=ContractorCompany.objects.get(contract_company_id=contract_company) if contract_company else None,
            work_location_id=Location.objects.get(location_id=work_location) if work_location else None,
            passport_issue_country_id=Country.objects.get(country_id=passport_issue_country),
            manager_id=manager_instance,
            active_date=active_date,
            join_date=join_date,
            photo_file_name=file,
            open_shift_flag=open_shift_flag,
            manager_flag=manager_flag,
            remarks=remarks,
            overtime_flag=overtime_flag,
            created_id=1,
            created_date=timezone.now(),
            last_updated_id=1,
            last_updated_date=timezone.now()
        )

        new_emp.save()
        usernames = f"{firstname_eng}{emp_no}"
        sec_user = SecUser(
            login=usernames,
            password=firstname_eng,
            employee_id=new_emp,
            last_updated_id=1
        )
        sec_user.save()

        messages.success(request, "Employee added successfully!")
        return redirect('employee_manage')

    # GET fallback
    return render(request, 'admin_employee_manage.html', {
        'employees': EmployeeMaster.objects.all(),
        'organizations': Organization.objects.all(),
        'designations': Designation.objects.all(),
        'countries': Country.objects.all(),
        'employee_types': EmployeeType.objects.all(),
        'locations': Location.objects.all(),
        'contractor_companies': ContractorCompany.objects.all(),
        'grades': Grade.objects.all(),
        'managers': EmployeeMaster.objects.filter(active_flag=1, manager_flag='Y')
    })

@custom_login_required
def employee_block(request, pk):
    admin_id = request.session.get('user_id')
    if not admin_id:
        messages.error(request, "Session expired or unauthorized access.")
        return redirect('login')

    try:  
        admin = EmployeeMaster.objects.get(employee_id=admin_id)
        if admin.active_flag != 1  and admin.firstname_eng != 'Admin':
            messages.error(request, "Inactive admin accounts cannot block employees.")
            return redirect('employee_manage')

        employee = get_object_or_404(EmployeeMaster, pk=pk)
        employee.active_flag = 0
        employee.inactive_date = timezone.now()
        employee.active_date = None
        employee.last_updated_id = admin.employee_id  # use admin ID from session
        employee.last_updated_date = timezone.now()
        employee.save()

        messages.info(request, f"Employee {employee.emp_no} has been blocked.")
        return redirect('employee_manage')

    except EmployeeMaster.DoesNotExist:
        messages.error(request, "Admin record not found.")
        return redirect('login')

@custom_login_required
def employee_unblock(request, pk):
    admin_id = request.session['user_id']
    if not admin_id:
        messages.error(request, "Session expired or unauthorized access.")
        return redirect('login')
    try:
        admin=EmployeeMaster.objects.get(employee_id=admin_id)
        if admin.active_flag != 1  and admin.firstname_eng != 'Admin':
            messages.error(request, "Inactive admin accounts cannot block employees.")
            return redirect('employee_manage')
        
        emp = get_object_or_404(EmployeeMaster, pk=pk)
        emp.active_flag = 1
        emp.active_date = timezone.now()
        emp.inactive_date = None
        emp.last_updated_id = admin.employee_id
        emp.last_updated_date = timezone.now()
        emp.save()
        messages.info(request, f"Employee {emp.emp_no} unblocked.")
        return redirect('employee_manage')
    except EmployeeMaster.DoesNotExist:
        messages.error(request, "Admin record not found.")
        return redirect('login')  
    return render(request,'admin_employee_manage.html')

def update_employee(request, emp_id):
    employee = get_object_or_404(EmployeeMaster, employee_id=emp_id)

    if request.method == 'POST':
        employee.emp_no = request.POST.get('emp_no')
        employee.firstname_eng = request.POST.get('firstname_eng')
        employee.lastname_eng = request.POST.get('lastname_eng')

        organization_id = request.POST.get('organization_id')
        if organization_id:
            employee.organization_id = get_object_or_404(Organization, organization_id=organization_id)

        passport_issue_country_id = request.POST.get('passport_issue_country')
        if passport_issue_country_id:
            employee.passport_issue_country_id = get_object_or_404(Country, country_id=passport_issue_country_id)

        designation_id = request.POST.get('designation_id')
        if designation_id:
            employee.designation_id = get_object_or_404(Designation, designation_id=designation_id)

        employee_type_id = request.POST.get('employee_type_id')
        if employee_type_id:
            employee.employee_type_id = get_object_or_404(EmployeeType, employee_type_id=employee_type_id)

        work_location_id = request.POST.get('work_location_id')
        if work_location_id:
            employee.work_location_id = get_object_or_404(Location, location_id=work_location_id)

        contractor_company_id = request.POST.get('contract_company_id')
        if contractor_company_id:
            employee.contract_company_id = get_object_or_404(ContractorCompany, contractor_company_id=contractor_company_id)

        grade_id = request.POST.get('grade_id')
        if grade_id:
            employee.grade_id = get_object_or_404(Grade, grade_id=grade_id)
        
        manager_id = request.POST.get('manager_id')
        if manager_id:
            employee.manager_id = get_object_or_404(EmployeeMaster, employee_id=manager_id)
        else:
            employee.manager_id = None

        employee.join_date = request.POST.get('join_date') or None
        employee.active_date = request.POST.get('active_date') or None
        employee.remarks = request.POST.get('remarks') or ''

        # Optional flags
        employee.open_shift_flag = request.POST.get('open_shift_flag') == '1'
        employee.overtime_flag = request.POST.get('overtime_flag') == '1'
        employee.manager_flag = request.POST.get('manager_flag') or 'N'

        if 'photo_file_name' in request.FILES:
            employee.photo_file_name = request.FILES['photo_file_name']

        employee.save()

        messages.success(request, f"Employee {employee.emp_no} updated successfully.")
        return redirect('employee_manage')

    return render(request, 'admin_update_employee_details.html', {
        'employee': employee,
        'employees': EmployeeMaster.objects.all(),
        'organizations': Organization.objects.all(),
        'designations': Designation.objects.all(),
        'countries': Country.objects.all(),
        'employee_types': EmployeeType.objects.all(),
        'locations': Location.objects.all(),
        'contractor_companies': ContractorCompany.objects.all(),
        'grades': Grade.objects.all(),
        'managers': EmployeeMaster.objects.filter(active_flag=1, manager_flag='Y')
    })

@custom_login_required
def country_list(request):
    q = request.GET.get('q', '').strip()
    qs = Country.objects.all()
    if q:
        qs = qs.filter(country_code__icontains=q) | qs.filter(country_eng__icontains=q)
    qs = qs.order_by('country_eng')
    paginator = Paginator(qs, 5)
    page = request.GET.get('page')
    countries = paginator.get_page(page)
    
    return render(request, 'admin_add_country.html', {'countries': countries, 'q': q})


@custom_login_required
def country_add(request):
    if request.method == 'POST':
        code = request.POST['country_code'].strip().upper()
        name = request.POST['country_eng'].strip()
        flag = request.POST['country_flag_url'].strip()
        if not code.isalpha():
            messages.error(request, "Country code must contain only letters")
        elif Country.objects.filter(country_code=code).exists():
            messages.error(request, f"Country code '{code}' already exists")
        elif Country.objects.filter(country_eng__iexact=name).exists():
            messages.error(request, f"Country '{name}' already exists")
        else:
            Country.objects.create(
                country_code=code,
                country_eng=name,
                country_arb=name,
                country_flag_url=flag,
                created_id=request.session['employee_id'],
                last_updated_id=request.session['employee_id'],
                created_date=now(),
                last_updated_date=now(),
            )
            messages.info(request, f"Country '{name}' added successfully")
            return redirect('country_list')
    return redirect('country_list')


@custom_login_required
def country_update(request):
    if request.method == 'POST':
        updated = []
        total = int(request.POST.get('total_rows', '0'))
        for i in range(1, total+1):
            cid = int(request.POST.get(f'id_{i}')) 
            code = request.POST.get(f'code_{i}','').strip().upper()
            name = request.POST.get(f'name_{i}','').strip()
            flag = request.POST.get(f'flag_{i}','').strip()
            country = get_object_or_404(Country, country_id=cid)
            changed = False
            if country.country_code != code:
                if Country.objects.filter(country_code=code).exclude(pk=cid).exists():
                    messages.error(request, f"Conflict code '{code}'")
                    continue
                country.country_code = code
                changed = True
            if country.country_eng != name:
                if Country.objects.filter(country_eng__iexact=name).exclude(pk=cid).exists():
                    messages.error(request, f"Conflict name '{name}'")
                    continue
                country.country_eng = name
                country.country_arb = name
                changed = True
            if country.country_flag_url != flag:
                country.country_flag_url = flag
                changed = True
            if changed:
                country.last_updated_id = request.session['employee_id']
                country.last_updated_date = now()
                country.save()
                updated.append(name)
        if updated:
            messages.info(request, f"Updated countries: {', '.join(updated)}")
    return redirect('country_list')

@custom_login_required
def country_delete(request):
    if request.method == 'POST':
        cid = request.POST.get('delete_id')
        try:
            country = Country.objects.get(country_id=cid)
            country_name = country.country_eng
            country.delete()
            messages.info(request, f"Deleted country '{country_name}' successfully.")
        except Country.DoesNotExist:
            messages.error(request, "Country not found.")
    return redirect('country_list')

@custom_login_required
def grade_list(request):
    q = request.GET.get('q', '').strip()
    qs = Grade.objects.all()
    if q:
        qs = qs.filter(code__icontains=q) | qs.filter(grade_eng__icontains=q)
    qs = qs.order_by('grade_eng')
    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    grades = paginator.get_page(page)
    return render(request, 'admin_add_grade.html', {'grades': grades, 'q': q})

@custom_login_required
def grade_add(request):
    if request.method == 'POST':
        code = request.POST['code'].strip().upper()
        name = request.POST['grade_eng'].strip()
        cl = request.POST.get('number_of_CL', 0)
        sl = request.POST.get('number_of_SL', 0)
        al = request.POST.get('number_of_AL', 0)
        overtime = request.POST.get('overtime_eligible_flag', 0)
        senior = request.POST.get('overtime_flag', 0)

        if Grade.objects.filter(code=code).exists():
            messages.error(request, f"Grade code '{code}' already exists.")
        elif Grade.objects.filter(grade_eng__iexact=name).exists():
            messages.error(request, f"Grade '{name}' already exists.")
        else:
            Grade.objects.create(
                code=code,
                grade_eng=name,
                grade_arb=name,
                number_of_CL=cl,
                number_of_SL=sl,
                number_of_AL=al,
                overtime_eligible_flag=overtime,
                senior_flag=senior,
                created_id=request.session['employee_id'],
                created_date=now(),
                last_updated_id=request.session['employee_id'],
                last_updated_date=now()
            )
            messages.success(request, f"Grade '{name}' added successfully.")
            return redirect('grade_list')
    return redirect('grade_list')

@custom_login_required
def grade_update(request):
    if request.method == 'POST':
        updated = []
        total = int(request.POST.get('total_rows', 0))
        for i in range(1, total + 1):
            gid = int(request.POST.get(f'id_{i}', 0))
            code = request.POST.get(f'code_{i}', '').strip().upper()
            name = request.POST.get(f'grade_{i}', '').strip()
            grade = get_object_or_404(Grade, grade_id=gid)
            changed = False

            if grade.code != code:
                if Grade.objects.filter(code=code).exclude(pk=gid).exists():
                    messages.error(request, f"Conflict code '{code}'")
                    continue
                grade.code = code
                changed = True
            if grade.grade_eng != name:
                if Grade.objects.filter(grade_eng__iexact=name).exclude(pk=gid).exists():
                    messages.error(request, f"Conflict name '{name}'")
                    continue
                grade.grade_eng = name
                grade.grade_arb = name
                changed = True
            if changed:
                grade.last_updated_id = request.session['employee_id']
                grade.last_updated_date = now()
                grade.save()
                updated.append(name)

        if updated:
            messages.success(request, f"Updated grades: {', '.join(updated)}")
    return redirect('grade_list')

@custom_login_required
def grade_delete(request):
    if request.method == 'POST':
        gid = request.POST.get('delete_id')
        grade = get_object_or_404(Grade, pk=gid)
        name = grade.grade_eng
        grade.delete()
        messages.error(request, f"Grade '{name}' deleted.")
    return redirect('grade_list')

@custom_login_required
def designation_list(request):
    q = request.GET.get('q', '').strip()
    qs = Designation.objects.all()
    if q:
        filters = Q(code__icontains=q) | Q(designation_eng__icontains=q)
        if q.isdigit():
            filters |= Q(vacancy=int(q))
        qs = qs.filter(filters)
        
    paginator = Paginator(qs.order_by('designation_eng'), 10)
    page = request.GET.get('page')
    return render(request, 'admin_add_designation.html', {'designations': paginator.get_page(page), 'q': q})

@custom_login_required
def designation_add(request):
    if request.method == 'POST':
        code = request.POST['code'].strip()
        name = request.POST['designation_eng'].strip()
        vacancy = request.POST.get('vacancy', '').strip()
        remarks = request.POST.get('remarks', '').strip()
        if not (code and name and vacancy):
            messages.error(request, "Code, Name and Vacancy are required.")
        elif not code[0].isalpha() or not name[0].isalpha():
            messages.error(request, "Code and Name must start with a letter.")
        elif Designation.objects.filter(code__iexact=code).exists():
            messages.error(request, f"Code '{code}' already exists.")
        else:
            des = Designation.objects.create(
                code=code, designation_eng=name, designation_arb=name,
                vacancy=int(vacancy), remarks=remarks,
                created_id=request.session['employee_id'], last_updated_id=request.session['employee_id'],
                created_date=now(), last_updated_date=now()
            )
            messages.info(request, f"Designation '{name}' added.")
            return redirect('designation_list')
    return redirect('designation_list')

@custom_login_required
def designation_update(request):
    if request.method == 'POST':
        total = int(request.POST.get('total_rows', 0))
        updated = []
        for i in range(1, total+1):
            did = request.POST.get(f'id_{i}')
            des = get_object_or_404(Designation, designation_id=did)
            code = request.POST.get(f'code_{i}', '').strip()
            name = request.POST.get(f'name_{i}', '').strip()
            vacancy = request.POST.get(f'vacancy_{i}', '').strip()
            remarks = request.POST.get(f'remarks_{i}', '').strip()
            changed = False

            if code and code[0].isalpha() and code.lower() != des.code.lower():
                if Designation.objects.filter(code__iexact=code).exclude(pk=did).exists():
                    messages.error(request, f"Duplicate code '{code}'")
                else:
                    des.code = code; changed = True

            if name and name[0].isalpha() and name.lower() != des.designation_eng.lower():
                des.designation_eng = name; des.designation_arb = name; changed = True

            if vacancy.isdigit() and int(vacancy) != des.vacancy:
                des.vacancy = int(vacancy); changed = True

            if remarks != des.remarks:
                des.remarks = remarks; changed = True

            if changed:
                des.last_updated_id = request.session['employee_id']
                des.last_updated_date = now()
                des.save()
                updated.append(des.designation_eng)

        if updated:
            messages.info(request, "Updated: " + ", ".join(updated))
    return redirect('designation_list')

@custom_login_required
def designation_delete(request):
    if request.method == 'POST':
        did = request.POST.get('delete_id')
        print(did)
        des = get_object_or_404(Designation, designation_id=did)
        name = des.designation_eng
        print(name)
        des.delete()
        messages.info(request, f"Deleted: {name}")
    return redirect('designation_list')

@custom_login_required
def employee_type_list(request):
    q = request.GET.get('q', '')
    employee_types = EmployeeType.objects.filter(
        Q(employee_type_code__icontains=q) | Q(employee_type_eng__icontains=q)
    ).order_by('-last_updated_date')

    paginator = Paginator(employee_types, 10)
    page = request.GET.get('page')
    employee_types = paginator.get_page(page)

    return render(request, 'admin_add_employee_type.html', {
        'employee_types': employee_types,
        'q': q
    })

@custom_login_required
def employee_type_add(request):
    if request.method == 'POST':
        if EmployeeType.objects.count() >= 2:
            messages.error(request, "Only two employee types are allowed.")
            return redirect('employee_type_list')

        code = request.POST.get('code').strip()
        eng = request.POST.get('employee_type_eng').strip()
        arb = eng
        user_id = request.session.get('user_id')

        if EmployeeType.objects.filter(Q(employee_type_code=code) | Q(employee_type_eng=eng)).exists():
            messages.error(request, "Code or English Description already exists.")
        else:
            EmployeeType.objects.create(
                employee_type_code=code,
                employee_type_eng=eng,
                employee_type_arb=arb,
                created_id=user_id,
                last_updated_id=user_id
            )
            messages.success(request, f"Added: {eng}")
    return redirect('employee_type_list')

@custom_login_required
def employee_type_update(request):
    if request.method == 'POST':
        total = int(request.POST.get('total_rows'))
        user_id = request.session.get('user_id')
        for i in range(1, total + 1):
            eid = request.POST.get(f'id_{i}')
            code = request.POST.get(f'code_{i}').strip()
            eng = request.POST.get(f'eng_{i}').strip()
            arb = eng

            et = get_object_or_404(EmployeeType, employee_type_id=eid)
            if (EmployeeType.objects.exclude(employee_type_id=eid)
                .filter(Q(employee_type_code=code) | Q(employee_type_eng=eng))
                .exists()):
                messages.error(request, f"Duplicate for {eng} not allowed.")
            else:
                et.employee_type_code = code
                et.employee_type_eng = eng
                et.employee_type_arb = arb
                et.last_updated_id = user_id
                et.last_updated_date = now()
                et.save()
                messages.success(request, f"Updated: {eng}")
    return redirect('employee_type_list')

@custom_login_required
def employee_type_delete(request):
    if request.method == 'POST':
        eid = request.POST.get('delete_id')
        et = get_object_or_404(EmployeeType, employee_type_id=eid)
        messages.info(request, f"Deleted: {et.employee_type_eng}")
        et.delete()
    return redirect('employee_type_list')

@custom_login_required
def permission_type_list(request):
    q = request.GET.get('q','').strip()
    qs = PermissionType.objects.all()
    if q:
        qs = qs.filter(
            Q(code__icontains=q) |
            Q(permdescription_eng__icontains=q) |
            Q(specific_gender__iexact=q)
        )
    paginator = Paginator(qs.order_by('permdescription_eng'), 10)
    page = request.GET.get('page')
    return render(request, 'admin_add_permission_type.html', {
        'items': paginator.get_page(page), 'q': q
    })

@custom_login_required
def permission_type_add(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        desc = request.POST.get('permdescription_eng', '').strip()
        max_perm_day = request.POST.get('max_perm_per_day') or 0
        max_mins_day = request.POST.get('max_minutes_per_day') or 0
        max_perm_month = request.POST.get('max_perm_per_month') or 0
        max_mins_month = request.POST.get('max_minutes_per_month') or 0
        gender = request.POST.get('specific_gender') or None
        status_flag = bool(request.POST.get('Status_Flag'))
        user_id = request.session.get('user_id')

        # Validation: reject only if same desc and same gender
        duplicate = PermissionType.objects.filter(
            permdescription_eng__iexact=desc,
            specific_gender=gender
        ).exists()

        if duplicate:
            messages.error(request, "Permission with same description and gender already exists.")
            return redirect('permission_type_list')

        try:
            PermissionType.objects.create(
                code=code,
                permdescription_eng=desc,
                permdescription_arb=desc,  # assuming Arabic is same as English
                max_perm_per_day=max_perm_day,
                max_minutes_per_day=max_mins_day,
                max_perm_per_month=max_perm_month,
                max_minutes_per_month=max_mins_month,
                specific_gender=gender,
                group_apply_flag=0,
                official_flag=0,
                full_day_flag=0,
                Status_Flag=status_flag,
                Workflow_Id=1,
                created_id=user_id,
                created_date=timezone.now(),
                last_updated_id=user_id,
                last_updated_time=timezone.now()
            )
            messages.success(request, f"Permission type '{desc}' added.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('permission_type_list')


@custom_login_required
def permission_type_update(request):
    if request.method == 'POST':
        total = int(request.POST.get('total_rows', '0'))

        def get_int(key):
            val = request.POST.get(key)
            return int(val) if val and val.isdigit() else 0

        for i in range(1, total + 1):
            pid = request.POST.get(f'id_{i}')
            obj = get_object_or_404(PermissionType, permission_type_id=pid)
            new_code = request.POST.get(f'code_{i}')
            new_desc = request.POST.get(f'desc_{i}')
            new_mpd = request.POST.get(f'mpd_{i}')
            new_mmpd = request.POST.get(f'mmpd_{i}')
            new_mpom = request.POST.get(f'mpom_{i}')
            new_mmom = request.POST.get(f'mmom_{i}')
            new_status = request.POST.get(f'status_{i}') == '1'
            gender_val = request.POST.get(f'gender_{i}')
            new_gender = gender_val if gender_val in ['M', 'F'] else None
            if (
                obj.code != new_code or
                obj.permdescription_eng != new_desc or
                str(obj.max_perm_per_day) != new_mpd or
                str(obj.max_minutes_per_day) != new_mmpd or
                str(obj.max_perm_per_month) != new_mpom or
                str(obj.max_minutes_per_month) != new_mmom or
                obj.Status_Flag != new_status or
                obj.specific_gender != new_gender
                ):
                obj.code = new_code
                obj.permdescription_eng = new_desc
                obj.max_perm_per_day = int(new_mpd) if new_mpd else None
                obj.max_minutes_per_day = int(new_mmpd) if new_mmpd else None
                obj.max_perm_per_month = int(new_mpom) if new_mpom else None
                obj.max_minutes_per_month = int(new_mmom) if new_mmom else None
                obj.Status_Flag = new_status
                obj.specific_gender = new_gender
                obj.last_updated_id = request.session['employee_id']
                obj.last_updated_time = now()
                obj.save()
        messages.success(request, 'Updated successfully.')
    return redirect('permission_type_list')

@custom_login_required
def permission_type_delete(request):
    if request.method=='POST':
        pid = request.POST.get('delete_id')
        obj = get_object_or_404(PermissionType, permission_type_id=pid)
        obj.delete()
        messages.info(request, f'Deleted "{obj.permdescription_eng}".')
    return redirect('permission_type_list')

def leave_type_list(request):
    q = request.GET.get('q', '').strip()
    leaves = LeaveType.objects.all()

    if q:
        gender_filter = None
        if q.lower() in ['female', 'girl', 'woman', 'women', 'lady', 'f']:
            gender_filter = 'F'
        elif q.lower() in ['male', 'man', 'boy', 'gentleman', 'm']:
            gender_filter = 'M'

        leaves = leaves.filter(
            Q(code__icontains=q) |
            Q(leaveDesc_eng__icontains=q) |
            Q(specific_gender=gender_filter) if gender_filter else Q()
        )

    paginator = Paginator(leaves.order_by('-last_updated_date'), 10)
    page = request.GET.get('page')
    items = paginator.get_page(page)

    return render(request, 'admin_add_leave_type.html', {
        'items': items,
        'q': q
    })


@custom_login_required
def leave_type_add(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        code = request.POST.get('code', '').strip()
        desc = request.POST.get('leaveDesc_eng', '').strip()
        gender = request.POST.get('specific_gender', '') or None
        status_flag = request.POST.get('status_Flag') == '1'
        official_flag = request.POST.get('official_flag') == '1'
        comment_required = request.POST.get('is_comment_mandatory') == '1'
        total_days = request.POST.get('total_entitled_days') or 0
        full = request.POST.get('full_pay_days') or 0
        half = request.POST.get('half_pay_days') or 0
        unpaid = request.POST.get('unpaidDays') or 0
        prior_days = request.POST.get('apply_prior_to_days') or 0

        # Validation: exactly one pay-type must be non-zero
        nonzero_count = sum(bool(float(x)) for x in [full, half, unpaid])
        if nonzero_count != 1:
            messages.error(request, "Please specify exactly one of full‑pay, half‑pay or unpaid days.")
            return redirect('leave_type_list')

        try:
            LeaveType.objects.create(
                code=code,
                leaveDesc_eng=desc,
                leaveDesc_arb=desc,
                official_flag=official_flag,
                status_Flag=status_flag,
                is_comment_mandatory=comment_required,
                total_entitled_days=total_days,
                full_pay_days=full,
                half_pay_days=half,
                unpaidDays=unpaid,
                apply_prior_to_days=prior_days,
                specific_gender=gender,
                approve_need_flag=1,
                allow_attachment=1,
                workflow_Id=1,
                created_id=user_id,
                created_date=timezone.now(),
                last_updated_id=user_id,
                last_updated_date=timezone.now()
            )
            messages.success(request, f"Leave Type '{code}' added.")
        except IntegrityError as e:
            messages.error(request, f"Error: {e}")
    return redirect('leave_type_list')

@custom_login_required
def leave_type_update(request):
    if request.method == 'POST':
        total = int(request.POST.get('total_rows', 0))
        user_id = request.session.get('user_id')
        updated_count = 0

        for i in range(1, total + 1):
            try:
                obj = LeaveType.objects.get(leave_type_id=request.POST[f'id_{i}'])
            except LeaveType.DoesNotExist:
                continue

            # Get and normalize input
            gender_raw = request.POST.get(f'gender_{i}', '').strip().upper()
            gender_value = gender_raw if gender_raw in ['M', 'F'] else None

            new_data = {
                'code': request.POST.get(f'code_{i}', '').strip(),
                'desc': request.POST.get(f'desc_{i}', '').strip(),
                'gender': gender_value,
                'total': request.POST.get(f'total_{i}', '').strip(),
                'full': request.POST.get(f'full_{i}', '').strip(),
                'half': request.POST.get(f'half_{i}', '').strip(),
                'unpaid': request.POST.get(f'unpaid_{i}', '').strip(),
                'prior': request.POST.get(f'prior_{i}', '').strip(),
                'comment': request.POST.get(f'comment_{i}', '0') == '1',
                'official': request.POST.get(f'official_{i}', '0') == '1',
                'status': request.POST.get(f'status_{i}', '0') == '1',
            }

            # Validation: only one of full/half/unpaid can be > 0
            full = float(new_data['full'] or 0)
            half = float(new_data['half'] or 0)
            unpaid = float(new_data['unpaid'] or 0)
            if sum(1 for v in [full, half, unpaid] if v > 0) != 1:
                messages.error(request, f"Row {i}: Only one of Full, Half, or Unpaid days must be non-zero.")
                continue

            changed = False
            if obj.code != new_data['code']:
                obj.code = new_data['code']; changed = True
            if obj.leaveDesc_eng != new_data['desc']:
                obj.leaveDesc_eng = new_data['desc']; changed = True
            if obj.specific_gender != new_data['gender']:
                obj.specific_gender = new_data['gender']; changed = True
            if str(obj.total_entitled_days) != new_data['total']:
                obj.total_entitled_days = new_data['total']; changed = True
            if str(obj.full_pay_days) != new_data['full']:
                obj.full_pay_days = new_data['full']; changed = True
            if str(obj.half_pay_days) != new_data['half']:
                obj.half_pay_days = new_data['half']; changed = True
            if str(obj.unpaidDays) != new_data['unpaid']:
                obj.unpaidDays = new_data['unpaid']; changed = True
            if str(obj.apply_prior_to_days) != new_data['prior']:
                obj.apply_prior_to_days = new_data['prior']; changed = True
            if obj.is_comment_mandatory != new_data['comment']:
                obj.is_comment_mandatory = new_data['comment']; changed = True
            if obj.official_flag != int(new_data['official']):
                obj.official_flag = int(new_data['official']); changed = True
            if obj.status_Flag != new_data['status']:
                obj.status_Flag = new_data['status']; changed = True

            if changed:
                obj.last_updated_id = user_id
                obj.last_updated_date = now()
                obj.save()
                updated_count += 1

        if updated_count:
            messages.success(request, f"{updated_count} leave type(s) updated.")
        else:
            messages.info(request, "No changes detected.")
    return redirect('leave_type_list')

@custom_login_required
def leave_type_delete(request):
    if request.method == 'POST':
        pk = request.POST.get('delete_id')
        lt = get_object_or_404(LeaveType, leave_type_id=pk)
        code = lt.code
        lt.delete()
        messages.info(request, f"Deleted leave type '{code}'.")
    return redirect('leave_type_list')

def employee_group_list(request):
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '').strip()
    groups = EmployeeGroup.objects.all()

    if q:
        groups = groups.filter(
            Q(group_code__icontains=q) | Q(group_name_eng__icontains=q)
        )

    # Sorting logic
    if sort == "code":
        groups = groups.order_by("group_code")
    elif sort == "start":
        groups = groups.order_by("group_start_Date")
    elif sort == "end":
        groups = groups.order_by("group_end_Date")
    elif sort == "schedule":
        groups = groups.order_by("-schedule_flag")

    paginator = Paginator(groups, 10)
    page = request.GET.get('page')
    items = paginator.get_page(page)

    return render(request, 'admin_create_group.html', {
        "items": items,
        "q": q,
        "sort": sort,
        "today": date.today()
    })

def employee_group_list(request):
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '').strip()
    groups = EmployeeGroup.objects.all()

    if q:
        groups = groups.filter(
            Q(group_code__icontains=q) | Q(group_name_eng__icontains=q)
        )

    # Sorting logic
    if sort == "code":
        groups = groups.order_by("group_code")
    elif sort == "start":
        groups = groups.order_by("group_start_Date")
    elif sort == "end":
        groups = groups.order_by("group_end_Date")
    elif sort == "schedule":
        groups = groups.order_by("-schedule_flag")

    paginator = Paginator(groups, 10)
    page = request.GET.get('page')
    items = paginator.get_page(page)

    return render(request, 'admin_create_group.html', {
        "items": items,
        "q": q,
        "sort": sort,
        "today": date.today(),
    })
    
@custom_login_required
def employee_group_add(request):
    if request.method == 'POST':
        code = request.POST['code'].strip()
        name = request.POST['name'].strip()
        sched = request.POST.get('schedule_flag') == '1'
        user = request.session.get('user_id')

        try:
            start = datetime.strptime(request.POST['start'], "%Y-%m-%d").date()
            end = datetime.strptime(request.POST['end'], "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('employee_group_list')

        # validations
        if EmployeeGroup.objects.filter(group_code__iexact=code).exists():
            messages.error(request, "Code must be unique.")
        elif start >= end:
            messages.error(request, "Start date must be before end date.")
        elif start < now().date().replace(year=now().year - 1):
            messages.error(request, "Start date cannot be older than 1 year from today.")
        else:
            EmployeeGroup.objects.create(
                group_code=code,
                group_name_eng=name,
                schedule_flag=int(sched),
                group_start_Date=start,
                group_end_Date=end,
                created_id=user,
                last_updated_id=user,
                created_date=now(),
                last_updated_date=now()
            )
            messages.success(request, f"Added group: {name}")
    return redirect('employee_group_list')

@custom_login_required
def employee_group_update(request):
    if request.method == 'POST':
        total = int(request.POST.get('total_rows', 0))
        user = request.session.get('user_id')
        updated = 0

        for i in range(1, total + 1):
            gid = request.POST.get(f'id_{i}')
            obj = get_object_or_404(EmployeeGroup, employee_group_id=gid)

            new_code = request.POST.get(f'code_{i}', '').strip()
            new_name = request.POST.get(f'name_{i}', '').strip()
            new_schedule = request.POST.get(f'schedule_{i}') == '1'
            new_start_str = request.POST.get(f'start_{i}')
            new_end_str = request.POST.get(f'end_{i}')

            try:
                new_start = datetime.strptime(new_start_str, "%Y-%m-%d").date()
                new_end = datetime.strptime(new_end_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, f"Row {i}: Invalid date format.")
                continue

            # Validation checks
            if EmployeeGroup.objects.exclude(pk=gid).filter(group_code__iexact=new_code).exists():
                messages.error(request, f"Row {i}: Code '{new_code}' already exists.")
                continue

            if new_start >= new_end:
                messages.error(request, f"Row {i}: Start date must be before end date.")
                continue

            if new_start < now().date().replace(year=now().year - 1):
                messages.error(request, f"Row {i}: Start date cannot be older than 1 year from today.")
                continue

            # Check what changed
            changed = False
            if obj.group_code != new_code:
                obj.group_code = new_code; changed = True
            if obj.group_name_eng != new_name:
                obj.group_name_eng = new_name; changed = True
            if obj.schedule_flag != int(new_schedule):
                obj.schedule_flag = int(new_schedule); changed = True
            if obj.group_start_Date.date() != new_start:
                obj.group_start_Date = new_start; changed = True
            if obj.group_end_Date.date() != new_end:
                obj.group_end_Date = new_end; changed = True

            if changed:
                obj.last_updated_id = user
                obj.last_updated_date = now()
                obj.save()
                updated += 1

        if updated:
            messages.success(request, f"{updated} group(s) updated.")

    return redirect('employee_group_list')

@custom_login_required
def employee_group_delete(request):
    if request.method == 'POST':
        gid = request.POST.get('delete_id')
        try:
            grp = EmployeeGroup.objects.get(employee_group_id=gid)
            grp.delete()
            messages.success(request, "Deleted group.")
        except EmployeeGroup.DoesNotExist:
            messages.error(request, "Could not find group.")
    return redirect('employee_group_list')

@custom_login_required
def admin_add_members(request, group_id):
    group = get_object_or_404(EmployeeGroup, employee_group_id=group_id)
    active_employees = EmployeeMaster.objects.filter(active_flag=1)
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date', None)
        active_flag = request.POST.get('active_flag', 1)
        
        employee = get_object_or_404(EmployeeMaster, employee_id=employee_id)
        
        # Insert member record
        member = EmployeeGroupMember(
            employee_group_id=group,
            employee_id=employee,
            effective_from_date=from_date,
            effective_to_date=to_date,
            active_flag=active_flag,
            created_id=request.session['employee_id'],  # Assuming the user making the update is stored in `request.user`
            last_updated_id=request.session['employee_id'],
            last_updated_date=now()
        )
        member.save()
        messages.success(request, 'Member added successfully!')
        return redirect('admin_add_members', group_id=group.employee_group_id)  # Redirect using group_id

    return render(request, 'admin_add_members.html', {
        'group': group,
        'active_employees': active_employees,
        'members': group.employeegroupmember_set.all(),
    })

@custom_login_required
def admin_update_member(request, group_id, member_id):
    member = get_object_or_404(EmployeeGroupMember, group_member_id=member_id)
    
    # Check group authorization
    if member.employee_group_id.employee_group_id != group_id:
        return HttpResponseForbidden('You are not authorized to edit this member.')

    if request.method == 'POST':
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date') or None
        active_flag = int(request.POST.get('active_flag', 1))
        employee_id = request.POST.get('employee_id')  # ✅ Capture new employee

        # Convert string to datetime
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect('admin_add_members', group_id=group_id)

        # Group date validation
        group = member.employee_group_id
        if group.group_start_Date and from_dt < group.group_start_Date:
            messages.error(request, f"Start date must be on or after group start date ({group.group_start_Date.date()}).")
            return redirect('admin_add_members', group_id=group_id)

        if to_dt and group.group_end_Date and to_dt > group.group_end_Date:
            messages.error(request, f"End date must be on or before group end date ({group.group_end_Date.date()}).")
            return redirect('admin_add_members', group_id=group_id)

        # Update fields
        member.effective_from_date = from_date
        member.effective_to_date = to_date
        member.active_flag = active_flag
        member.last_updated_id = request.session['employee_id']
        member.last_updated_date = now()

        if employee_id:
            try:
                member.employee_id = EmployeeMaster.objects.get(employee_id=employee_id)
            except EmployeeMaster.DoesNotExist:
                messages.error(request, "Selected employee does not exist.")
                return redirect('admin_add_members', group_id=group_id)

        member.save()
        messages.success(request, 'Member updated successfully!')
        return redirect('admin_add_members', group_id=group_id)

    return render(request, 'admin_add_members.html', {
        'member': member,
    })


@custom_login_required
def admin_delete_member(request, group_id, member_id):
    member = get_object_or_404(EmployeeGroupMember, group_member_id=member_id)
    if member.employee_group_id.employee_group_id != group_id:
        return HttpResponseForbidden('You are not authorized to delete this member.')
    
    member.delete()
    messages.success(request, 'Member deleted successfully!')
    return redirect('admin_add_members', group_id=group_id)  



def combine_today_with_time(timestr):
    h, m = map(int, timestr.split(':'))
    return datetime.combine(date.today(), time(h, m))

def schedule_page(request):
    q = request.GET.get('q', '')
    schedules = Schedule.objects.select_related('organization_id')
    if q:
        schedules = schedules.filter(schedule_code__icontains=q)

    special_map = {s.sch_parent_id: s for s in Schedule.objects.filter(sch_parent__isnull=False)}
    
    context = {
        'schedules': schedules,
        'organizations': Organization.objects.all(),
        'special_map': special_map,
        'q': q,
    }
    return render(request, 'admin_add_schedule.html', context)

def add_schedule(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')

        normal = Schedule(
            organization_id_id=request.POST['normal_organization_id'],
            schedule_code=request.POST['normal_schedule_code'],
            in_time=combine_today_with_time(request.POST['normal_in_time']),
            out_time=combine_today_with_time(request.POST['normal_out_time']),
            flexible_min=request.POST['normal_flexible_min'],
            grace_in_min=request.POST['normal_grace_in_min'],
            grace_out_min=request.POST['normal_grace_out_min'],
            open_shift=1 if 'normal_open_shift' in request.POST else 0,
            night_shift=1 if 'normal_night_shift' in request.POST else 0,
            sch_color=request.POST['normal_sch_color'],
            required_work_hours=combine_today_with_time(request.POST.get('normal_required_work_hours', '00:00')),
            Status_Flag='normal_Status_Flag' in request.POST,
            created_id=user_id,
            created_date=now(),
            last_updated_id=user_id,
            last_updated_date=now()
        )
        normal.save()

        if request.POST.get('special_schedule_code'):
            Schedule.objects.create(
                organization_id_id=request.POST['special_organization_id'],
                schedule_code=request.POST['special_schedule_code'],
                in_time=combine_today_with_time(request.POST['special_in_time']),
                out_time=combine_today_with_time(request.POST['special_out_time']),
                flexible_min=request.POST['special_flexible_min'],
                grace_in_min=request.POST['special_grace_in_min'],
                grace_out_min=request.POST['special_grace_out_min'],
                open_shift=1 if 'special_open_shift' in request.POST else 0,
                night_shift=1 if 'special_night_shift' in request.POST else 0,
                sch_color=request.POST['special_sch_color'],
                required_work_hours=combine_today_with_time(request.POST.get('special_required_work_hours', '00:00')),
                Status_Flag='special_Status_Flag' in request.POST,
                sch_parent=normal,
                created_id=user_id,
                created_date=now(),
                last_updated_id=user_id,
                last_updated_date=now()
            )

    return redirect('admin_add_schedule')

def delete_schedule(request, schedule_id):
    try:
        schedule = Schedule.objects.get(schedule_id=schedule_id)
        if schedule.sch_parent_id is None:
            Schedule.objects.filter(sch_parent_id=schedule_id).delete()
        schedule.delete()
        messages.success(request, "Schedule deleted successfully.")
    except Schedule.DoesNotExist:
        messages.error(request, "Schedule not found.")
    return redirect('admin_add_schedule')

def edit_schedule(request, schedule_id):
    schedule = get_object_or_404(Schedule, pk=schedule_id)

    if request.method == 'POST':
        schedule_type = request.POST.get('schedule_type')  # 'normal' or 'special'
        prefix = f"{schedule_type}_"

        schedule.schedule_code = request.POST.get(prefix + 'schedule_code')
        schedule.in_time = combine_today_with_time(request.POST.get(prefix + 'in_time'))
        schedule.out_time = combine_today_with_time(request.POST.get(prefix + 'out_time'))
        schedule.flexible_min = int(request.POST.get(prefix + 'flexible_min') or 0)
        schedule.grace_in_min = int(request.POST.get(prefix + 'grace_in_min') or 0)
        schedule.grace_out_min = int(request.POST.get(prefix + 'grace_out_min') or 0)
        schedule.open_shift = 1 if request.POST.get(prefix + 'open_shift') == '1' else 0
        schedule.night_shift = 1 if request.POST.get(prefix + 'night_shift') == '1' else 0
        schedule.required_work_hours = combine_today_with_time(request.POST.get(prefix + 'required_work_hours', '00:00'))
        schedule.sch_color = request.POST.get(prefix + 'sch_color') or '#000000'
        schedule.Status_Flag = True if request.POST.get(prefix + 'Status_Flag') else False

        schedule.last_updated_id = request.session.get('user_id')
        schedule.last_updated_date = now()

        schedule.save()
        messages.success(request, 'Schedule updated successfully.')

    return redirect('admin_add_schedule')



def org_schedule_page(request):
    q = request.GET.get('q', '').strip()

    # Add all schedule foreign keys to select_related for eager loading
    qs = OrganizationSchedule.objects.select_related(
        'organization_id',
        'monday_schedule_id',
        'tuesday_schedule_id',
        'wednesday_schedule_id',
        'thursday_schedule_id',
        'friday_schedule_id',
        'saturday_schedule_id',
        'sunday_schedule_id'
    )

    filters = Q()
    if q:
        try:
            parsed_date = parser.parse(q, fuzzy=True).date()
            filters |= Q(from_date__date=parsed_date) | Q(to_date__date=parsed_date)
        except (ValueError, OverflowError):
            filters |= Q(organization_id__organization_eng__icontains=q)
            if q.isdigit():
                filters |= Q(from_date__year=int(q)) | Q(to_date__year=int(q))

    qs = qs.filter(filters)

    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    org_schedules = []
    for os in qs:
        day_schedules = OrderedDict()
        for day in days_list:
            day_field = f"{day.lower()}_schedule_id"
            schedule = getattr(os, day_field, None)  # Should be Schedule instance or None
            day_schedules[day] = schedule
        org_schedules.append({
            'obj': os,
            'days': day_schedules
        })

    context = {
        'org_schedules': org_schedules,
        'organizations': Organization.objects.all(),
        'all_schedules': Schedule.objects.all(),
        'q': q,
        'days_list': days_list,
    }
    return render(request, 'admin_add_org_schedule.html', context)


def add_org_schedule(request):
    if request.method == 'POST':
        data = request.POST
        osch = OrganizationSchedule(
            organization_id_id=data['organization_id'],
            from_date=data['from_date'],
            to_date=data.get('to_date') or None,
            created_id=request.session.get('user_id'),
            last_updated_id=request.session.get('user_id'),
            last_updated_date=datetime.now()
        )

        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            val = data.get(f'{day}_schedule_id')
            if val:
                try:
                    schedule_instance = Schedule.objects.get(pk=int(val))
                    setattr(osch, f'{day}_schedule_id', schedule_instance)
                except Schedule.DoesNotExist:
                    setattr(osch, f'{day}_schedule_id', None)
            else:
                setattr(osch, f'{day}_schedule_id', None)

        osch.save()
        messages.success(request, 'Organization Schedule added.')
    return redirect('admin_add_org_schedule')

def edit_org_schedule(request, pk):
    osch = get_object_or_404(OrganizationSchedule, pk=pk)
    if request.method == 'POST':
        data = request.POST
        osch.organization_id_id = data['organization_id']
        osch.from_date = data['from_date']
        osch.to_date = data.get('to_date') or None
        osch.last_updated_id = request.session.get('user_id')
        osch.last_updated_date = datetime.now()

        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            val = data.get(f'{day}_schedule_id')
            if val:
                schedule_instance = Schedule.objects.get(pk=int(val))
                setattr(osch, f'{day}_schedule_id', schedule_instance)
            else:
                setattr(osch, f'{day}_schedule_id', None)

        osch.save()
        messages.success(request, 'Schedule updated.')
    return redirect('admin_add_org_schedule')



def delete_org_schedule(request, pk):
    osch = get_object_or_404(OrganizationSchedule, pk=pk)
    osch.delete()
    messages.success(request, 'Schedule deleted.')
    return redirect('admin_add_org_schedule')


def group_schedule_page(request):
    q = request.GET.get('q', '').strip()
    qs = GroupSchedule.objects.select_related('employee_group_id')

    filters = Q()
    if q:
        try:
            parsed_date = parser.parse(q, fuzzy=True).date()
            filters |= Q(from_date__date=parsed_date) | Q(to_date__date=parsed_date)
        except (ValueError, OverflowError):
            filters |= Q(employee_group_id__group_name_eng__icontains=q)
    qs = qs.filter(filters)

    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    grp_schedules = []
    for gs in qs:
        day_schedules = OrderedDict()
        for day in days_list:
            field = f"{day.lower()}_schedule_id"
            day_schedules[day] = getattr(gs, field, None)
        grp_schedules.append({
            'obj': gs,
            'days': day_schedules
        })

    context = {
        'grp_schedules': grp_schedules,
        'groups': EmployeeGroup.objects.all(),
        'all_schedules': Schedule.objects.all(),
        'q': q,
        'days_list': days_list,
    }
    return render(request, 'admin_add_grp_schedule.html', context)

def admin_add_grp_schedule(request):
    if request.method == 'POST':
        data = request.POST
        print("POST data:", request.POST)

        gs = GroupSchedule(
            employee_group_id_id=data['employee_group_id'],
            from_date=data['from_date'],
            to_date=data.get('to_date') or None,
            created_id=request.session.get('user_id'),
            last_updated_id=request.session.get('user_id'),
            last_updated_time=datetime.now()
        )

        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            val = data.get(f'{day}_schedule_id')
            setattr(gs, f'{day}_schedule_id', Schedule.objects.get(pk=int(val)) if val else None)

        gs.save()
        messages.success(request, 'Group Schedule added successfully.')
        return redirect('group_schedule_page')

    # GET handling
    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    qs = GroupSchedule.objects.select_related('employee_group_id')
    grp_schedules = []

    for gs in qs:
        day_schedules = OrderedDict()
        for day in days_list:
            day_field = f"{day.lower()}_schedule_id"
            day_schedules[day] = getattr(gs, day_field, None)
        grp_schedules.append({'obj': gs, 'days': day_schedules})

    return render(request, 'admin_add_grp_schedule.html')

def edit_grp_schedule(request, pk):
    gs = get_object_or_404(GroupSchedule, pk=pk)
    if request.method == 'POST':
        data = request.POST
        gs.employee_group_id_id = data['employee_group_id']
        gs.from_date = data['from_date']
        gs.to_date = data.get('to_date') or None
        gs.last_updated_id = request.session.get('user_id')
        gs.last_updated_time = datetime.now()
        for day in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']:
            val = data.get(f'{day}_schedule_id')
            setattr(gs, f'{day}_schedule_id', Schedule.objects.get(pk=int(val)) if val else None)
        gs.save()
        messages.success(request, 'Group Schedule updated.')
    return redirect('group_schedule_page')

def delete_grp_schedule(request, pk):
    if request.method == 'POST':
        GroupSchedule.objects.filter(pk=pk).delete()
        messages.success(request, 'Schedule deleted.')
    return redirect('group_schedule_page')


def employee_schedule_page(request):
    q = request.GET.get('q', '').strip()
    qs = EmployeeSchedule.objects.select_related('employee_id')

    filters = Q()
    if q:
        try:
            parsed_date = parser.parse(q, fuzzy=True).date()
            filters |= Q(from_date__date=parsed_date) | Q(to_date__date=parsed_date)
        except:
            filters |= Q(employee_id__employee_name__icontains=q)
            if q.isdigit():
                filters |= Q(from_date__year=q) | Q(to_date__year=q)

    qs = qs.filter(filters)

    days_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    emp_schedules = []
    for es in qs:
        day_schedules = OrderedDict()
        for day in days_list:
            field = f"{day.lower()}_schedule_id"
            day_schedules[day] = getattr(es, field, None)
        emp_schedules.append({'obj': es, 'days': day_schedules})

    context = {
        'emp_schedules': emp_schedules,
        'employees': EmployeeMaster.objects.filter(active_flag=1),
        'all_schedules': Schedule.objects.all(),
        'days_list': days_list,
        'q': q,
    }
    return render(request, 'admin_add_employee_schedule.html', context)

def add_employee_schedule(request):
    if request.method == 'POST':
        data = request.POST
        es = EmployeeSchedule(
            employee_id_id=data['employee_id'],
            from_date=data['from_date'],
            to_date=data.get('to_date') or None,
            created_id=request.session.get('user_id'),
            last_updated_id=request.session.get('user_id'),
            last_updated_date=datetime.now()
        )
        es.save()

        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            val = data.get(f'{day}_schedule_id')
            setattr(es, f'{day}_schedule_id', Schedule.objects.get(pk=int(val)) if val else None)

        es.save()
        messages.success(request, 'Employee schedule added.')
    return redirect('employee_schedule_page')

def edit_employee_schedule(request, pk):
    es = get_object_or_404(EmployeeSchedule, pk=pk)
    if request.method == 'POST':
        data = request.POST
        es.employee_id_id = data['employee_id']
        es.from_date = data['from_date']
        es.to_date = data.get('to_date') or None
        es.last_updated_id = request.session.get('user_id')
        es.last_updated_date = datetime.now()

        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            val = data.get(f'{day}_schedule_id')
            setattr(es, f'{day}_schedule_id', Schedule.objects.get(pk=int(val)) if val else None)

        es.save()
        messages.success(request, 'Employee schedule updated.')
    return redirect('employee_schedule_page')

def delete_employee_schedule(request, pk):
    es = get_object_or_404(EmployeeSchedule, pk=pk)
    es.delete()
    messages.success(request, 'Employee schedule deleted.')
    return redirect('employee_schedule_page')



def admin_add_organization(request):
    search_query = request.GET.get('search', '')

    # Filtering by code, organization_eng or organization_type name
    organizations = Organization.objects.select_related(
    'organization_type_id', 'location_id', 'parent_id').filter(
        Q(code__icontains=search_query) |
        Q(organization_eng__icontains=search_query) |
        Q(organization_type_id__organization_type_eng__icontains=search_query)
        ).order_by('-last_updated_date')

    paginator = Paginator(organizations, 10)
    page = request.GET.get('page')
    organizations_page = paginator.get_page(page)

    org_types = OrganizationType.objects.all()
    locations = Location.objects.all()

    context = {
        'organizations': organizations_page,
        'org_types': org_types,
        'locations': locations
    }
    return render(request, 'admin_add_organization.html', context)


from django.db import IntegrityError

def add_organization(request):
    if request.method == 'POST':
        organization_type_id = request.POST.get('organization_type')
        code = request.POST.get('code')
        organization_eng = request.POST.get('organization_eng')
        parent_id = request.POST.get('parent_id') or None
        location_id = request.POST.get('location_id') or None

        created_id = request.session.get('user_id')
        current_time = now()

        organization_type = OrganizationType.objects.get(pk=organization_type_id)
        location = Location.objects.get(pk=location_id) if location_id else None
        parent = Organization.objects.get(pk=parent_id) if parent_id else None

        # Check if code already exists
        if Organization.objects.filter(code__iexact=code).exists():
            messages.error(request, f"Organization code '{code}' already exists.")
            return redirect('admin_add_organization')

        try:
            Organization.objects.create(
                organization_type_id=organization_type,
                code=code,
                organization_eng=organization_eng,
                parent_id=parent,
                location_id=location,
                created_id=created_id,
                created_date=current_time,
                last_updated_id=created_id,
                last_updated_date=current_time
            )
            messages.success(request, "Organization added successfully.")
        except IntegrityError:
            messages.error(request, "Organization code must be unique.")
        
    return redirect('admin_add_organization')



def update_organization(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)

    if request.method == 'POST':
        org.organization_type_id = OrganizationType.objects.get(pk=request.POST.get('organization_type'))
        org.code = request.POST.get('code')
        org.organization_eng = request.POST.get('organization_eng')

        parent_id = request.POST.get('parent_id') or None
        org.parent_id = Organization.objects.get(pk=parent_id) if parent_id else None

        location_id = request.POST.get('location_id') or None
        org.location_id = Location.objects.get(pk=location_id) if location_id else None

        org.last_updated_id = request.session.get('user_id')
        org.last_updated_date = now()
        org.save()

        messages.success(request, "Organization updated successfully.")
    
    return redirect('admin_add_organization')

def admin_add_ccompany(request):
    search_query = request.GET.get('search', '')

    companies = ContractorCompany.objects.filter(
        Q(code__icontains=search_query) |
        Q(contract_company_eng__icontains=search_query)
    ).order_by('-last_updated_date')

    paginator = Paginator(companies, 10)
    page = request.GET.get('page')
    companies_page = paginator.get_page(page)

    return render(request, 'admin_add_ccompany.html', {
        'companies': companies_page,
        'search_query': search_query
    })

def add_ccompany(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        name = request.POST.get('contract_company_eng', '').strip()
        image = request.FILES.get('image')
        created_id = request.session.get('user_id')
        now_time = now()

        if not code or not name:
            messages.error(request, "Code and Company Name are required.")
            return redirect('admin_add_ccompany')

        if ContractorCompany.objects.filter(code=code).exists():
            messages.error(request, f"Code '{code}' already exists.")
            return redirect('admin_add_ccompany')

        ContractorCompany.objects.create(
            code=code,
            contract_company_eng=name,
            contract_company_arb=name,
            image=image,
            created_id=created_id,
            created_date=now_time,
            last_updated_id=created_id,
            last_updated_date=now_time
        )
        messages.success(request, "Contractor Company added.")
    return redirect('admin_add_ccompany')

def update_ccompany(request, company_id):
    company = get_object_or_404(ContractorCompany, pk=company_id)

    if request.method == 'POST':
        company.code = request.POST.get('code')
        company.contract_company_eng = request.POST.get('contract_company_eng')
        image = request.FILES.get('image')
        if image:
            company.image = image

        company.last_updated_id = request.session.get('user_id')
        company.last_updated_date = now()
        company.save()

        messages.success(request, "Contractor Company updated.")
    return redirect('admin_add_ccompany')

def build_org_tree(parent=None):
    orgs = Organization.objects.filter(parent_id=parent).order_by('organization_eng')
    tree = []
    for org in orgs:
        children = build_org_tree(org)
        employees = EmployeeMaster.objects.filter(organization_id=org).order_by('firstname_eng')
        tree.append({
            'org': org,
            'employees': employees,
            'children': children
        })
    return tree

@custom_login_required
def org_hierarchy_view(request):
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass
    user = EmployeeMaster.objects.get(employee_id=employee_id)
    tree = build_org_tree(None)
    return render(request, 'organization_structure.html', {
        'org_tree': tree,
        'user_org_id': user.organization_id.organization_id if user.organization_id else None,
        'user_name': f"{user.firstname_eng} {user.lastname_eng}",
        'user':user,
        'manage_employee_access': access,
        'manage_designation_access': manage_designation_access,
    })


logger = logging.getLogger(__name__)
@custom_login_required
def privilege_management(request):
    roles = SecRole.objects.all()
    submodules = SecSubModule.objects.select_related('module_id').order_by('module_id__module_name')
    users = SecUser.objects.select_related('employee_id')
    orgs = Organization.objects.all()

    return render(request, 'admin_privilege_management.html', {
        'roles': roles,
        'submodules': submodules,
        'users': users,
        'orgs': orgs,
    })


@custom_login_required
def privilege_management(request):
    roles = SecRole.objects.all()
    modules = SecModule.objects.prefetch_related('secsubmodule_set').all()
    users = SecUser.objects.select_related('employee_id').all()
    context = {
        'roles': roles,
        'modules': modules,
        'users': users,
    }
    return render(request, 'admin_privilege_management.html', context)

@custom_login_required
@require_POST
def create_role(request):
    data = json.loads(request.body)
    name = data.get('role_name')
    if not name:
        return JsonResponse({'status':'error','message':'Name required'}, status=400)
    role, _ = SecRole.objects.get_or_create(
        role_name=name, defaults={'editable_flag': True, 'last_updated_id': request.session.get('user_id')}
    )
    return JsonResponse({'status':'success','role_id': role.role_id, 'role_name': role.role_name})

@custom_login_required
def get_role_privileges(request, role_id):
    modules = []
    privsmap = {p.sub_module_id_id: p for p in SecRolePrivilege.objects.filter(role_id=role_id)}
    for m in SecModule.objects.all():
        subs=[]
        for s in SecSubModule.objects.filter(module_id=m):
            p = privsmap.get(s.sub_module_id)
            subs.append({
                'sub_id': s.sub_module_id,
                'sub_name': s.sub_module_name,
                'access': p.access_flag if p else False,
                'view': p.view_flag if p else False,
                'create': p.create_flag if p else False,
                'edit': p.edit_flag if p else False,
                'delete': p.delete_flag if p else False,
                'scope': p.scope if p else 'ALL',
            })
        modules.append({'mod_id': m.module_id, 'mod_name': m.module_name, 'subs': subs})
    return JsonResponse({'modules': modules})

@custom_login_required
@require_POST
def save_privileges(request, role_id):
    data = json.loads(request.body)
    items = data.get('privileges', [])
    user_emp_id = request.session.get('user_id')
    now = datetime.now()
    SecRolePrivilege.objects.filter(role_id=role_id).delete()
    for i in items:
        SecRolePrivilege.objects.create(
            role_id_id=role_id,
            sub_module_id_id=i['sub_id'],
            access_flag=i['access'], view_flag=i.get('view', False),
            create_flag=i.get('create', False), edit_flag=i.get('edit', False),
            delete_flag=i.get('delete', False), scope=i['scope'],
            last_updated_id=user_emp_id, last_updated_time=now
        )
    return JsonResponse({'status':'success'})

@custom_login_required
def get_role_users(request, role_id):
    arr=[]
    for ru in SecUserRole.objects.filter(role_id=role_id).select_related('user_id__employee_id'):
        emp = ru.user_id.employee_id
        arr.append({
    'user_id': ru.user_id.user_id,
    'emp_no': emp.emp_no,
    'firstname_eng': emp.firstname_eng,
    'lastname_eng': emp.lastname_eng,
    'photo_url': emp.photo_file_name.url if emp.photo_file_name else ''
})
    return JsonResponse({'users': arr})

@custom_login_required
@require_POST
def add_user_to_role(request, role_id):
    uid = json.loads(request.body).get('user_id')
    if not uid:
        return JsonResponse({'status':'error','message':'User ID missing'}, status=400)
    user_emp_id = request.session.get('user_id')
    SecUserRole.objects.update_or_create(
        user_id_id=uid,
        defaults={'role_id_id': role_id, 'last_updated_id': user_emp_id, 'last_updated_time': datetime.now()}
    )
    return JsonResponse({'status':'assigned'})

@custom_login_required
def search_users_api(request):
    term = request.GET.get('q', '').strip()
    users = SecUser.objects.select_related('employee_id').filter(
        Q(employee_id__firstname_eng__icontains=term) |
        Q(employee_id__lastname_eng__icontains=term) |
        Q(employee_id__emp_no__icontains=term)
    )[:10]

    result = []
    for u in users:
        emp = u.employee_id
        result.append({
            'user_id': u.user_id,
            'emp_no': emp.emp_no,
            'firstname_eng': emp.firstname_eng,
            'lastname_eng': emp.lastname_eng,
            'photo_url': emp.photo_file_name.url if emp.photo_file_name else '',
        })
    
    return JsonResponse(result, safe=False)

@custom_login_required
def get_role_users_with_privileges(request, role_id):
    # Get users in role
    users = SecUserRole.objects.filter(role_id=role_id).select_related('user_id__employee_id')
    # Get role privileges
    privs = SecRolePrivilege.objects.filter(role_id=role_id)
    
    # Create dict of sub_module_id -> privileges for easy lookup
    priv_map = {}
    for p in privs:
        priv_map[p.sub_module_id_id] = {
            'access': p.access_flag,
            'view': p.view_flag,
            'create': p.create_flag,
            'edit': p.edit_flag,
            'delete': p.delete_flag,
        }

    user_list = []
    for ur in users:
        emp = ur.user_id.employee_id
        # Summarize privileges per user: 
        # For simplicity, combine all privileges in role to one 'summary' (e.g. any access = yes)
        combined_privs = {
            'access': any(p['access'] for p in priv_map.values()),
            'view': any(p['view'] for p in priv_map.values()),
            'create': any(p['create'] for p in priv_map.values()),
            'edit': any(p['edit'] for p in priv_map.values()),
            'delete': any(p['delete'] for p in priv_map.values()),
        }
        user_list.append({
            'user_id': ur.user_id.user_id,
            'emp_no': emp.emp_no,
            'firstname_eng': emp.firstname_eng,
            'lastname_eng': emp.lastname_eng,
            'photo_url': emp.photo_file_name.url if emp.photo_file_name else '',
            'privileges': combined_privs,
        })

    return JsonResponse({'users': user_list})



def attendance_report(request):
    org_id = request.GET.get('organization')
    manager_id = request.GET.get('manager')
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')

    filters = Q()

    if from_date_str and to_date_str:
        try:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
            filters &= Q(Ddate__range=(from_date, to_date))
        except ValueError:
            pass

    if org_id:
        filters &= Q(employee_id__organization_id=org_id)

    if manager_id:
        filters &= Q(employee_id__manager_id=manager_id)

    # Filter attendance records
    data = DailyEmployeeAttendanceDetails.objects.filter(filters)\
        .select_related('employee_id', 'employee_id__organization_id', 'employee_id__designation_id')\
        .order_by('employee_id', 'Ddate')

    # Generate summary
    report_summary = {}
    for item in data:
        month = item.Ddate.strftime("%Y-%m")
        month_label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        key = (item.employee_id.employee_id, month_label)
        if key not in report_summary:
            report_summary[key] = {
                "employee": item.employee_id,
                "month": month,
                "month_label": month_label,
            }

    # Filter orgs and managers based on current dataset
    attendance_emp_ids = data.values_list('employee_id__employee_id', flat=True).distinct()

    organizations = Organization.objects.filter(
    organization_id__in=EmployeeMaster.objects.filter(employee_id__in=attendance_emp_ids)
    .values_list('organization_id', flat=True)
    )

    managers = EmployeeMaster.objects.filter(
        employee_id__in=EmployeeMaster.objects.filter(employee_id__in=attendance_emp_ids)
        .values_list('manager_id', flat=True)
    ).distinct()

    context = {
        "organizations": organizations,
        "managers": managers,
        "report_data": report_summary.values()
    }

    return render(request, "admin_reports.html", context)



def generate_pdf(request, emp_id, month):

    from calendar import monthrange
    from datetime import datetime

    month_date = datetime.strptime(month, "%Y-%m")
    start_date = month_date.replace(day=1)
    end_date = start_date.replace(day=monthrange(start_date.year, start_date.month)[1])

    records = DailyEmployeeAttendanceDetails.objects.filter(
    employee_id=emp_id,
    Ddate__range=(start_date, end_date)
    ).select_related('employee_id__organization_id', 'employee_id__designation_id').order_by('Ddate')

    response = generate_attendance_pdf(records)
    return response


def admin_add_holidays(request):
    search_query = request.GET.get('search', '')
    holidays = Holiday.objects.all()

    if search_query:
        holidays = holidays.filter(holiday_eng__icontains=search_query)

    paginator = Paginator(holidays.order_by('-from_date'), 10)
    page = request.GET.get('page')
    holidays_page = paginator.get_page(page)

    return render(request, 'admin_add_holidays.html', {
        'holidays': holidays_page,
        'search_query': search_query
    })

def add_holiday(request):
    if request.method == 'POST':
        Holiday.objects.create(
            holiday_eng=request.POST['holiday_eng'],
            holiday_arb=request.POST['holiday_eng'],
            from_date=request.POST['from_date'],
            to_date=request.POST['to_date'],
            remarks=request.POST.get('remarks', ''),
            created_id=request.session['user_id'],
            last_updated_id=request.session['user_id'],
            created_date=now(),
            last_updated_time=now(),
            recurring_flag=0 
        )
        messages.success(request, "Holiday added successfully.")
    return redirect('admin_add_holidays')

def update_holiday(request, holiday_id):
    holiday = get_object_or_404(Holiday, pk=holiday_id)

    if request.method == 'POST':
        holiday.holiday_eng = request.POST['holiday_eng']
        holiday.from_date = request.POST['from_date']
        holiday.to_date = request.POST['to_date']
        holiday.remarks = request.POST.get('remarks', '')
        holiday.last_updated_id = request.session['user_id']
        holiday.last_updated_time = now()
        holiday.save()
        messages.success(request, "Holiday updated successfully.")
    return redirect('admin_add_holidays')

#--------EMPLOYEE-------------------------------------------
def resolve_schedule(employee, punch_date):
    weekday = day_name[punch_date.weekday()].lower()

    emp_sched = EmployeeSchedule.objects.filter(
        employee_id=employee,
        from_date__lte=punch_date,
        to_date__gte=punch_date
    ).first()
    if emp_sched:
        return getattr(emp_sched, f"{weekday}_schedule", None)

    group_id = getattr(employee, 'employee_group', None)
    if group_id:
        group_sched = GroupSchedule.objects.filter(
            employee_group_id=group_id,
            from_date__lte=punch_date,
            to_date__gte=punch_date
        ).first()
        if group_sched:
            return getattr(group_sched, f"{weekday}_schedule", None)

    org_sched = OrganizationSchedule.objects.filter(
        organization_id=employee.organization_id,
        from_date__lte=punch_date,
        to_date__gte=punch_date
    ).first()
    if org_sched:
        return getattr(org_sched, f"{weekday}_schedule", None)

    return None

def employee_dashboard(request):
    today = date.today()
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass

    punches_today = EmployeeEventTransaction.objects.filter(
        employee_id=manager,
        transaction_time__date=today
    ).order_by('transaction_time')
    
    worked_duration = None
    if punches_today.count() > 1:
            time_in = punches_today.first().transaction_time
            time_out = punches_today.last().transaction_time
            if time_out > time_in:
                duration = time_out - time_in
                total_minutes = duration.total_seconds() // 60
                hours = int(total_minutes // 60)
                minutes = int(total_minutes % 60)
                worked_duration = f"{hours}h {minutes}m"

    punches_month = EmployeeEventTransaction.objects.filter(
        employee_id=manager,
        transaction_time__month=today.month,
        transaction_time__year=today.year
    ).order_by('transaction_time')

    subordinates = []
    punch_in_count = 0
    punch_out_count = 0
    if manager.manager_flag == 'Y':
        subs = EmployeeMaster.objects.filter(manager_id=manager.employee_id)
        for emp in subs:
            sched = resolve_schedule(emp, today)
            is_holiday = False
            holiday_name = None
            holiday = Holiday.objects.filter(from_date__date__lte=today, to_date__date__gte=today).first()
            if holiday:
                is_holiday = True
                holiday_name = holiday.holiday_eng
                
            p_today = EmployeeEventTransaction.objects.filter(
                employee_id=emp,
                transaction_time__date=today
            ).order_by('transaction_time')
            in_p = p_today.first()
            out_p = p_today.last() if p_today.count() > 1 else None
            perm = EmployeeShortPermission.objects.filter(
                employee_id=emp,
                approve_reject_flag=1,
                from_time__gte=datetime.combine(today, time.min),
                from_time__lte=datetime.combine(today, time.max),
            ).first()
            leave_today = EmployeeLeave.objects.filter(
                employee_id=emp,
                leave_status='Approved',
                from_date__lte=today,
                to_date__gte=today
            ).exists()
            late_in = False
            early_out = False
            illegal_punch = False
            punched_out_late = False
            is_missing = in_p is None or out_p is None
            if sched and in_p:
                sched_in = datetime.combine(today, sched.start_time)
                actual_in = in_p.transaction_time
                if actual_in > sched_in + timedelta(minutes=sched.grace_period or 0):
                    if not perm or not (perm.from_time <= actual_in <= perm.to_time):
                        late_in = True
            if sched and out_p:
                sched_out = datetime.combine(today, sched.end_time)
                actual_out = out_p.transaction_time
                if actual_out < sched_out - timedelta(minutes=1):
                    if not perm or not (perm.from_time <= actual_out <= perm.to_time):
                        early_out = True
                if actual_out > sched_out + timedelta(minutes=60):
                    punched_out_late = True
            if leave_today and (in_p or out_p):
                illegal_punch = True
            subordinates.append({
                'emp': emp,
                'punch_in': in_p,
                'punch_out': out_p,
                'perm': perm,
                'on_leave': leave_today,
                'schedule': sched,
                'late_in': late_in,
                'early_out': early_out,
                'punched_out_late': punched_out_late,
                'illegal_punch': illegal_punch,
                'is_missing': is_missing,
                'is_holiday': is_holiday,
                'holiday_name': holiday_name,
                'no_schedule': sched is None,
            })
        punch_in_count = sum(1 for row in subordinates if row['punch_in'])
        punch_out_count = sum(1 for row in subordinates if row['punch_out'])

    month_rows = []
    by_date = {}
    for punch in punches_month:
        punch_date = punch.transaction_time.date()
        by_date.setdefault(punch_date, {'in': None, 'out': None})
        if by_date[punch_date]['in'] is None:
            by_date[punch_date]['in'] = punch
        by_date[punch_date]['out'] = punch

    for punch_date in sorted(by_date):
        in_p = by_date[punch_date]['in']
        out_p = by_date[punch_date]['out']
        sched = resolve_schedule(manager, punch_date)
        perm = EmployeeShortPermission.objects.filter(
            employee_id=manager,
            approve_reject_flag=1,
            from_time__gte=datetime.combine(today, time.min),
            from_time__lte=datetime.combine(today, time.max)
        ).first()
        leave_today = EmployeeLeave.objects.filter(
            employee_id=manager,
            leave_status='Approved',
            from_date__lte=punch_date,
            to_date__gte=punch_date
        ).exists()
        late_in = False
        early_out = False
        punched_out_late = False
        illegal_punch = False
        is_missing = in_p is None or out_p is None
        if sched and in_p:
            sched_in = datetime.combine(punch_date, sched.start_time)
            actual_in = in_p.transaction_time
            if actual_in > sched_in + timedelta(minutes=sched.grace_period or 0):
                if not perm or not (perm.from_time <= actual_in <= perm.to_time):
                    late_in = True
        if sched and out_p:
            sched_out = datetime.combine(punch_date, sched.end_time)
            actual_out = out_p.transaction_time
            if actual_out < sched_out - timedelta(minutes=1):
                if not perm or not (perm.from_time <= actual_out <= perm.to_time):
                    early_out = True
            if actual_out > sched_out + timedelta(minutes=60):
                punched_out_late = True
        if leave_today and (in_p or out_p):
            illegal_punch = True
        month_rows.append({
            'date': punch_date,
            'in': in_p,
            'out': out_p,
            'schedule': sched,
            'perm': perm,
            'on_leave': leave_today,
            'is_missing': is_missing,
            'late_in': late_in,
            'early_out': early_out,
            'punched_out_late': punched_out_late,
            'illegal_punch': illegal_punch,
        })

    return render(request, 'employee_dashboard.html', {
        'user': manager,
        'manage_employee_access': access,
        'manage_designation_access': manage_designation_access,
        'is_manager': manager.manager_flag == 'Y',
        'today_punches': punches_today,
        'subordinates': subordinates,
        'month_rows': month_rows,
        'punch_in_count': punch_in_count,
        'punch_out_count': punch_out_count,
        'worked_duration': worked_duration,
    })
    
    
@custom_login_required
def employee_details(request):
    employee = get_object_or_404(EmployeeMaster, pk=request.session['employee_id'])
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass
    
    return render(request, 'employee_details.html', {'employee': employee,
                                                     'manage_employee_access': access,
                                                     'manage_designation_access': manage_designation_access,})

@custom_login_required
def employee_update(request, emp_id):
    employee = get_object_or_404(EmployeeMaster, pk=emp_id)
    me = get_object_or_404(EmployeeMaster, pk=request.session['employee_id'])

    if request.method == 'POST':
        allowed_fields = ['firstname_eng', 'lastname_eng', 'mobile', 'email', 'gender']
        data = request.POST
        changed = False

        for field in allowed_fields:
            new = data.get(field)
            if new is not None:
                if getattr(employee, field) != new:
                    setattr(employee, field, new)
                    changed = True

        # Managers can also:
        if me.manager_flag == 'Y':
            mgr_fields = [
                'organization_id', 'grade_id', 'designation_id',
                'employee_type_id', 'passport_issue_country_id',
                'work_location_id', 'contract_company_id'
            ]
            for f in mgr_fields:
                v = data.get(f)
                if v:
                    setattr(employee, f, get_object_or_404(
                        EmployeeMaster._meta.get_field(f).remote_field.model, pk=v)
                    )
                    changed = True

        if changed:
            employee.last_updated_id = me.employee_id
            employee.last_updated_date = timezone.now()
            employee.save()
            messages.info(request, 'Details updated successfully.')

        return redirect('employee_details')

    messages.error(request, 'Invalid method.')
    return redirect('employee_details')

@custom_login_required
def employee_permission_type(request):
    emp_id = request.session.get('employee_id')
    employee = EmployeeMaster.objects.get(employee_id=emp_id)
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)
    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass



    search = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '').strip()

    permissions = PermissionType.objects.all()

    # Non-managers see only active
    if employee.active_flag == 1 and employee.manager_flag == 'N':
        permissions = permissions.filter(Status_Flag=True)

    # Search logic
    if search:
        permissions = permissions.filter(
            Q(code__icontains=search) |
            Q(permdescription_eng__icontains=search) |
            Q(specific_gender__icontains=search)
        )

    # Sorting logic
    if sort == 'code':
        permissions = permissions.order_by('code')
    elif sort == 'description':
        permissions = permissions.order_by('permdescription_eng')
    elif sort == 'gender':
        permissions = permissions.order_by('specific_gender')
    elif sort == 'status':
        permissions = permissions.order_by('-Status_Flag')  # Active first

    context = {
        'permissions': permissions,
        'is_manager': employee.manager_flag == 'Y',
        'q': search,
        'sort': sort,
    }
    return render(request, 'employee_permission_type.html', context)

@custom_login_required
def edit_permission_type(request, perm_id):
    employee_id = request.session.get('employee_id')
    employee = get_object_or_404(EmployeeMaster, employee_id=employee_id)

    if not (employee.active_flag == 1 and employee.manager_flag == 'Y'):
        return HttpResponseForbidden('You are not authorized to edit this permission type.')

    permission = get_object_or_404(PermissionType, permission_type_id=perm_id)

    if request.method == 'POST':
        permission.code = request.POST.get('code')
        permission.permdescription_eng = request.POST.get('permdescription_eng')
        permission.permdescription_arb = permission.permdescription_eng
        permission.max_perm_per_day = request.POST.get('max_perm_per_day') or None
        permission.max_minutes_per_day = request.POST.get('max_minutes_per_day') or None
        permission.max_perm_per_month = request.POST.get('max_perm_per_month') or None
        permission.max_minutes_per_month = request.POST.get('max_minutes_per_month') or None
        
        gender = request.POST.get('specific_gender')
        permission.specific_gender = gender if gender in ['M', 'F'] else None

        permission.Status_Flag = request.POST.get('Status_Flag') == 'on'
        permission.last_updated_id = employee_id
        permission.last_updated_time = timezone.now()

        permission.save()
        messages.success(request, "Permission Type updated successfully.")
        return redirect('employee_permission_type')

    return render(request, 'edit_permission_type.html', {
        'permission': permission
    })




@custom_login_required
def employee_apply_leave(request):
    employee = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass
    
    leaves = EmployeeLeave.objects.filter(employee_id=employee).order_by('-from_date')
    leave_types = LeaveType.objects.filter(status_Flag=True)
    return render(request, 'employee_apply_leave.html', {
        'leaves': leaves,
        'leave_types': leave_types,
        'manage_employee_access': access,
        'manage_designation_access': manage_designation_access,
        'user': employee,
        'MEDIA_URL': settings.MEDIA_URL
    })

@custom_login_required
def add_leave(request):
    if request.method == 'POST':
        employee = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])
        leave_type = LeaveType.objects.get(leave_type_id=request.POST['leave_type_id'])

        # Gender validation
        if leave_type.specific_gender and leave_type.specific_gender != employee.gender:
            messages.error(request, "This leave type is restricted to your gender.")
            return redirect('employee_apply_leave')

        # Comment mandatory validation
        remarks = request.POST.get('employee_remarks', '')
        if leave_type.is_comment_mandatory and not remarks.strip():
            messages.error(request, "Remarks are mandatory for this leave.")
            return redirect('employee_apply_leave')

        # Extract dates and number of days
        from_date_str = request.POST['from_date']
        to_date_str = request.POST['to_date']
        number_of_leaves = int(request.POST['number_of_leaves'])

        from_date = datetime.strptime(from_date_str, '%Y-%m-%d')
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d')
        today = timezone.now().date()

        # --- Overlapping Leave Validation ---
        overlapping_leaves = EmployeeLeave.objects.filter(
            employee_id=employee,
            leave_status__in=['Pending', 'Approved'],
            from_date__lte=to_date,
            to_date__gte=from_date
        )
        if overlapping_leaves.exists():
            messages.error(request, "You already have a leave during or overlapping with the selected period.")
            return redirect('employee_apply_leave')

        # --- Annual Limit Validation ---
        current_year = today.year
        taken_leaves = EmployeeLeave.objects.filter(
            employee_id=employee,
            leave_type_id=leave_type,
            from_date__year=current_year,
            leave_status__in=['Pending', 'Approved']
        ).aggregate(total=Sum('number_of_leaves'))['total'] or 0

        # Determine limit from grade and leave type
        grade = employee.grade_id
        max_by_type = leave_type.total_entitled_days or 0
        max_by_grade = 0
        if grade:
            if leave_type.Is_AL_flag:
                max_by_grade = grade.number_of_AL
            elif leave_type.Is_SL_flag:
                max_by_grade = grade.number_of_SL

        allowed_limit = max(max_by_grade, max_by_type)
        if (taken_leaves + number_of_leaves) > allowed_limit:
            messages.error(
                request,
                f"You have already taken {taken_leaves} day(s) of this leave in {current_year}. "
                f"Maximum allowed is {allowed_limit}."
            )
            return redirect('employee_apply_leave')

        # --- Upload file if provided ---
        file_path = None
        if 'leave_doc_filename_path' in request.FILES:
            file = request.FILES['leave_doc_filename_path']
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            filename = fs.save(f'leave_docs/{file.name}', file)
            file_path = f'leave_docs/{file.name}'

        # --- Generate leave reference ---
        today_str = today.strftime('%d%m%Y')
        count = EmployeeLeave.objects.filter(
            employee_id=employee,
            created_date__date=today
        ).count() + 1
        ref_no = f"{employee.emp_no}{today_str}{count}"

        # --- Create the leave record ---
        EmployeeLeave.objects.create(
            employee_id=employee,
            leave_type_id=leave_type,
            from_date=from_date,
            to_date=to_date,
            number_of_leaves=number_of_leaves,
            employee_remarks=remarks,
            leave_doc_filename_path=file_path,
            leave_UniqueRefNo=ref_no,
            leave_status='Pending',
            created_id=employee.employee_id,
            created_date=timezone.now(),
            last_updated_id=employee.employee_id,
            last_updated_date=timezone.now()
        )

        messages.success(request, "Leave applied successfully.")
        return redirect('employee_apply_leave')

@custom_login_required
def update_leave(request, pk):
    leave = get_object_or_404(EmployeeLeave, pk=pk)
    if leave.leave_status in ['Approved', 'Rejected']:
        messages.error(request, "Approved or Rejected leaves cannot be modified.")
        return redirect('employee_apply_leave')

    if request.method == 'POST':
        leave.leave_type_id_id = request.POST['leave_type_id']
        leave.from_date = request.POST['from_date']
        leave.to_date = request.POST['to_date']
        leave.number_of_leaves = request.POST['number_of_leaves']
        leave.employee_remarks = request.POST['employee_remarks']
        if 'leave_doc_filename_path' in request.FILES:
            file = request.FILES['leave_doc_filename_path']
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            filename = fs.save(f'leave_docs/{file.name}', file)
            leave.leave_doc_filename_path = f'leave_docs/{file.name}'
        leave.last_updated_date = timezone.now()
        leave.save()
        messages.success(request, "Leave updated successfully.")
    return redirect('employee_apply_leave')

@custom_login_required
def delete_leave(request, pk):
    leave = get_object_or_404(EmployeeLeave, pk=pk)
    if leave.leave_status not in ['Approved', 'Rejected']:
        leave.delete()
        messages.success(request, "Leave deleted.")
    else:
        messages.error(request, "Approved/Rejected leave can't be deleted.")
    return redirect('employee_apply_leave')

@custom_login_required
def managers_approve_leave(request):
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass
    
    leaves = EmployeeLeave.objects.filter(employee_id__manager_id=manager).order_by('-created_date')

    # Flag late leaves
    for leave in leaves:
        leave.is_late_applied = False

        apply_days = leave.leave_type_id.apply_prior_to_days
        if leave.created_date and leave.from_date and apply_days is not None:
            try:
                required_days = int(apply_days)
                latest_allowed_date = leave.from_date.date() - timedelta(days=required_days)
                if leave.created_date.date() > latest_allowed_date:
                    leave.is_late_applied = True
            except:
                pass  # Ignore conversion errors

    return render(request, 'managers_approve_leave.html', {
        'leaves': leaves,
        'user': manager,
        'manage_employee_access': access,
        'manage_designation_access': manage_designation_access
    })

@custom_login_required
def approve_reject_leave(request, pk):
    if request.method == 'POST':
        leave = get_object_or_404(EmployeeLeave, pk=pk)
        manager = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])
        action = request.POST.get('action')

        if leave.leave_status in ['Approved', 'Rejected']:
            messages.warning(request, "Leave already processed.")
            return redirect('managers_approve_leave')

        if action == 'approve':
            leave.leave_status = 'Approved'
        elif action == 'reject':
            leave.leave_status = 'Rejected'

        leave.approver_id = manager
        leave.approved_date = timezone.now()
        leave.last_updated_id = manager.employee_id
        leave.last_updated_date = timezone.now()
        leave.save()
        messages.success(request, f"Leave {action}d successfully.")
    return redirect('managers_approve_leave')

@custom_login_required
def employee_apply_permission(request):
    employee = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass
    
    permissions = EmployeeShortPermission.objects.filter(employee_id=employee).order_by('-from_date')
    permission_types = PermissionType.objects.filter(Status_Flag=True)
    return render(request, 'employee_apply_permission.html', {
        'permissions': permissions,
        'permission_types': permission_types,
        'user': employee,
        'manage_employee_access': access,
        'manage_designation_access': manage_designation_access
    })

@custom_login_required
def add_permission(request):
    if request.method == 'POST':
        employee = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])
        permission_type = get_object_or_404(PermissionType, pk=request.POST['permission_type_id'])

        permission = EmployeeShortPermission.objects.create(
            permission_type_id=permission_type,
            employee_id=employee,
            from_date=request.POST['from_date'],
            to_date=request.POST['to_date'],
            from_time=request.POST.get('from_time'),
            to_time=request.POST.get('to_time'),
            remarks=request.POST.get('remarks', ''),
            approve_reject_flag=0,  # Pending
            created_id=employee.employee_id,
            created_date=timezone.now(),
            last_updated_id=employee.employee_id,
            last_updated_date=timezone.now()
        )
        messages.success(request, "Permission applied successfully.")
        return redirect('employee_apply_permission')
    
@custom_login_required
def update_permission(request, pk):
    permission = get_object_or_404(EmployeeShortPermission, pk=pk)
    if permission.approve_reject_flag != 0:
        messages.error(request, "Approved/Rejected permissions cannot be modified.")
        return redirect('employee_apply_permission')

    if request.method == 'POST':
        permission.permission_type_id_id = request.POST['permission_type_id']
        permission.from_date = request.POST['from_date']
        permission.to_date = request.POST['to_date']
        permission.from_time = request.POST.get('from_time')
        permission.to_time = request.POST.get('to_time')
        permission.remarks = request.POST.get('remarks', '')
        permission.last_updated_id = request.session['employee_id']
        permission.last_updated_date = timezone.now()
        permission.save()
        messages.success(request, "Permission updated successfully.")
    return redirect('employee_apply_permission')

@custom_login_required
def delete_permission(request, pk):
    permission = get_object_or_404(EmployeeShortPermission, pk=pk)
    if permission.approve_reject_flag == 0:
        permission.delete()
        messages.success(request, "Permission deleted.")
    else:
        messages.error(request, "Cannot delete approved/rejected permission.")
    return redirect('employee_apply_permission')

@custom_login_required
def manager_approve_permission(request):
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass
    
    permissions = EmployeeShortPermission.objects.filter(employee_id__manager_id=manager).order_by('-created_date')
    return render(request, 'managers_approve_permission.html', {'permissions': permissions, 'user': manager,
                                                                'manage_employee_access': access,
        'manage_designation_access': manage_designation_access})

@custom_login_required
def approve_reject_permission(request, pk):
    permission = get_object_or_404(EmployeeShortPermission, pk=pk)
    if permission.approve_reject_flag in [1, 2]:
        messages.warning(request, "Permission request already processed.")
        return redirect('manager_approve_permission')

    if request.method == 'POST':
        action = request.POST.get('action')
        manager = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])

        if action == 'approve':
            permission.approve_reject_flag = 1
        elif action == 'reject':
            permission.approve_reject_flag = 2

        permission.approver_id = manager
        permission.approved_date = timezone.now()
        permission.last_updated_id = manager.employee_id
        permission.last_updated_date = timezone.now()
        permission.save()

        messages.success(request, f"Permission {action}d successfully.")
    return redirect('manager_approve_permission')

def employee_view_leave_types(request):
    employee_id = request.session.get('employee_id')
    manager = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    user = get_object_or_404(SecUser, employee_id=manager)

    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)

    access = None
    try:
        employees_module = SecModule.objects.get(module_name='Employees')
        manage_employee_sub = SecSubModule.objects.get(module_id=employees_module.module_id, sub_module_name='Manage Employee')
        access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_employee_sub.sub_module_id).first()
    except (SecModule.DoesNotExist, SecSubModule.DoesNotExist):
        pass

    manage_designation_access = None
    try:
        designation_module = SecModule.objects.get(module_name='General')
        manage_designation_sub = SecSubModule.objects.get(module_id=designation_module.module_id, sub_module_name='Designations')
        manage_designation_access = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=manage_designation_sub.sub_module_id).first()
    except SecSubModule.DoesNotExist:
        pass
    search_query = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort', 'code')  

    leave_types = LeaveType.objects.all()

    if search_query:
        leave_types = leave_types.filter(
            Q(code__icontains=search_query) |
            Q(leaveDesc_eng__icontains=search_query) |
            Q(specific_gender__icontains=search_query)
        )

    # Valid sort fields (fallback to 'code' if invalid)
    valid_sort_fields = ['code', 'leaveDesc_eng', 'specific_gender']
    if sort_by not in valid_sort_fields:
        sort_by = 'code'

    leave_types = leave_types.order_by(sort_by)

    context = {
        'leave_types': leave_types,
        'search_query': search_query,
        'sort_by': sort_by,
        'manage_employee_access': access,
        'manage_designation_access': manage_designation_access,
    }
    return render(request, 'employee_view_leave_types.html', context)



def get_all_child_org_ids(parent_id):
    child_ids = []
    for child in Organization.objects.filter(parent_id=parent_id):
        child_ids.append(child.organization_id)
        child_ids.extend(get_all_child_org_ids(child.organization_id))
    return child_ids

def get_user_scope_permissions(user, module_name, sub_module_name):
    role_ids = SecUserRole.objects.filter(user_id=user).values_list('role_id', flat=True)
    print(f"[DEBUG] Role IDs for user {user.login}: {list(role_ids)}")

    module = SecModule.objects.filter(module_name=module_name).first()
    if not module:
        print(f"[ERROR] Module '{module_name}' not found.")
        return None

    sub_module = SecSubModule.objects.filter(module_id=module.module_id, sub_module_name=sub_module_name).first()
    if not sub_module:
        print(f"[ERROR] Sub Module '{sub_module_name}' not found.")
        return None

    privilege = SecRolePrivilege.objects.filter(role_id__in=role_ids, sub_module_id=sub_module.sub_module_id).first()
    if not privilege:
        print(f"[ERROR] No privileges found for submodule '{sub_module_name}'")

    return privilege

@custom_login_required
def manage_employees(request):
    print("\n=== [START] EMPLOYEE MANAGE OTHERS ===")
    user_id = request.session.get('user_id')
    employee_id = request.session.get('employee_id')

    if not user_id or not employee_id:
        return redirect('login')

    user = get_object_or_404(SecUser, user_id=user_id)
    emp = get_object_or_404(EmployeeMaster, employee_id=employee_id)

    privilege = get_user_scope_permissions(user, 'Employees', 'Manage Employee')
    if not privilege or not privilege.view_flag:
        return render(request, 'employee_manage_others.html', {'error': 'No access rights'})

    scope = (privilege.scope or 'OWN').strip().upper()

    # Get employees based on scope
    if scope == 'OWN':
        employees = EmployeeMaster.objects.filter(employee_id=emp.employee_id)
    elif scope == 'NODE':
        employees = EmployeeMaster.objects.filter(Q(manager_id_id=emp.employee_id) | Q(employee_id=emp.employee_id)).distinct()
    elif scope == 'ALL':
        org_id = emp.organization_id.organization_id if emp.organization_id else None
        org_ids = [org_id] + get_all_child_org_ids(org_id) if org_id else []
        employees = EmployeeMaster.objects.filter(organization_id__in=org_ids)
    else:
        employees = EmployeeMaster.objects.filter(employee_id=emp.employee_id)

    employees = employees.select_related('manager_id')

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    employee_data = []

    for e in employees:
        try:
            punch_data = EmployeeEventTransaction.objects.filter(
                employee_id=e,
                transaction_time__range=(today_start, today_end)
            ).aggregate(
                punch_in=Min('transaction_time'),
                punch_out=Max('transaction_time')
            )

            on_leave = EmployeeLeave.objects.filter(
                employee_id=e,
                approve_reject_flag=1,
                from_date__lte=today_start,
                to_date__gte=today_start
            ).exists()

            on_permission = EmployeeShortPermission.objects.filter(
                employee_id=e,
                approve_reject_flag=1,
                from_date__lte=today_start,
                to_date__gte=today_start
            ).exists()

            status = 'On Leave' if on_leave else 'On Permission' if on_permission else 'Active'

            employee_data.append({
                'employee_id': e.employee_id,
                'emp_no': e.emp_no,
                'first_name': e.firstname_eng,
                'last_name': e.lastname_eng,
                'manager_name': f"{e.manager_id.firstname_eng} {e.manager_id.lastname_eng}" if e.manager_id else '-',
                'punch_in': punch_data['punch_in'].strftime('%H:%M') if punch_data['punch_in'] else '-',
                'punch_out': punch_data['punch_out'].strftime('%H:%M') if punch_data['punch_out'] else '-',
                'status': status,
                'photo': e.photo_file_name.url if e.photo_file_name else None,
                'editable': True,
                'deletable': True,
                'is_blocked': e.active_flag == 0,
            })
        except Exception as ex:
            print(f"[ERROR] Failed to process employee {e.employee_id}: {ex}")

    paginator = Paginator(employee_data, 10)
    page = request.GET.get('page', 1)
    employees_paginated = paginator.get_page(page)

    return render(request, 'employee_manage_others.html', {
        'employees': employees_paginated,
        'page': int(page),
        'page_range': paginator.page_range,
        'edit_flag': privilege.edit_flag,
        'delete_flag': privilege.delete_flag,
        'create_flag': privilege.create_flag,
        'scope': scope,
        'user_emp_id': emp.employee_id,
        'organizations': Organization.objects.all(),
    'designations': Designation.objects.all(),
    'employee_types': EmployeeType.objects.all(),
    'countries': Country.objects.all(),
    'locations': Location.objects.all(),
    'contractor_companies': ContractorCompany.objects.all(),
    'grades': Grade.objects.all(),
    'managers': EmployeeMaster.objects.filter(manager_flag='Y'),
    })

@custom_login_required
def employee_add_employee(request):
    if request.method == 'POST':
        data = request.POST
        try:
            new_emp = EmployeeMaster(
                emp_no=data.get('emp_no'),
                firstname_eng=data.get('firstname_eng'),
                lastname_eng=data.get('lastname_eng'),
                firstname_arb=data.get('firstname_eng'),
                lastname_arb=data.get('lastname_eng'),
                organization_id_id=data.get('organization_id'),
                designation_id_id=data.get('designation_id'),
                employee_type_id_id=data.get('employee_type_id'),
                passport_issue_country_id_id=data.get('passport_issue_country_id'),
                work_location_id_id=data.get('work_location_id'),
                contract_company_id_id=data.get('contract_company_id'),
                grade_id_id=data.get('grade_id'),
                join_date=data.get('join_date') or None,
                active_date=data.get('active_date') or None,
                inactive_date=data.get('inactive_date') or None,
                remarks=data.get('remarks') or '',
                manager_id_id=data.get('manager_id'),
                manager_flag=data.get('manager_flag'),
                open_shift_flag=data.get('open_shift_flag', 0),
                overtime_flag=data.get('overtime_flag', 0),
                active_flag=1 if data.get('active_date') and not data.get('inactive_date') else 0,
                photo_file_name=request.FILES.get('photo_file_name'),
                created_id=request.session['user_id'],
                created_date=timezone.now(),
                last_updated_id=request.session['user_id'],
                last_updated_date=timezone.now()
            )
            new_emp.save()

            SecUser.objects.create(
                login=new_emp.firstname_eng,
                password=new_emp.firstname_eng,
                employee_id=new_emp,
                last_updated_id=request.session['user_id']
            )

            messages.success(request, "Employee added successfully.")
        except Exception as e:
            messages.error(request, f"Error adding employee: {str(e)}")
    return redirect('employee_manage_others')


@custom_login_required
def employee_update_employee(request, employee_id):
    emp = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    if request.method == 'POST':
        try:
            emp.emp_no = request.POST.get('emp_no')
            emp.firstname_eng = request.POST.get('firstname_eng')
            emp.lastname_eng = request.POST.get('lastname_eng')
            emp.firstname_arb = request.POST.get('firstname_eng')
            emp.lastname_arb = request.POST.get('lastname_eng')
            organization_id = request.POST.get('organization_id')
            if organization_id:
                emp.organization_id = get_object_or_404(Organization, organization_id=organization_id)
            passport_issue_country_id = request.POST.get('passport_issue_country')
            
            if passport_issue_country_id:
                emp.passport_issue_country_id = get_object_or_404(Country, country_id=passport_issue_country_id)
            
            designation_id = request.POST.get('designation_id')
            if designation_id:
                emp.designation_id = get_object_or_404(Designation, designation_id=designation_id)
                
            employee_type_id = request.POST.get('employee_type_id')
            if employee_type_id:
                emp.employee_type_id = get_object_or_404(EmployeeType, employee_type_id=employee_type_id)
                
            work_location_id = request.POST.get('work_location_id')
            if work_location_id:
                emp.work_location_id = get_object_or_404(Location, location_id=work_location_id)
            
            contractor_company_id = request.POST.get('contract_company_id')
            if contractor_company_id:
                emp.contract_company_id = get_object_or_404(ContractorCompany, contractor_company_id=contractor_company_id)
            
            grade_id = request.POST.get('grade_id')
            if grade_id:
                emp.grade_id = get_object_or_404(Grade, grade_id=grade_id)
            
            manager_id = request.POST.get('manager_id')
            if manager_id:
                emp.manager_id = get_object_or_404(EmployeeMaster, employee_id=manager_id)
            else:
                emp.manager_id = None

            emp.join_date = request.POST.get('join_date') or None
            emp.active_date = request.POST.get('active_date') or None
            emp.inactive_date = request.POST.get('inactive_date') or None
            emp.remarks = request.POST.get('remarks') or ''
            emp.manager_id_id = request.POST.get('manager_id')
            emp.manager_flag = request.POST.get('manager_flag')
            emp.open_shift_flag = int(request.POST.get('open_shift_flag', 0))
            emp.overtime_flag = int(request.POST.get('overtime_flag', 0))
            emp.active_flag = 1 if emp.active_date and not emp.inactive_date else 0

            if 'photo_file_name' in request.FILES:
                emp.photo_file_name = request.FILES['photo_file_name']

            emp.last_updated_id = request.session['user_id']
            emp.last_updated_date = timezone.now()

            emp.save()
            messages.success(request, f"Employee {emp.emp_no} updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating employee: {str(e)}")
    return redirect('employee_manage_others')


@custom_login_required
def employee_delete_employee(request, employee_id):
    emp = get_object_or_404(EmployeeMaster, employee_id=employee_id)
    emp.active_flag = 0
    emp.inactive_date = date.today()
    emp.last_updated_id = request.session['user_id']
    emp.last_updated_date = timezone.now()
    emp.save()
    messages.warning(request, f"Employee {emp.emp_no} was blocked.")
    return redirect('employee_manage_others')



@custom_login_required
def update_employee_modal(request, emp_id):
    employee = get_object_or_404(EmployeeMaster, pk=emp_id)

    context = {
        'employee': employee,
        'mode': 'update',
        'organizations': Organization.objects.all(),
        'designations': Designation.objects.all(),
        'employee_types': EmployeeType.objects.all(),
        'countries': Country.objects.all(),
        'locations': Location.objects.all(),
        'contractor_companies': ContractorCompany.objects.all(),
        'grades': Grade.objects.all(),
        'managers': EmployeeMaster.objects.all(),
    }

    return render(request, 'partials/employee_form_fields.html', context)

@custom_login_required
def manager_manage_designations(request):
    user_id = request.session.get('user_id')
    employee_id = request.session.get('employee_id')

    if not user_id or not employee_id:
        return redirect('login')

    user = get_object_or_404(SecUser, user_id=user_id)
    employee = get_object_or_404(EmployeeMaster, employee_id=employee_id)

    privilege = get_user_scope_permissions(user, 'General', 'Designations')
    if not privilege or not privilege.view_flag:
        return render(request, 'manager_manage_designations.html', {'error': 'No access rights'})

    scope = (privilege.scope or 'OWN').strip().upper()
    if scope == 'SELF':
        scope = 'OWN'

    allowed_employee_ids = set()

    if scope == 'OWN':
        allowed_employee_ids.add(employee.employee_id)

    elif scope == 'NODE':
        team_ids = EmployeeMaster.objects.filter(manager_id=employee.employee_id).values_list('employee_id', flat=True)
        allowed_employee_ids.update(team_ids)
        allowed_employee_ids.add(employee.employee_id)

    elif scope == 'ALL':
        allowed_employee_ids.add(employee.employee_id)
        team_ids = EmployeeMaster.objects.filter(manager_id=employee.employee_id).values_list('employee_id', flat=True)
        allowed_employee_ids.update(team_ids)

        org_id = employee.organization_id.organization_id if employee.organization_id else None
        if org_id:
            child_org_ids = get_all_child_org_ids(org_id)
            org_ids = [org_id] + child_org_ids
            org_employees = EmployeeMaster.objects.filter(organization_id__in=org_ids).values_list('employee_id', flat=True)
            allowed_employee_ids.update(org_employees)

    designation_ids_qs = EmployeeMaster.objects.filter(
        employee_id__in=allowed_employee_ids,
        designation_id__isnull=False
    ).values_list('designation_id', flat=True).distinct()
    designation_ids = list(designation_ids_qs)

    print(f"[DEBUG] Scope: {scope}")
    print(f"[DEBUG] Allowed employee IDs: {allowed_employee_ids}")
    print(f"[DEBUG] Designation IDs: {designation_ids}")

    queryset = Designation.objects.filter(designation_id__in=designation_ids).order_by('designation_eng')

    paginator = Paginator(queryset, 10)
    page = request.GET.get('page', 1)
    designations = paginator.get_page(page)
    print(f"[DEBUG] Privileges: Create={privilege.create_flag}, Edit={privilege.edit_flag}, View={privilege.view_flag}")
    print(f"[DEBUG] Template flags: {privilege.create_flag == 'Y'}, {privilege.edit_flag == 'Y'}, {privilege.view_flag == 'Y'}")


    context = {
    'designations': designations,
    'designation_ids': designation_ids,
    'create_flag': privilege.create_flag == 'Y' or privilege.create_flag is True,
    'edit_flag': privilege.edit_flag == 'Y' or privilege.edit_flag is True,
    'view_flag': privilege.view_flag == 'Y' or privilege.view_flag is True,
    'delete_flag': privilege.delete_flag == 'Y' or privilege.delete_flag is True,
    'scope': scope,
    'user_emp_id': employee.employee_id,
    'page': int(page),
    'page_range': paginator.page_range,
    }
    print(f"[DEBUG] Template flags: {context['create_flag']}, {context['edit_flag']}, {context['view_flag']}")


    return render(request, 'manager_manage_designations.html', context)


    
@require_POST
@custom_login_required
def add_designation(request):
    employee_id = request.session['employee_id']
    employee = get_object_or_404(EmployeeMaster, employee_id=employee_id)

    code = request.POST.get('code')
    name = request.POST.get('designation_eng')
    vacancy = request.POST.get('vacancy')
    
    if not (code and name and vacancy):
            messages.error(request, "Code, Name and Vacancy are required.")
    elif not code[0].isalpha() or not name[0].isalpha():
            messages.error(request, "Code and Name must start with a letter.")
    elif Designation.objects.filter(code__iexact=code).exists():
            messages.error(request, f"Code '{code}' already exists.")
    
    else:
        if code and name:
            Designation.objects.create(
            code=code,
            designation_eng=name,
            vacancy=vacancy,
            remarks=request.POST.get('remarks'),
            created_id=request.session['user_id'],
            created_date=timezone.now(),
            last_updated_id=request.session['user_id'],
            last_updated_date=timezone.now()
            )
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Missing required fields'})

@require_POST
@custom_login_required
def update_designation(request, designation_id):
    employee_id = request.session['employee_id']
    employee = get_object_or_404(EmployeeMaster, employee_id=employee_id)

    # Corrected line below
    designation = get_object_or_404(Designation, designation_id=designation_id)

    designation.code = request.POST['code']
    designation.designation_eng = request.POST['designation_eng']
    designation.vacancy = request.POST['vacancy']
    designation.remarks = request.POST.get('remarks')
    designation.last_updated_id = employee.employee_id

    designation.last_updated_date = timezone.now()
    designation.save()

    return JsonResponse({'status': 'success'})

@custom_login_required
def get_designation_detail(request, designation_id):
    d = get_object_or_404(Designation, designation_id=designation_id)

    return JsonResponse({
        'code': d.code,
        'designation_eng': d.designation_eng,
        'vacancy': d.vacancy,
        'remarks': d.remarks,
        'created_date': d.created_date.strftime('%Y-%m-%d %H:%M:%S'),
        'last_updated_date': d.last_updated_date.strftime('%Y-%m-%d %H:%M:%S') if d.last_updated_date else ''
    })

@custom_login_required
def employee_attendance_reports(request):
    try:
        emp_id = request.session.get('employee_id')
        employee = EmployeeMaster.objects.get(employee_id=emp_id)
    except (KeyError, EmployeeMaster.DoesNotExist):
        return redirect('login')

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    attendance = DailyEmployeeAttendanceDetails.objects.filter(employee_id=employee)

    if from_date:
        attendance = attendance.filter(Ddate__gte=parse_date(from_date))
    if to_date:
        attendance = attendance.filter(Ddate__lte=parse_date(to_date))

    monthly_data = defaultdict(list)
    for item in attendance:
        month_key = item.Ddate.strftime("%Y-%m")
        monthly_data[month_key].append(item)

    report_data = []
    for month_key, records in monthly_data.items():
        has_data = any(i.time_in or i.time_out for i in records)
        if has_data:
            report_data.append({
                "employee": employee,
                "month": month_key,
                "month_label": datetime.strptime(month_key, "%Y-%m").strftime("%B %Y"),
            })

    return render(request, "employee_attendence_reports.html", {
        "report_data": report_data,
        "user": employee,
    })

@custom_login_required
def employee_attendance_report_pdf(request, emp_id, month):
    try:
        target_month = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise Http404("Invalid month format")

    employee = get_object_or_404(EmployeeMaster, employee_id=emp_id)
    records = DailyEmployeeAttendanceDetails.objects.filter(
        employee_id=employee,
        Ddate__year=target_month.year,
        Ddate__month=target_month.month
    ).order_by('Ddate')

    if not records.exists():
        raise Http404("No attendance data found")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    emp_name = f"{employee.firstname_eng or ''} {employee.lastname_eng or ''}".strip()
    emp_org = employee.organization_id.organization_eng if employee.organization_id else "-"
    emp_designation = employee.designation_id.designation_eng if employee.designation_id else "-"
    elements.append(Paragraph("<b>Attendance Report</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Employee:</b> {emp_name} ({employee.emp_no})", styles['Normal']))
    elements.append(Paragraph(f"<b>Organization:</b> {emp_org}", styles['Normal']))
    elements.append(Paragraph(f"<b>Designation:</b> {emp_designation}", styles['Normal']))
    elements.append(Paragraph(f"<b>Month:</b> {target_month.strftime('%B %Y')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    table_data = [[
        'Date', 'Punch In', 'Punch Out', 'Late (min)', 'Early (min)',
        'Work Mins', 'Extra Mins', 'Comment'
    ]]

    for row in records:
        table_data.append([
            row.Ddate.strftime('%Y-%m-%d') if row.Ddate else '-',
            row.time_in.strftime('%H:%M') if row.time_in else '-',
            row.time_out.strftime('%H:%M') if row.time_out else '-',
            str(row.late or 0),
            str(row.early or 0),
            str(row.workmts_row_timediff or 0),
            str(row.dailyextramts or 0),
            row.comment or '-'
        ])

    table = Table(table_data, colWidths=[1.0 * inch] * 8)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"Attendance_{employee.emp_no}_{month}.pdf")


def make_aware_safe(dt):
    """Ensure datetime is timezone-aware."""
    return make_aware(dt) if is_naive(dt) else dt

def get_schedule_for_day(employee, target_date):
    # Ensure target_date is a naive datetime (since DB is naive)
    date_dt = datetime.combine(target_date, time.min)  # Naive datetime

    weekday_field = target_date.strftime("%A").lower() + '_schedule_id'

    # 1. Employee Schedule
    emp_schedule = EmployeeSchedule.objects.filter(
        employee_id=employee,
        from_date__lte=date_dt,
        to_date__gte=date_dt
    ).first()
    if emp_schedule:
        schedule = getattr(emp_schedule, weekday_field)
        if schedule:
            return schedule, 'Employee'

    # 2. Group Schedule
    try:
        group = EmployeeGroupMember.objects.get(employee_id=employee).employee_group_id
        group_schedule = GroupSchedule.objects.filter(
            employee_group_id=group,
            from_date__lte=date_dt,
            to_date__gte=date_dt
        ).first()
        if group_schedule:
            schedule = getattr(group_schedule, weekday_field)
            if schedule:
                return schedule, 'Group'
    except EmployeeGroupMember.DoesNotExist:
        pass

    # 3. Organization Schedule
    org_schedules = OrganizationSchedule.objects.filter(
        organization_id=employee.organization_id,
        from_date__lte=date_dt
    ).order_by('-from_date')

    for org_schedule in org_schedules:
        if not org_schedule.to_date or org_schedule.to_date >= date_dt:
            schedule = getattr(org_schedule, weekday_field)
            if schedule:
                return schedule, 'Organization'

    return None, 'No Schedule'

@custom_login_required
def employee_schedule_calendar(request):
    employee_id = request.session.get('employee_id')
    employee = get_object_or_404(EmployeeMaster, employee_id=employee_id)

    today = now().replace(tzinfo=None).date()  # Strip timezone
    current_month = today.replace(day=1)
    days_in_month = monthrange(current_month.year, current_month.month)[1]

    calendar_data = []

    for day in range(1, days_in_month + 1):
        single_day = date(current_month.year, current_month.month, day)

        schedule, schedule_type = get_schedule_for_day(employee, single_day)

        calendar_data.append({
            'date': single_day,
            'schedule_type': schedule_type,
            'in_time': schedule.in_time if schedule else None,
            'out_time': schedule.out_time if schedule else None,
        })

    return render(request, 'employee_schedule.html', {
        'employee': employee,
        'calendar_data': calendar_data,
        'current_month': current_month,
    })

    

#---------------------------------MANAGERS-----------------------------
@custom_login_required
def managers_employee_report(request):
    try:
        manager = get_object_or_404(EmployeeMaster, employee_id=request.session['employee_id'])
    except KeyError:
        return redirect('login')

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # Get employees under this manager
    employees = EmployeeMaster.objects.filter(manager_id=manager)

    # Fetch attendance for these employees
    attendance = DailyEmployeeAttendanceDetails.objects.filter(employee_id__in=employees)

    if from_date:
        attendance = attendance.filter(Ddate__gte=from_date)
    if to_date:
        attendance = attendance.filter(Ddate__lte=to_date)

    # Group attendance by (employee, month)
    monthly_data = defaultdict(list)
    for item in attendance:
        month_key = item.Ddate.strftime("%Y-%m")
        key = (item.employee_id.employee_id, month_key)
        monthly_data[key].append(item)

    # Prepare final report data (only if there's at least 1 time_in or time_out)
    report_data = []
    for key, items in monthly_data.items():
        employee_id, month = key
        employee = items[0].employee_id
        month_label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")
        has_data = any(i.time_in or i.time_out for i in items)

        if has_data:
            report_data.append({
                "employee": employee,
                "month": month,
                "month_label": month_label,
            })

    return render(request, "managers_employee_report.html", {
        "report_data": report_data,
        "user": manager,
    })

@custom_login_required
def generate_employee_pdf(request, emp_id, month):
    try:
        # Parse month like '2025-07'
        target_month = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise Http404("Invalid month format")

    employee = EmployeeMaster.objects.filter(employee_id=emp_id).first()
    if not employee:
        raise Http404("Employee not found")

    # Get attendance records for that month
    records = DailyEmployeeAttendanceDetails.objects.filter(
        employee_id=employee,
        Ddate__year=target_month.year,
        Ddate__month=target_month.month
    ).order_by('Ddate')

    if not records.exists():
        raise Http404("No attendance data found")

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    emp_name = f"{employee.firstname_eng or ''} {employee.lastname_eng or ''}".strip()
    emp_org = employee.organization_id.organization_eng if employee.organization_id else "-"
    emp_designation = employee.designation_id.designation_eng if employee.designation_id else "-"
    elements.append(Paragraph(f"<b>Attendance Report</b>", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Employee:</b> {emp_name} ({employee.emp_no})", styles['Normal']))
    elements.append(Paragraph(f"<b>Organization:</b> {emp_org}", styles['Normal']))
    elements.append(Paragraph(f"<b>Designation:</b> {emp_designation}", styles['Normal']))
    elements.append(Paragraph(f"<b>Month:</b> {target_month.strftime('%B %Y')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Table Header
    table_data = [[
        'Date', 'Punch In', 'Punch Out', 'Late (min)', 'Early (min)',
        'Work Mins', 'Extra Mins', 'Comment'
    ]]

    # Table Rows
    for row in records:
        table_data.append([
            row.Ddate.strftime('%Y-%m-%d') if row.Ddate else '-',
            row.time_in.strftime('%H:%M') if row.time_in else '-',
            row.time_out.strftime('%H:%M') if row.time_out else '-',
            str(row.late or 0),
            str(row.early or 0),
            str(row.workmts_row_timediff or 0),
            str(row.dailyextramts or 0),
            row.comment or '-'
        ])

    # Table Styles
    table = Table(table_data, colWidths=[1.0*inch]*8)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)

    # Build and return response
    doc.build(elements)
    buffer.seek(0)
    filename = f"Attendance_{employee.emp_no}_{month}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


