from django.db import models
from django.utils.timezone import now
from django.core.validators import FileExtensionValidator

class Country(models.Model):
    country_id = models.AutoField(primary_key=True,db_column='country_id')
    country_code = models.CharField(max_length=50, unique=True,db_column='country_code')
    country_eng = models.CharField(max_length=800, unique=True,db_column='country_eng')
    country_arb = models.CharField(max_length=800,db_column='country_arb')
    country_flag_url = models.CharField(max_length=800, null=True, blank=True,db_column='country_flag_url')
    created_id = models.IntegerField(db_column='created_id')
    created_date = models.DateTimeField(default=now,db_column='created_date')
    last_updated_id = models.IntegerField(db_column='last_updated_id')
    last_updated_date = models.DateTimeField(default=now,db_column='last_updated_date')

    class Meta:
        db_table = 'countries'
        managed = False



class Location(models.Model):
    location_id = models.AutoField(primary_key=True)
    location_code = models.CharField(max_length=200)
    location_eng = models.CharField(max_length=200, unique=True)
    location_arb = models.CharField(max_length=200, unique=True)
    city = models.CharField(max_length=500, null=True, blank=True)
    region_name = models.CharField(max_length=500, null=True, blank=True)

    country_code = models.ForeignKey(
        Country,
        to_field='country_code',
        db_column='country_code',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    radius = models.IntegerField(null=True, blank=True)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'locations'
        managed = False

class OrganizationType(models.Model):
    organization_type_id = models.AutoField(primary_key=True)
    organization_type_arb = models.CharField(max_length=500)
    organization_type_eng = models.CharField(max_length=500)
    OrgTypeLevel = models.IntegerField(default=1)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'organization_types'
        managed = False

class Organization(models.Model):
    organization_id = models.AutoField(primary_key=True)
    organization_type_id = models.ForeignKey(
        OrganizationType,
        on_delete=models.PROTECT,
        db_column='organization_type_id'
    )
    code = models.CharField(max_length=200)
    organization_eng = models.CharField(max_length=500)
    organization_arb = models.CharField(max_length=500)
    parent_id = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='parent_id',
        related_name='children'
    )
    position_in_grid = models.IntegerField(default=0)
    location_id = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='location_id'
    )
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'organizations'
        managed = False
    

class Grade(models.Model):
    grade_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=200)
    grade_eng = models.CharField(max_length=200)
    grade_arb = models.CharField(max_length=200)
    number_of_CL = models.IntegerField(default=0)  # Casual Leave
    number_of_SL = models.IntegerField(default=0)  # Sick Leave
    number_of_AL = models.IntegerField(default=0)  # Annual Leave
    overtime_eligible_flag = models.IntegerField(default=0, null=True, blank=True)
    senior_flag = models.IntegerField(default=0)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'grades'
        managed = False


class Designation(models.Model):
    designation_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=200)
    designation_arb = models.CharField(max_length=200)
    designation_eng = models.CharField(max_length=200)
    vacancy = models.IntegerField(default=0, null=True, blank=True)
    remarks = models.CharField(max_length=255, null=True, blank=True)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'designations'
        managed = False

class RamadanDate(models.Model):
    id = models.AutoField(primary_key=True)
    ramadan_name_eng = models.CharField(max_length=50, null=True, blank=True)
    ramadan_name_arb = models.CharField(max_length=50, null=True, blank=True)
    remarks = models.CharField(max_length=255, null=True, blank=True)
    from_date = models.DateTimeField(null=True, blank=True)
    to_date = models.DateTimeField(null=True, blank=True)
    created_id = models.IntegerField(null=True, blank=True)
    created_date = models.DateTimeField(default=now, null=True, blank=True)
    updated_id = models.IntegerField(null=True, blank=True)
    updated_date = models.DateTimeField(default=now, null=True, blank=True)

    class Meta:
        db_table = 'ramadan_Dates'
        managed = False



