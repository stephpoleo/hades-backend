from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.conf import settings

# Create your models here.

EDS_DB_TABLE_NAME = getattr(settings, "EDS_DB_TABLE", "oasis_cat_eds")


class EDS(models.Model):
    id_eds_pk = models.CharField(
        primary_key=True,
        max_length=10,
        db_column="cod_eds",
        help_text="Identificador oficial de la estación en la base externa.",
    )
    sap_code = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        db_column="cod_sap",
        help_text="Código SAP asociado a la estación.",
    )
    name = models.CharField(
        max_length=65,
        blank=True,
        null=True,
        db_column="nom",
        help_text="Nombre descriptivo de la estación.",
    )
    permit_code = models.CharField(
        max_length=22,
        blank=True,
        null=True,
        db_column="perm_cre",
        help_text="Permiso CRE registrado para la estación.",
    )
    plaza = models.CharField(max_length=30, blank=True, null=True)
    state = models.CharField(
        max_length=45,
        blank=True,
        null=True,
        db_column="cd",
        help_text="Entidad o ciudad reportada en la tabla oasis_cat_eds.",
    )
    municipality = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        db_column="col",
        help_text="Municipio o colonia registrada para la estación.",
    )
    zip_code = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        db_column="cp",
    )
    plaza_status = models.BooleanField(
        blank=True,
        null=True,
        db_column="is_activa",
        help_text="Indicador de actividad según la fuente externa.",
    )
    status_code = models.SmallIntegerField(
        blank=True,
        null=True,
        db_column="stat",
        help_text="Estado numérico original reportado por oasis_cat_eds.",
    )
    long_eds = models.DecimalField(
        max_digits=17,
        decimal_places=7,
        blank=True,
        null=True,
        db_column="long_eds",
    )
    latit_eds = models.DecimalField(
        max_digits=17,
        decimal_places=7,
        blank=True,
        null=True,
        db_column="latid_eds",
    )
    phone = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        db_column="tel_eds",
    )
    email = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_column="email",
    )
    legal_rep_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        db_column="cod_rep_legal",
    )
    legal_rep_name = models.CharField(
        max_length=135,
        blank=True,
        null=True,
        db_column="nom_rep_legal",
    )
    street = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_column="calle",
    )
    street_number = models.CharField(
        max_length=45,
        blank=True,
        null=True,
        db_column="num",
    )
    zone_id = models.IntegerField(blank=True, null=True, db_column="id_zona_fk")
    alert_amount = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        blank=True,
        null=True,
        db_column="monto_alrta",
    )
    max_average_amount = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        blank=True,
        null=True,
        db_column="monto_max_prom",
    )
    island_count = models.SmallIntegerField(
        blank=True,
        null=True,
        db_column="num_islas",
    )
    conversion_factor = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        blank=True,
        null=True,
        db_column="factr_cnvrs",
    )
    public_price_gnv = models.DecimalField(
        max_digits=17,
        decimal_places=4,
        blank=True,
        null=True,
        db_column="prcio_pblic_gnv",
    )
    created_at_remote = models.DateTimeField(
        blank=True, null=True, db_column="fch_alta"
    )
    updated_at_remote = models.DateTimeField(
        blank=True, null=True, db_column="fch_modif"
    )
    created_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_column="usr_alta",
    )
    updated_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_column="usr_modif",
    )
    responsible_user = models.CharField(
        max_length=135,
        blank=True,
        null=True,
        db_column="rspnb_usr",
    )
    printer_ip = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        db_column="ip_impresora",
    )
    fillpost_permit_code = models.CharField(
        max_length=22,
        blank=True,
        null=True,
        db_column="perm_cre_fillpost",
    )
    fillpost_station_name = models.CharField(
        max_length=65,
        blank=True,
        null=True,
        db_column="nom_eds_fillpost",
    )
    fillpost_sap_code = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        db_column="cod_sap_fillpost",
    )
    is_descompresion = models.BooleanField(
        blank=True, null=True, db_column="is_descompresion"
    )
    calorific_power = models.DecimalField(
        max_digits=13,
        decimal_places=4,
        blank=True,
        null=True,
        db_column="pod_cal",
    )

    class Meta:
        managed = False
        db_table = EDS_DB_TABLE_NAME


