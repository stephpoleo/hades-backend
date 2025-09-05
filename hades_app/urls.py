from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router para API REST
router = DefaultRouter()
router.register(r'users', views.UsersViewSet)
router.register(r'eds', views.EDSViewSet)
router.register(r'form-templates', views.FormTemplateViewSet)
router.register(r'work-orders', views.WorkOrderViewSet)
router.register(r'form-questions', views.FormQuestionsViewSet)
router.register(r'form-answers', views.FormAnswersViewSet)
router.register(r'roles', views.RolesViewSet)
router.register(r'permissions', views.PermissionsViewSet)

urlpatterns = [
    # API REST endpoints
    path('api/', include(router.urls)),
    
    # API endpoint específico para listar usuarios
    path('api/users-list/', views.users_list, name='users-list'),
]