class Holiday(models.Model):
    holiday_id = models.AutoField(primary_key=True)
    holiday_eng = models.CharField(max_length=200)
    holiday_arb = models.CharField(max_length=200)
    remarks = models.CharField(max_length=255, null=True, blank=True)
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    recurring_flag = models.IntegerField()
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)

    class Meta:
        db_table = 'holidays'
        managed = False

class ContractorCompany(models.Model):
    contract_company_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    contract_company_eng = models.CharField(max_length=200, unique=True)
    contract_company_arb = models.CharField(max_length=200, unique=True)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='images/', null=True, blank=True)

    class Meta:
        db_table = 'contractor_companies'
        managed = False   
    
class EmployeeType(models.Model):
        employee_type_id = models.AutoField(primary_key=True)
        employee_type_code = models.CharField(max_length=50, unique=True)
        employee_type_eng = models.CharField(max_length=100, unique=True)
        employee_type_arb = models.CharField(max_length=100, unique=True)
        created_id = models.IntegerField()
        created_date = models.DateTimeField(default=now, null=True, blank=True)
        last_updated_id = models.IntegerField()
        last_updated_date = models.DateTimeField(default=now)
        
        class Meta:
            db_table = 'employee_type'
            managed = False
            
class PermissionType(models.Model):
    permission_type_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50)
    permdescription_arb = models.CharField(max_length=100)
    permdescription_eng = models.CharField(max_length=100)
    max_perm_per_day = models.IntegerField(null=True, blank=True)
    max_minutes_per_day = models.IntegerField(null=True, blank=True)
    max_perm_per_month = models.IntegerField(null=True, blank=True)
    max_minutes_per_month = models.IntegerField(null=True, blank=True)
    group_apply_flag = models.IntegerField(default=0)
    official_flag = models.IntegerField(default=0, null=True, blank=True)
    full_day_flag = models.IntegerField(default=0, null=True, blank=True)
    Status_Flag = models.BooleanField(default=False)
    Workflow_Id = models.IntegerField(null=True, blank=True)
    specific_gender = models.CharField(max_length=1, null=True, blank=True)

    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)

    class Meta:
        db_table = 'permission_types'
        managed = False
        
        
class LeaveType(models.Model):
    leave_type_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50)
    leaveDesc_eng = models.CharField(max_length=200, null=True, blank=True)
    leaveDesc_arb = models.CharField(max_length=200, null=True, blank=True)
    approve_need_flag = models.IntegerField(default=0, null=True, blank=True)
    official_flag = models.IntegerField(default=0, null=True, blank=True)
    status_Flag = models.BooleanField(default=False)
    allow_attachment = models.IntegerField(default=0, null=True, blank=True)
    workflow_Id = models.IntegerField(null=True, blank=True)
    is_comment_mandatory = models.BooleanField(default=False, null=True, blank=True)
    total_entitled_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    full_pay_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    half_pay_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unpaidDays = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    apply_prior_to_days = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    Is_AL_flag = models.IntegerField(default=0, null=True, blank=True)
    Is_SL_flag = models.IntegerField(default=0, null=True, blank=True)
    exclude_holiday = models.IntegerField(default=0, null=True, blank=True)
    exclude_weekend = models.IntegerField(default=0, null=True, blank=True)
    apply_not_laterthandays = models.IntegerField(null=True, blank=True)
    is_validation_mandatory = models.IntegerField(null=True, blank=True)
    leave_by_overtime = models.IntegerField(null=True, blank=True)
    carryforwardflg = models.IntegerField(null=True, blank=True)
    specific_gender = models.CharField(max_length=1, null=True, blank=True)

    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'leave_types'
        managed = False



