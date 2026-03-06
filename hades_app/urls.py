from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router para API REST
router = DefaultRouter()
router.register(r"users", views.UsersViewSet)
router.register(r"eds", views.EDSViewSet)
router.register(r"form-templates", views.FormTemplateViewSet)
router.register(r"work-orders", views.WorkOrderViewSet)
router.register(r"form-questions", views.FormQuestionsViewSet)
router.register(r"form-answers", views.FormAnswersViewSet)
router.register(r"roles", views.RolesViewSet)
router.register(r"permissions", views.PermissionsViewSet)

urlpatterns = [
    # API REST endpoints
    path("api/", include(router.urls)),
    path("api/form-templates/clear-all/", views.clear_form_templates, name="clear_form_templates"),
    path("api/work-orders/clear-all/", views.clear_work_orders, name="clear_work_orders"),
    # Dashboard KPIs endpoint
    path("api/dashboard/kpis/", views.dashboard_kpis, name="dashboard_kpis"),
    # Power BI endpoint
    path("api/powerbi/canastilla-inventory/", views.powerbi_canastilla_inventory, name="powerbi_canastilla_inventory"),
    # Auth endpoints para SPA/PWA
    path("api/auth/csrf/", views.csrf, name="csrf"),
    path("api/auth/login/", views.login_view, name="login"),
    path("api/auth/logout/", views.logout_view, name="logout"),
    path("api/auth/me/", views.me_view, name="me"),
]
