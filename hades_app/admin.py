from django.contrib import admin
from .models import Users
@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'role_name', 'usr_status']
    list_filter = ['usr_status', 'id_role_fk']
    search_fields = ['name', 'email']
    ordering = ['name']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('name', 'email', 'password')
        }),
        ('Estado y Permisos', {
            'fields': ('usr_status', 'id_role_fk')
        }),
        ('Asignaciones Futuras', {
            'fields': ('id_eds_fk', 'id_work_area_fk')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        # Si es un nuevo usuario o se cambió la contraseña, encriptarla
        if not change or 'password' in form.changed_data:
            if obj.password and not obj.password.startswith('pbkdf2_'):
                obj.set_password(obj.password)
        super().save_model(request, obj, form, change)