class EmployeeMaster(models.Model):
    employee_id = models.AutoField(primary_key=True, db_column='employee_id')
    emp_no = models.CharField(max_length=50, db_column='emp_no')
    firstname_eng = models.CharField(max_length=800, db_column='firstname_eng')
    lastname_eng = models.CharField(max_length=800, db_column='lastname_eng')
    firstname_arb = models.CharField(max_length=800, db_column='firstname_arb')
    lastname_arb = models.CharField(max_length=800, db_column='lastname_arb')
    card_number = models.CharField(max_length=100, null=True, db_column='card_number')
    pin = models.CharField(max_length=100, null=True, db_column='pin')

    organization_id = models.ForeignKey('Organization', models.SET_NULL, null=True, db_column='organization_id')
    grade_id = models.ForeignKey('Grade', models.SET_NULL, null=True, db_column='grade_id')
    designation_id = models.ForeignKey('Designation', models.SET_NULL, null=True, db_column='designation_id')
    employee_type_id = models.ForeignKey('EmployeeType', models.SET_NULL, null=True, db_column='employee_type_id')


    join_date = models.DateTimeField(null=True, db_column='join_date')
    active_date = models.DateTimeField(null=True, db_column='active_date')
    inactive_date = models.DateTimeField(null=True, db_column='inactive_date')
    passport_issue_country_id = models.ForeignKey('Country', models.SET_NULL, null=True, db_column='passport_issue_country_Id')

    mobile = models.CharField(max_length=100, null=True, db_column='mobile')
    email = models.CharField(max_length=500, null=True, db_column='email')

    active_flag = models.IntegerField(null=True, default=1, db_column='active_flag')
    gender = models.CharField(max_length=10, null=True, db_column='gender')
    local_flag = models.IntegerField(null=True, default=0, db_column='local_flag')
    on_reports_flag = models.IntegerField(null=True, default=1, db_column='on_reports_flag')
    punch_flag = models.IntegerField(null=True, default=1, db_column='punch_flag')
    open_shift_flag = models.IntegerField(null=True, default=0, db_column='open_shift_flag')
    overtime_flag = models.IntegerField(null=True, default=0, db_column='overtime_flag')
    web_punch_flag = models.IntegerField(null=True, default=0, db_column='web_punch_flag')
    check_inout_self = models.IntegerField(null=True, default=1, db_column='check_inout_self')
    calculate_monthly_missed_hrs = models.IntegerField(null=True, default=0, db_column='calculate_monthly_missed_hrs')
    photo_file_name = models.ImageField(upload_to='employee_photos/', null=True, blank=True, db_column='photo_file_name')

    manager_flag = models.CharField(max_length=1, null=True, default='Y', db_column='manager_flag')
    manager_id = models.ForeignKey('self', models.SET_NULL, null=True, blank=True, db_column='manager_id')
    
    inpayroll = models.IntegerField(null=True, default=0, db_column='inpayroll')
    share_roster = models.IntegerField(null=True, default=0, db_column='share_roster')
    
    work_location_id = models.ForeignKey('Location', models.SET_NULL, null=True, db_column='work_location_id')
    contract_company_id = models.ForeignKey('ContractorCompany', models.SET_NULL, null=True, db_column='contract_company_id')

    remarks = models.CharField(max_length=900, null=True, db_column='remarks')
    created_id = models.IntegerField(db_column='created_id')
    created_date = models.DateTimeField(db_column='created_date', auto_now_add=False)
    last_updated_id = models.IntegerField(db_column='last_updated_id')
    last_updated_date = models.DateTimeField(db_column='last_updated_date', auto_now_add=False)

    class Meta:
        db_table = 'employee_master'
        managed = False


class SecUser(models.Model):
    user_id=models.AutoField(primary_key=True)
    login = models.CharField(max_length=200, null=True, blank=True)
    password = models.CharField(max_length=256, null=True, blank=True)
    employee_id = models.ForeignKey(EmployeeMaster, on_delete=models.CASCADE,db_column='employee_id')
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'sec_users'
        managed = False

class EmployeeGroup(models.Model):
    employee_group_id = models.AutoField(primary_key=True)
    group_code = models.CharField(max_length=50, null=True, blank=True)
    group_name_eng = models.CharField(max_length=200, null=True, blank=True)
    group_name_arb = models.CharField(max_length=200, null=True, blank=True)
    schedule_flag = models.BooleanField(default=False)
    group_start_Date = models.DateTimeField(null=True, blank=True)
    group_end_Date = models.DateTimeField(null=True, blank=True)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'employee_groups'
        managed = False

