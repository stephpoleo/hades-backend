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
    # Las preguntas se relacionan por ForeignKey en FormQuestions

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
    image = models.CharField(max_length=255, blank=True, null=True, help_text="Nombre del archivo de imagen")

    class Meta:
        db_table = 'FormAnswers'
        # Permitir múltiples respuestas por pregunta (ej: diferentes caras, áreas, etc.)

    def __str__(self):
        return f"WO-{self.work_order.id}: {self.question.question[:30]}..."
