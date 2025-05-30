from .base_window import BaseWindow
from .login_window import LoginWindow
from .dashboard_window import DashboardWindow, FacultyCard
from .consultation_panel import ConsultationRequestForm
from .admin_login_window import AdminLoginWindow
from .admin_dashboard_window import AdminDashboardWindow, FacultyManagementTab, StudentManagementTab, SystemMaintenanceTab

__all__ = [
    'BaseWindow',
    'LoginWindow',
    'DashboardWindow',
    'FacultyCard',
    'ConsultationRequestForm',
    'AdminLoginWindow',
    'AdminDashboardWindow',
    'FacultyManagementTab',
    'StudentManagementTab',
    'SystemMaintenanceTab'
]