class EmployeeGroupMember(models.Model):
    group_member_id = models.AutoField(primary_key=True)
    employee_group_id = models.ForeignKey('EmployeeGroup', on_delete=models.CASCADE, db_column='employee_group_id')
    employee_id = models.ForeignKey('EmployeeMaster', on_delete=models.CASCADE, db_column='employee_id')
    effective_from_date = models.DateTimeField()
    effective_to_date = models.DateTimeField(null=True, blank=True)
    active_flag = models.IntegerField(default=0)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'employee_group_members'
        managed = False

class EmployeeLeave(models.Model):
    employee_leave_id = models.AutoField(primary_key=True)
    leave_type_id = models.ForeignKey('LeaveType', on_delete=models.CASCADE, db_column='leave_type_id')
    employee_id = models.ForeignKey('EmployeeMaster', on_delete=models.CASCADE, db_column='employee_id')
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    number_of_leaves = models.IntegerField(null=True, blank=True)
    employee_remarks = models.TextField(null=True, blank=True)
    approve_reject_flag = models.IntegerField(default=0, null=True, blank=True)
    #approver_id = models.IntegerField('EmployeeMaster', on_delete=models.SET_NULL, db_column='employee_id',null=True, blank=True)
    approver_id = models.ForeignKey('EmployeeMaster',on_delete=models.SET_NULL,null=True,blank=True,db_column='approver_id',related_name='leaves_approved')
    approver_remarks = models.TextField(null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    leave_status = models.CharField(max_length=50, null=True, blank=True)
    alternate_employee_id = models.IntegerField(null=True, blank=True)
    handovers_to_alternate_employee = models.TextField(null=True, blank=True)
    leave_doc_filename_path = models.FileField(upload_to='leave_docs/', null=True, blank=True)
    leave_UniqueRefNo = models.CharField(max_length=500, null=True, blank=True)
    carryforward = models.IntegerField(null=True, blank=True)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'employee_leaves'
        managed = False

class EmployeeShortPermission(models.Model):
    single_permissions_id = models.AutoField(primary_key=True)
    permission_type_id = models.ForeignKey('PermissionType', on_delete=models.CASCADE, db_column='permission_type_id')
    employee_id = models.ForeignKey('EmployeeMaster', on_delete=models.CASCADE, db_column='employee_id')
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    from_time = models.TimeField(null=True, blank=True)
    to_time = models.TimeField(null=True, blank=True)
    perm_minutes = models.IntegerField(null=True, blank=True)
    remarks = models.TextField()
    approver_remarks = models.TextField(null=True, blank=True)
    approve_reject_flag = models.IntegerField(default=0)
    approver_id = models.ForeignKey('EmployeeMaster',on_delete=models.SET_NULL,null=True,blank=True,db_column='approver_id',related_name='short_perm_approved')
    approved_date = models.DateTimeField(null=True, blank=True)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'employee_short_permissions'
        managed = False


class Schedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    organization_id = models.ForeignKey('Organization', on_delete=models.CASCADE, db_column='organization_id')
    schedule_code = models.CharField(max_length=10)
    in_time = models.DateTimeField(null=True, blank=True)
    out_time = models.DateTimeField(null=True, blank=True)
    flexible_min = models.IntegerField(default=0, null=True, blank=True)
    grace_in_min = models.IntegerField(default=0, null=True, blank=True)
    grace_out_min = models.IntegerField(default=0, null=True, blank=True)
    open_shift = models.IntegerField(default=0, null=True, blank=True)
    night_shift = models.IntegerField(default=0, null=True, blank=True)
    sch_color = models.CharField(max_length=10, null=True, blank=True)
    ramadan_flag = models.BooleanField(default=False)
    sch_parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, db_column='sch_parent_id')
    required_work_hours = models.DateTimeField(null=True, blank=True)
    Status_Flag = models.BooleanField(default=True)
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'schedules'
        managed = False

