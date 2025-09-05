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
    date = models.DateField(help_text="Fecha de la orden de trabajo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    id_usr_fk = models.IntegerField(help_text="ID del usuario responsable")
    id_eds_fk = models.IntegerField(help_text="ID de la estación de servicio")
    id_form_template_fk = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, help_text="Plantilla de formulario", db_column='id_form_template_fk')
    start_date_time = models.DateTimeField(blank=True, null=True)
    end_date_time = models.DateTimeField(blank=True, null=True)
    id_work_area_fk = models.IntegerField(blank=True, null=True, help_text="ID del área de trabajo")

    class Meta:
        db_table = 'WorkOrder'
        ordering = ['-date']

    def __str__(self):
        return f"{self.id_form_template_fk.name} - {self.date}"
    
    @property
    def name(self):
        """Obtiene el nombre de la plantilla de formulario"""
        return self.id_form_template_fk.name if self.id_form_template_fk else "Sin plantilla"
    
    @property
    def description(self):
        """Obtiene la descripción de la plantilla de formulario"""
        return self.id_form_template_fk.description if self.id_form_template_fk else "Sin descripción"

class FormQuestions(models.Model):
    """Preguntas que pertenecen a una plantilla de formulario específica"""
    TYPE_CHOICES = [
        ('text', 'Texto'),
        ('number', 'Número'),
        ('boolean', 'Sí/No'),
        ('date', 'Fecha'),
        ('file', 'Archivo'),
    ]
    
    id = models.AutoField(primary_key=True)
    question = models.TextField(help_text="Texto de la pregunta")
    is_required = models.BooleanField(default=False, help_text="¿Es obligatoria la respuesta?")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text', help_text="Tipo de respuesta esperada")
    id_form_template_fk = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, help_text="Plantilla a la que pertenece", db_column='id_form_template_fk')
    question_order = models.IntegerField(help_text="Orden de aparición de la pregunta")

    class Meta:
        db_table = 'FormQuestions'
        ordering = ['id_form_template_fk', 'question_order']

    def __str__(self):
        return f"{self.id_form_template_fk.name}: {self.question[:50]}..."

class FormAnswers(models.Model):
    """Respuestas a las preguntas de un formulario para una orden de trabajo específica"""
    id = models.AutoField(primary_key=True)
    id_question_form_fk = models.ForeignKey(FormQuestions, on_delete=models.CASCADE, help_text="Pregunta respondida", db_column='id_question_form_fk')
    work_order_id = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, help_text="Orden de trabajo", db_column='work_order_id')
    answer = models.TextField(blank=True, null=True, help_text="Respuesta a la pregunta")
    area = models.CharField(max_length=100, blank=True, null=True, help_text="Área específica del trabajo")
    comments = models.TextField(blank=True, null=True, help_text="Comentarios adicionales")
    image = models.CharField(max_length=255, blank=True, null=True, help_text="Nombre del archivo de imagen")

    class Meta:
        db_table = 'FormAnswers'
        # Permitir múltiples respuestas por pregunta (ej: diferentes caras, áreas, etc.)

    def __str__(self):
        return f"WO-{self.work_order_id.id}: {self.id_question_form_fk.question[:30]}..."

class Roles(models.Model):
    id_rol_pk = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    updated_at = models.DateField(null=True, blank=True)
    usr_created_at = models.CharField(max_length=65, null=True, blank=True)
    usr_updated_at = models.CharField(max_length=65, null=True, blank=True)
    id_permission_fk = models.IntegerField(null=True, blank=True)  # Referencia a Permissions
    role_status = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'Roles'

    def __str__(self):
        return self.name if self.name else f"Rol {self.id_rol_pk}"

class Permissions(models.Model):
    id_permissions_pk = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    updated_at = models.DateField(null=True, blank=True)
    usr_created_at = models.CharField(max_length=65, null=True, blank=True)
    usr_updated_at = models.CharField(max_length=65, null=True, blank=True)
    permission_status = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'Permissions'

    def __str__(self):
        return self.name if self.name else f"Permiso {self.id_permissions_pk}"
