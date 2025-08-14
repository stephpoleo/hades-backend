from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Router para API REST
router = DefaultRouter()
router.register(r'users', views.UsersViewSet)

urlpatterns = [
    # API REST endpoints
    path('api/', include(router.urls)),
    
    # API endpoint específico para listar usuarios
    path('api/users-list/', views.users_list, name='users-list'),
]