class OrganizationSchedule(models.Model):
    organization_schedule_id = models.AutoField(primary_key=True)
    organization_id = models.ForeignKey('Organization', on_delete=models.CASCADE, db_column='organization_id')
    from_date = models.DateTimeField()
    to_date = models.DateTimeField(null=True, blank=True)
    monday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='monday_schedule_id', related_name='+')
    tuesday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='tuesday_schedule_id', related_name='+')
    wednesday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='wednesday_schedule_id', related_name='+')
    thursday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='thursday_schedule_id', related_name='+')
    friday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='friday_schedule_id', related_name='+')
    saturday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='saturday_schedule_id', related_name='+')
    sunday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='sunday_schedule_id', related_name='+')
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'organization_schedules'
        managed = False

class GroupSchedule(models.Model):
    group_schedule_id = models.AutoField(primary_key=True)
    employee_group_id = models.ForeignKey('EmployeeGroup', on_delete=models.CASCADE, db_column='employee_group_id')
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    monday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='monday_schedule_id', related_name='+')
    tuesday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='tuesday_schedule_id', related_name='+')
    wednesday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='wednesday_schedule_id', related_name='+')
    thursday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='thursday_schedule_id', related_name='+')
    friday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='friday_schedule_id', related_name='+')
    saturday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='saturday_schedule_id', related_name='+')
    sunday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='sunday_schedule_id', related_name='+')
    created_id = models.IntegerField()
    created_time = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)

    class Meta:
        db_table = 'group_schedules'
        managed = False

class EmployeeSchedule(models.Model):
    employee_schedule_id = models.AutoField(primary_key=True)
    employee_id = models.ForeignKey('EmployeeMaster', on_delete=models.CASCADE, db_column='employee_id')
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    monday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='monday_schedule_id', related_name='+')
    tuesday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='tuesday_schedule_id', related_name='+')
    wednesday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='wednesday_schedule_id', related_name='+')
    thursday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='thursday_schedule_id', related_name='+')
    friday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='friday_schedule_id', related_name='+')
    saturday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='saturday_schedule_id', related_name='+')
    sunday_schedule_id = models.ForeignKey('Schedule', null=True, blank=True, on_delete=models.SET_NULL, db_column='sunday_schedule_id', related_name='+')
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'employee_schedules'
        managed = False

class EmployeeEventTransaction(models.Model):
    transaction_id = models.AutoField(primary_key=True)
    employee_id = models.ForeignKey('EmployeeMaster', on_delete=models.CASCADE, db_column='employee_id')
    transaction_time = models.DateTimeField()
    reason = models.CharField(max_length=10)
    remarks = models.CharField(max_length=255, null=True, blank=True)
    reader_id = models.IntegerField(null=True, blank=True)
    user_entry_flag = models.IntegerField()
    created_id = models.IntegerField()
    created_date = models.DateTimeField(default=now)
    last_updated_id = models.IntegerField()
    last_updated_date = models.DateTimeField(default=now)

    class Meta:
        db_table = 'employee_event_transactions'
        managed = False
        
class ChatMessage(models.Model):
    chat_id = models.AutoField(primary_key=True, db_column='chat_id')
    sender_id = models.ForeignKey('EmployeeMaster', related_name='sent_messages', on_delete=models.CASCADE,db_column='sender_id' )
    receiver_id = models.ForeignKey('EmployeeMaster', related_name='received_messages', on_delete=models.CASCADE,db_column='receiver_id')
    message_text = models.TextField(blank=True, null=True)

    file_path = models.FileField(
        upload_to='chat_uploads/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'pdf', 'docx'])],
        blank=True,
        null=True
    )
    file_type = models.CharField(max_length=50, blank=True, null=True)  # image, pdf, docx
    is_bad_content = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender} to {self.receiver} at {self.timestamp}"
    class Meta:
        db_table = 'ChatMessage'
        managed = False



