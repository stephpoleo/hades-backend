from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

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


# UserManager personalizado
class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('usr_status', True)
        return self.create_user(email, name, password, **extra_fields)

# Modelo de usuario principal
class Users(AbstractBaseUser, PermissionsMixin):
    id_usr_pk = models.AutoField(primary_key=True)
    name = models.CharField(max_length=65)
    email = models.EmailField(max_length=255, unique=True)
    usr_status = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    id_role_fk = models.IntegerField(null=True, blank=True)  # Referencia a Roles 
    id_eds_fk = models.IntegerField(null=True, blank=True)  # Referencia a EDS
    id_work_area_fk = models.IntegerField(null=True, blank=True)  # Referencia a WorkArea

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    class Meta:
        db_table = 'Users'

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def is_active(self):
        return self.usr_status

    @property
    def role_name(self):
        if self.id_role_fk == 1:
            return "Empleado"
        elif self.id_role_fk == 2:
            return "Administrador"
        else:
            return "Sin rol"

class FormTemplate(models.Model):
    """Plantillas de formularios para diferentes tipos de trabajo"""
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, help_text="Nombre del formulario/plantilla")
    description = models.TextField(blank=True, null=True, help_text="Descripción del tipo de trabajo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        db_table = 'FormTemplate'
        ordering = ['name']

    def __str__(self):
        return self.name

class WorkOrder(models.Model):
    """Órdenes de trabajo que utilizan plantillas de formularios"""
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]

    id = models.AutoField(primary_key=True)
    date = models.DateTimeField(help_text="Fecha y hora de la orden de trabajo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    user_id = models.IntegerField()
    eds_id = models.IntegerField()
    form_template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, help_text="Plantilla de formulario", db_column='form_template_id')
    start_date_time = models.DateTimeField(blank=True, null=True)
    end_date_time = models.DateTimeField(blank=True, null=True)
    work_area_id = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'WorkOrder'
        ordering = ['-date']

    def __str__(self):
        return f"{self.form_template.name} - {self.date}"
    
    @property
    def template_name(self):
        """Obtiene el nombre de la plantilla de formulario"""
        return self.form_template.name if self.form_template else "Sin plantilla"
    
    @property
    def template_description(self):
        """Obtiene la descripción de la plantilla de formulario"""
        return self.form_template.description if self.form_template else "Sin descripción"
    
class FormQuestions(models.Model):
    """Preguntas que pertenecen a una plantilla de formulario específica"""
    TYPE_CHOICES = [
        ('text', 'Texto'),
        ('number', 'Número'),
        ('boolean', 'Sí/No'),
        ('date', 'Fecha'),
        ('file', 'Archivo'),
        ('percent', 'Porcentaje'),
    ]
    
    id = models.AutoField(primary_key=True)
    question = models.TextField(help_text="Texto de la pregunta")
    is_required = models.BooleanField(default=False, help_text="¿Es obligatoria la respuesta?")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text', help_text="Tipo de respuesta esperada")
    question_order = models.IntegerField(help_text="Orden de aparición de la pregunta")
    form_template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='questions')

    class Meta:
        db_table = 'FormQuestions'
        ordering = ['question_order']

    def __str__(self):
        return f"{self.question[:50]}..."

class FormAnswers(models.Model):
    """Respuestas a las preguntas de un formulario para una orden de trabajo específica"""
    id = models.AutoField(primary_key=True)
    question = models.ForeignKey(FormQuestions, on_delete=models.CASCADE, help_text="Pregunta respondida", db_column='question_id')
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, help_text="Orden de trabajo", db_column='work_order_id')
    answer = models.TextField(blank=True, null=True, help_text="Respuesta a la pregunta")
    area = models.CharField(max_length=100, blank=True, null=True, help_text="Área específica del trabajo")
    comments = models.TextField(blank=True, null=True, help_text="Comentarios adicionales")
    image = models.ImageField(upload_to='form_answers/', blank=True, null=True, help_text="Archivo de imagen de la respuesta")

    class Meta:
        db_table = 'FormAnswers'

    def __str__(self):
        return f"WO-{self.work_order.id}: {self.question.question[:30]}..."
class Roles(models.Model):
    id_rol_pk = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    updated_at = models.DateField(null=True, blank=True)
    usr_created_at = models.CharField(max_length=65, null=True, blank=True)
    usr_updated_at = models.CharField(max_length=65, null=True, blank=True)
    permissions = models.ManyToManyField('Permissions', blank=True, related_name='roles')
    role_status = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'Roles'

    def __str__(self):
        return self.name if self.name else f"Rol {self.id_rol_pk}"

class Permissions(models.Model):
    id_permissions_pk = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    updated_at = models.DateField(null=True, blank=True)
    usr_created_at = models.CharField(max_length=65, null=True, blank=True)
    usr_updated_at = models.CharField(max_length=65, null=True, blank=True)
    permission_status = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'Permissions'

    def __str__(self):
        return self.name if self.name else f"Permiso {self.id_permissions_pk}"
