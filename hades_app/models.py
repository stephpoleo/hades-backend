from django.db import models
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.

class EDS(models.Model):
    id_eds_pk = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=65, null=True, blank=True)
    plaza = models.CharField(max_length=20, null=True, blank=True)
    state = models.CharField(max_length=20, null=True, blank=True)
    municipality = models.CharField(max_length=35, null=True, blank=True)
    zip_code = models.CharField(max_length=10, null=True, blank=True)
    plaza_status = models.BooleanField(null=True, blank=True)
    long_eds = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    latit_eds = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)

    class Meta:
        db_table = 'EDS'

class Users(models.Model):
    id_usr_pk = models.AutoField(primary_key=True)
    name = models.CharField(max_length=65)
    email = models.CharField(max_length=30, unique=True)
    password = models.CharField(max_length=100)
    usr_status = models.BooleanField(default=True)
    id_role_fk = models.IntegerField(null=True, blank=True)  # Referencia a Roles 
    id_eds_fk = models.IntegerField(null=True, blank=True)  # Referencia a EDS
    id_work_area_fk = models.IntegerField(null=True, blank=True)  # Referencia a WorkArea

    class Meta:
        db_table = 'Users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.name} ({self.email})"

    def set_password(self, raw_password):
        """Encripta la contraseña antes de guardarla"""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifica si la contraseña es correcta"""
        return check_password(raw_password, self.password)

    @property
    def is_active(self):
        """Retorna True si el usuario está activo"""
        return self.usr_status

    @property
    def role_name(self):
        """Retorna el nombre del rol del usuario (temporal)"""
        if self.id_role_fk == 1:
            return "Administrador"
        elif self.id_role_fk == 2:
            return "Empleado"
        else:
            return "Sin rol"
