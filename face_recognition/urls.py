"""
URL configuration for face_recognition project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from face_rec import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    #path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    #path('login/', views.login, name='login'),
    #path('logout/', views.logout_view, name='logout'),
    path('login/', views.login_view, name='login'),
    path('verify-face/', views.verify_face_page, name='verify_face'),
    path('verify-face-api/', views.verify_face, name='verify_face_api'),
    path('logout_face/', views.logout_face, name='logout_face_api'),
    path('verify_logout/', views.verify_logout_page, name='verify_logout'),
    path('chat/<int:receiver_id>/', views.chat_view, name='chat_view'),
    path('my/chat/', views.chat_dashboard, name='chat_dashboard'),
    path("ajax/employee-search/", views.employee_search, name="employee_search"),
    path("chatbot/", views.chatbot_view, name="chatbot"),

    #------ADMIN-----
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('organization/type/', views.organization_type_view, name='organization_type_view'),
    path('employees/', views.employee_manage_view, name='employee_manage'),
    path('employees/add/', views.employee_add_view, name='employee_add'),
    path('employees/block/<int:pk>/', views.employee_block, name='employee_block'),
    path('employees/unblock/<int:pk>/', views.employee_unblock, name='employee_unblock'),
    path('admin/employee/update/<int:emp_id>/', views.update_employee, name='update_employee'),
    path('countries/', views.country_list, name='country_list'),
    path('countries/add/', views.country_add, name='country_add'),
    path('countries/update/', views.country_update, name='country_update'),
    path('countries/delete/', views.country_delete, name='country_delete'),
    path('grades/', views.grade_list, name='grade_list'),
    path('grades/add/', views.grade_add, name='grade_add'),
    path('grades/update/', views.grade_update, name='grade_update'),
    path('grades/delete/', views.grade_delete, name='grade_delete'),
    path('designation/', views.designation_list, name='designation_list'),
    path('designation/add/', views.designation_add, name='designation_add'),
    path('designation/update/', views.designation_update, name='designation_update'),
    path('designation/delete/', views.designation_delete, name='designation_delete'),
    path('employee-type/', views.employee_type_list, name='employee_type_list'),
    path('employee-type/add/', views.employee_type_add, name='employee_type_add'),
    path('employee-type/update/', views.employee_type_update, name='employee_type_update'),
    path('employee-type/delete/', views.employee_type_delete, name='employee_type_delete'),
    path('permissions/', views.permission_type_list, name='permission_type_list'),
    path('permissions/add/', views.permission_type_add, name='permission_type_add'),
    path('permissions/update/', views.permission_type_update, name='permission_type_update'),
    path('permissions/delete/', views.permission_type_delete, name='permission_type_delete'),
    path('leave-type/', views.leave_type_list, name='leave_type_list'),
    path('leave-type/add/', views.leave_type_add, name='leave_type_add'),
    path('leave-type/update/', views.leave_type_update, name='leave_type_update'),
    path('leave-type/delete/', views.leave_type_delete, name='leave_type_delete'),
    path('employee-groups/', views.employee_group_list, name='employee_group_list'),
    path('employee-groups/add/', views.employee_group_add, name='employee_group_add'),
    path('employee-groups/update/', views.employee_group_update, name='employee_group_update'),
    path('employee-groups/delete/', views.employee_group_delete, name='employee_group_delete'),  
    path('groups/<int:group_id>/members/', views.admin_add_members, name='admin_add_members'),
    path('groups/<int:group_id>/members/add/', views.admin_add_members, name='admin_add_member'),
    path('groups/<int:group_id>/members/<int:member_id>/update/', views.admin_update_member, name='admin_update_member'),
    path('groups/<int:group_id>/members/<int:member_id>/delete/', views.admin_delete_member, name='admin_delete_member'),
    path('admin/schedules/', views.schedule_page, name='admin_add_schedule'),         
    path('admin/schedules/add/', views.add_schedule, name='add_schedule'),                 
    path('admin/schedules/edit/<int:schedule_id>/', views.edit_schedule, name='edit_schedule'),
    path('admin/schedules/delete/<int:schedule_id>/', views.delete_schedule, name='delete_schedule'),
    path('admin/org-schedule/', views.org_schedule_page, name='admin_add_org_schedule'),
    path('admin/org-schedule/add/', views.add_org_schedule, name='add_org_schedule'),
    path('admin/org-schedule/edit/<int:pk>/', views.edit_org_schedule, name='edit_org_schedule'),
    path('admin/org-schedule/delete/<int:pk>/', views.delete_org_schedule, name='delete_org_schedule'),
    path('admin/group-schedule/', views.group_schedule_page, name='group_schedule_page'),
    path('admin/group-schedule/add/', views.admin_add_grp_schedule, name='add_grp_schedule'),
    path('admin/group-schedule/edit/<int:pk>/', views.edit_grp_schedule, name='edit_grp_schedule'),
    path('admin/group-schedule/delete/<int:pk>/', views.delete_grp_schedule, name='delete_grp_schedule'),
    path('admin/employee-schedule/', views.employee_schedule_page, name='employee_schedule_page'),
    path('admin/employee-schedule/add/', views.add_employee_schedule, name='add_employee_schedule'),
    path('admin/employee-schedule/edit/<int:pk>/', views.edit_employee_schedule, name='edit_employee_schedule'),
    path('admin/employee-schedule/delete/<int:pk>/', views.delete_employee_schedule, name='delete_employee_schedule'),
    path('admin/add_organization/', views.admin_add_organization, name='admin_add_organization'),
    path('admin/add_organization/save/', views.add_organization, name='add_organization'),
    path('admin/update_organization/<int:org_id>/', views.update_organization, name='update_organization'),
    path('admin/add_ccompany/', views.admin_add_ccompany, name='admin_add_ccompany'),
    path('admin/add_ccompany/save/', views.add_ccompany, name='add_ccompany'),
    path('admin/update_ccompany/<int:company_id>/', views.update_ccompany, name='update_ccompany'),
    path('organization/hierarchy/', views.org_hierarchy_view, name='organization_hierarchy'),
    
    path('admin/privileges/', views.privilege_management, name='privilege_management'),
    path('admin/roles/create/', views.create_role, name='create_role'),
    path('admin/roles/<int:role_id>/privileges/', views.get_role_privileges, name='get_role_privileges'),
    path('admin/roles/<int:role_id>/save-privileges/', views.save_privileges, name='save_privileges'),
    path('admin/roles/<int:role_id>/users/', views.get_role_users, name='get_role_users'),
    path('admin/roles/<int:role_id>/add-user/', views.add_user_to_role, name='add_user_to_role'),
    path('api/search-users/', views.search_users_api, name='search_users_api'),
    
    path('admin/reports/', views.attendance_report, name='attendance_report'),
    path('admin/reports/pdf/<int:emp_id>/<str:month>/', views.generate_pdf, name='generate_pdf'),
     path('admin/holidays/', views.admin_add_holidays, name='admin_add_holidays'),
    path('admin/holidays/add/', views.add_holiday, name='add_holiday'),
    path('admin/holidays/update/<int:holiday_id>/', views.update_holiday, name='update_holiday'),



    #------EMPLOYEE-----
    path('employee_dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('employee/details/', views.employee_details, name='employee_details'),
    path('employee/update/<int:employee_id>/', views.employee_update, name='employee_update'),
    path('employee/permission-types/', views.employee_permission_type, name='employee_permission_type'),
    path('edit-permission/<int:perm_id>/', views.edit_permission_type, name='edit_permission_type'),
    path('employee/apply-leave/', views.employee_apply_leave, name='employee_apply_leave'),
    path('employee/apply-leave/add/', views.add_leave, name='add_leave'),
    path('employee/apply-leave/update/<int:pk>/', views.update_leave, name='update_leave'),
    path('employee/apply-leave/delete/<int:pk>/', views.delete_leave, name='delete_leave'),
    path('manager/approve-leaves/', views.managers_approve_leave, name='managers_approve_leave'),
    path('manager/approve-reject/<int:pk>/', views.approve_reject_leave, name='approve_reject_leave'),
     path('apply-permission/', views.employee_apply_permission, name='employee_apply_permission'),
    path('add-permission/', views.add_permission, name='add_permission'),
    path('update-permission/<int:pk>/', views.update_permission, name='update_permission'),
    path('delete-permission/<int:pk>/', views.delete_permission, name='delete_permission'),
    path('manager-approve-permission/', views.manager_approve_permission, name='manager_approve_permission'),
    path('approve-reject-permission/<int:pk>/', views.approve_reject_permission, name='approve_reject_permission'),
    path('employee/leave-types/', views.employee_view_leave_types, name='employee_view_leave_types'),
    path('employees/manage/', views.manage_employees, name='employee_manage_others'),
    path('employees/add/', views.employee_add_employee, name='employee_add_employee'),
    path('employees/update/<int:employee_id>/', views.employee_update_employee, name='employee_update_employee'),  # for POST
    path('employees/modal/<int:emp_id>/', views.update_employee_modal, name='employee_update_modal'),  # for AJAX GET
    path('employees/delete/<int:employee_id>/', views.employee_delete_employee, name='delete_employee'),
    path('manager_manage_designations/', views.manager_manage_designations, name='manager_manage_designations'),
    path('add_designation/', views.add_designation, name='add_designation'),
    path('update_designation/<int:designation_id>/', views.update_designation, name='update_designation'),
    path('get_designation_detail/<int:designation_id>/', views.get_designation_detail, name='get_designation_detail'),
    path('manager/reports/', views.managers_employee_report, name='managers_employee_report'),
    path('manager/reports/pdf/<int:emp_id>/<str:month>/', views.generate_employee_pdf, name='generate_employee_pdf'),
    path('attendance/reports/', views.employee_attendance_reports, name='employee_attendance_reports'),
    path('attendance/pdf/<str:emp_id>/<str:month>/', views.employee_attendance_report_pdf, name='employee_attendance_report_pdf'),
     path('employee_schedule/', views.employee_schedule_calendar, name='employee_schedule_calendar'),

    #path('test_manager/', views.test_manager_filter, name='test_manager_filter'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