class SecPrivilegeGroup(models.Model):
    privilege_group_id= models.AutoField(primary_key=True, db_column='privilege_group_id')
    group_name = models.CharField(max_length=50)
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)
    
    class Meta:
        db_table = 'sec_privilege_groups'
        managed = False


class SecModule(models.Model):
    module_id= models.AutoField(primary_key=True, db_column='module_id')
    module_name = models.CharField(max_length=50)
    privilege_group_id = models.ForeignKey(SecPrivilegeGroup, null=True, blank=True, on_delete=models.SET_NULL,db_column='privilege_group_id')
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)

    class Meta:
        db_table = 'sec_modules'
        managed = False

class SecSubModule(models.Model):
    sub_module_id= models.AutoField(primary_key=True, db_column='sub_module_id')
    sub_module_name = models.CharField(max_length=50)
    module_id = models.ForeignKey(SecModule, null=True, blank=True, on_delete=models.SET_NULL,db_column='module_id')
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)

    class Meta:
        db_table = 'sec_sub_modules'
        managed = False

class SecRole(models.Model):
    role_id= models.AutoField(primary_key=True, db_column='role_id')
    role_name = models.CharField(max_length=20)
    editable_flag = models.BooleanField(default=False)
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)

    class Meta:
        db_table = 'sec_roles'
        managed = False

class SecRolePrivilege(models.Model):
    SCOPE_CHOICES = (
        ('ALL', 'All'),
        ('NODE', 'Node'),
        ('OWN', 'Own'),
    )
    role_privilege_id= models.AutoField(primary_key=True, db_column='role_privilege_id')
    role_id = models.ForeignKey(SecRole, on_delete=models.CASCADE,db_column='role_id')
    sub_module_id = models.ForeignKey(SecSubModule, null=True, blank=True, on_delete=models.SET_NULL,db_column='sub_module_id')
    scope = models.CharField(max_length=5, choices=SCOPE_CHOICES)
    access_flag = models.BooleanField(default=False)
    view_flag = models.BooleanField(default=False)
    create_flag = models.BooleanField(default=False)
    edit_flag = models.BooleanField(default=False)
    delete_flag = models.BooleanField(default=False)
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)

    class Meta:
        db_table = 'sec_role_privileges'
        managed = False

class SecUserRole(models.Model):
    user_role_id= models.AutoField(primary_key=True, db_column='user_role_id')
    user_id = models.ForeignKey(SecUser, on_delete=models.CASCADE,db_column='user_id')
    role_id = models.ForeignKey(SecRole, on_delete=models.CASCADE,db_column='role_id')
    last_updated_id = models.IntegerField()
    last_updated_time = models.DateTimeField(default=now)
    
    class Meta:
        db_table = 'sec_user_roles'
        managed = False