# UserManager personalizado
class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("usr_status", True)
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
    id_eds_fk = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Código de la EDS en la base externa",
    )
    id_work_area_fk = models.IntegerField(
        null=True, blank=True
    )  # Referencia a WorkArea

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        db_table = "Users"

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
    description = models.TextField(
        blank=True, null=True, help_text="Descripción del tipo de trabajo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "FormTemplate"
        ordering = ["name"]

    def __str__(self):
        return self.name


class WorkOrder(models.Model):
    """Órdenes de trabajo que utilizan plantillas de formularios"""

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("in_progress", "En Progreso"),
        ("completed", "Completado"),
        ("cancelled", "Cancelado"),
    ]

    id = models.AutoField(primary_key=True)
    date = models.DateTimeField(help_text="Fecha y hora de la orden de trabajo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    user_id = models.IntegerField()
    eds_id = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="Código de la EDS asignada a la orden",
    )
    form_template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE,
        help_text="Plantilla de formulario",
        db_column="form_template_id",
    )
    start_date_time = models.DateTimeField(blank=True, null=True)
    end_date_time = models.DateTimeField(blank=True, null=True)
    work_area_id = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = "WorkOrder"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.form_template.name} - {self.date}"

    @property
    def template_name(self):
        """Obtiene el nombre de la plantilla de formulario"""
        return self.form_template.name if self.form_template else "Sin plantilla"

    @property
    def template_description(self):
        """Obtiene la descripción de la plantilla de formulario"""
        return (
            self.form_template.description if self.form_template else "Sin descripción"
        )


class FormQuestions(models.Model):
    """Preguntas que pertenecen a una plantilla de formulario específica"""

    TYPE_CHOICES = [
        ("text", "Texto"),
        ("number", "Número"),
        ("boolean", "Sí/No"),
        ("date", "Fecha"),
        ("file", "Archivo"),
        ("percent", "Porcentaje"),
    ]

    id = models.AutoField(primary_key=True)
    question = models.TextField(help_text="Texto de la pregunta")
    is_required = models.BooleanField(
        default=False, help_text="¿Es obligatoria la respuesta?"
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="text",
        help_text="Tipo de respuesta esperada",
    )
    question_order = models.IntegerField(help_text="Orden de aparición de la pregunta")
    form_template = models.ForeignKey(
        FormTemplate, on_delete=models.CASCADE, related_name="questions"
    )
    allow_comments = models.BooleanField(
        default=False,
        help_text="Permite capturar comentarios adicionales para la pregunta.",
    )
    allow_attachments = models.BooleanField(
        default=False,
        help_text="Permite adjuntar una imagen o evidencia.",
    )

    class Meta:
        db_table = "FormQuestions"
        ordering = ["question_order"]

    def __str__(self):
        return f"{self.question[:50]}..."


class FormAnswers(models.Model):
    """Respuestas a las preguntas de un formulario para una orden de trabajo específica"""

    id = models.AutoField(primary_key=True)
    question = models.ForeignKey(
        FormQuestions,
        on_delete=models.CASCADE,
        help_text="Pregunta respondida",
        db_column="question_id",
    )
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        help_text="Orden de trabajo",
        db_column="work_order_id",
    )
    answer = models.TextField(
        blank=True, null=True, help_text="Respuesta a la pregunta"
    )
    area = models.CharField(
        max_length=100, blank=True, null=True, help_text="Área específica del trabajo"
    )
    comments = models.TextField(
        blank=True, null=True, help_text="Comentarios adicionales"
    )
    image = models.ImageField(
        upload_to="form_answers/",
        blank=True,
        null=True,
        help_text="Archivo de imagen de la respuesta",
    )

    class Meta:
        db_table = "FormAnswers"

    def __str__(self):
        return f"WO-{self.work_order.id}: {self.question.question[:30]}..."


class Roles(models.Model):
    id_rol_pk = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateField(null=True, blank=True)
    updated_at = models.DateField(null=True, blank=True)
    usr_created_at = models.CharField(max_length=65, null=True, blank=True)
    usr_updated_at = models.CharField(max_length=65, null=True, blank=True)
    permissions = models.ManyToManyField(
        "Permissions", blank=True, related_name="roles"
    )
    role_status = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "Roles"

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
        db_table = "Permissions"

    def __str__(self):
        return self.name if self.name else f"Permiso {self.id_permissions_pk}"