class DailyEmployeeAttendanceDetails(models.Model):
    daily_EmployeeAttendanceDetails_id = models.AutoField(primary_key=True)
    Ddate = models.DateTimeField()
    employee_id = models.ForeignKey('EmployeeMaster', on_delete=models.DO_NOTHING, db_column='employee_id')

    employee_no = models.CharField(max_length=50)
    organization_id = models.ForeignKey('Organization', on_delete=models.DO_NOTHING, db_column='organization_id', null=True, blank=True)
    designation_id = models.ForeignKey('Designation', on_delete=models.DO_NOTHING, db_column='designation_id', null=True, blank=True)

    manager_id = models.IntegerField(null=True, blank=True)
    email = models.CharField(max_length=50, null=True, blank=True)
    schedule_id = models.ForeignKey('Schedule', on_delete=models.DO_NOTHING, db_column='schedule_id', null=True, blank=True)
    grade_id = models.ForeignKey('Grade', on_delete=models.DO_NOTHING, db_column='grade_id', null=True, blank=True)
    country_id = models.ForeignKey('Country', on_delete=models.DO_NOTHING, db_column='country_id', null=True, blank=True)
    
    in_time = models.DateTimeField(null=True, blank=True)
    out_time = models.DateTimeField(null=True, blank=True)
    time_in = models.DateTimeField(blank=True, null=True)
    time_out = models.DateTimeField(blank=True, null=True)

    late = models.IntegerField(null=True, blank=True)
    early = models.IntegerField(null=True, blank=True)
    workmts_row_timediff = models.IntegerField(null=True, blank=True)

    comment = models.CharField(max_length=50, null=True, blank=True)
    gracetime_in = models.IntegerField(db_column='gracetime_in', null=True, blank=True)
    gracetime_out = models.IntegerField(db_column='gracetime_out', null=True, blank=True)
    actualschInPerMove = models.DateTimeField(null=True, blank=True)
    actualschOutPerMove = models.DateTimeField(null=True, blank=True)
    actualschOUTCalculated = models.DateTimeField(null=True, blank=True)
    nightshift = models.IntegerField(db_column='nightshift', null=True, blank=True)
    leave = models.BooleanField(db_column='leave', null=True)
    isabsent = models.BooleanField(db_column='isabsent', null=True)
    empleaveid = models.IntegerField(db_column='empleaveid', null=True, blank=True)
    holidayid = models.IntegerField(db_column='holidayid', null=True, blank=True)
    
    in_permissionid = models.IntegerField(db_column='in_permissionid', null=True, blank=True)
    in_perm_from_time = models.DateTimeField(db_column='in_perm_from_time', null=True, blank=True)
    in_perm_to_time = models.DateTimeField(db_column='in_perm_to_time', null=True, blank=True)
    out_permissionid = models.IntegerField(db_column='out_permissionid', null=True, blank=True)
    out_perm_from_time = models.DateTimeField(db_column='out_perm_from_time', null=True, blank=True)
    out_perm_to_time = models.DateTimeField(db_column='out_perm_to_time', null=True, blank=True)
    fulldaypermission = models.IntegerField(db_column='fulldaypermission', null=True, blank=True)
    in_offcialperm = models.CharField(max_length=1, db_column='in_offcialperm', null=True, blank=True)
    out_offcialperm = models.CharField(max_length=1, db_column='out_offcialperm', null=True, blank=True)

    permappliedMts = models.IntegerField(db_column='permappliedMts', null=True, blank=True)
    perm_time_used_wp = models.IntegerField(db_column='perm_time_used_wp', null=True, blank=True)
    perm_time_used_wop = models.IntegerField(db_column='perm_time_used_wop', null=True, blank=True)
    open_shift = models.CharField(max_length=1, db_column='open_shift', null=True, blank=True)
    shiftno = models.IntegerField(db_column='shiftno', null=True, blank=True)
    workmts_row_timediff = models.IntegerField(db_column='workmts_row_timediff', null=True, blank=True)
    overtime = models.IntegerField(db_column='overtime', null=True, blank=True)
    comment_for_update = models.CharField(max_length=200, db_column='comment_for_update', null=True, blank=True)
    permviolatedmts = models.IntegerField(db_column='permviolatedmts', null=True, blank=True)
    isovertimecounted = models.IntegerField(db_column='isovertimecounted', null=True, blank=True)
    
    missedwrkmts = models.IntegerField(db_column='missedwrkmts', null=True, blank=True)
    extrawrkmts = models.IntegerField(db_column='extrawrkmts', null=True, blank=True)
    monthlymissedmts = models.IntegerField(db_column='monthlymissedmts', null=True, blank=True)
    monthlyextramts = models.IntegerField(db_column='monthlyextramts', null=True, blank=True)
    dailymissedmts = models.IntegerField(db_column='dailymissedmts', null=True, blank=True)
    dailyextramts = models.IntegerField(db_column='dailyextramts', null=True, blank=True)
    dailyworkmts = models.IntegerField(db_column='dailyworkmts', null=True, blank=True)

    holiday = models.BooleanField(null=True, blank=True)
    restday = models.BooleanField(null=True, blank=True)
    leave = models.BooleanField(null=True, blank=True)
    isabsent = models.BooleanField(null=True, blank=True)

    created_date = models.DateTimeField()
    last_updated_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'daily_EmployeeAttendanceDetails'

        
