import logging
import uuid
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from google.cloud import storage
from google.cloud.storage import _signing

from rest_framework import serializers
from django.conf import settings
from django.urls import reverse
from .models import (
    Users,
    EDS,
    FormTemplate,
    WorkOrder,
    FormQuestions,
    FormAnswers,
    Roles,
    Permissions,
)

try:
    from google.cloud import storage
except ImportError:  # pragma: no cover
    storage = None


def _build_signed_url(image_field):
    """
    Genera una URL firmada temporal para un ImageField almacenado en GCS.
    Retorna None si no hay bucket o no se puede firmar.
    """
    if not image_field or not getattr(image_field, "name", None):
        return None
    # Primero intenta con el storage configurado (si firma automáticamente)
    try:
        candidate = image_field.storage.url(image_field.name)
        if candidate and "X-Goog-" in candidate:
            return candidate
    except Exception as exc:
        logging.getLogger("django").warning(
            "Signed URL via storage.url failed: %s", exc, exc_info=True
        )
        pass

    logger = logging.getLogger("django")
    bucket_name = getattr(settings, "GS_BUCKET_NAME", None)
    credentials = getattr(settings, "GS_CREDENTIALS", None)
    project_id = getattr(settings, "GS_PROJECT_ID", None)
    if not project_id and credentials is not None:
        project_id = getattr(credentials, "project_id", None)
    scopes = ["https://www.googleapis.com/auth/devstorage.read_only"]
    if credentials and hasattr(credentials, "with_scopes"):
        credentials = credentials.with_scopes(scopes)
    if not bucket_name or storage is None:
        return None
    try:
        client = (
            storage.Client(project=project_id, credentials=credentials)
            if project_id
            else storage.Client(credentials=credentials)
        )
    except Exception as exc:
        logger.error(
            "[SignedURL] No se pudo crear el cliente de GCS: %s", exc, exc_info=True
        )
        return None
    object_name = image_field.name
    blob = client.bucket(bucket_name).blob(object_name)
    try:
        try:
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=1),
                method="GET",
                credentials=credentials,
            )
        except TypeError:
            logger.warning(
                "[SignedURL] generate_signed_url no acepta credentials explícitos, reintentando sin parámetro"
            )
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=1),
                method="GET",
            )
    except Exception as exc:
        logger.error(
            "[SignedURL] Error firmando %s con blob.generate_signed_url: %s",
            object_name,
            exc,
            exc_info=True,
        )
        manual_url = None
        if credentials is not None:
            try:
                manual_url = _signing.generate_signed_url_v4(
                    credentials=credentials,
                    request_method="GET",
                    bucket_name=bucket_name,
                    blob_name=object_name,
                    expiration=timedelta(hours=1),
                )
                logger.error(
                    "[SignedURL] URL firmada generada vía fallback manual para %s",
                    object_name,
                )
            except Exception as manual_exc:
                logger.error(
                    "[SignedURL] Fallback manual también falló para %s: %s",
                    object_name,
                    manual_exc,
                    exc_info=True,
                )
        if manual_url:
            return manual_url
        return None


def _build_backend_attachment_url(instance, request):
    if not request:
        return None
    try:
        return request.build_absolute_uri(
            reverse("formanswers-attachment", args=[instance.pk])
        )
    except Exception:  # pragma: no cover
        return None


def _build_media_url(image_field):
    bucket = getattr(settings, "GS_BUCKET_NAME", None)
    if not bucket or not image_field or not getattr(image_field, "name", None):
        return None
    path = image_field.name.lstrip("/")
    path = "/".join(segment for segment in path.split("/") if segment)
    return f"https://storage.googleapis.com/{bucket}/{path}"


# Serializer para EDS
class EDSSerializer(serializers.ModelSerializer):
    # id_eds_pk es la clave_eds (cod_eds en erelis)
    class Meta:
        model = EDS
        fields = [
            "id_eds_pk",
            "name",
            "plaza",
            "state",
            "municipality",
            "zip_code",
            "plaza_status",
            "long_eds",
            "latit_eds",
        ]


# Importar serializers necesarios para referencias
## Eliminada importación circular innecesaria


class UsersSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)  # Opcional
    eds_info = serializers.SerializerMethodField(
        read_only=True
    )  # Información completa de EDS
    assigned_forms = serializers.SerializerMethodField(read_only=True)
    completed_forms = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Users
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True, "required": False},  # Opcional
            "email": {"required": False},  # Email también opcional
            # Excluir campos many-to-many heredados de PermissionsMixin
            "groups": {"read_only": True},
            "user_permissions": {"read_only": True},
        }

    def get_eds_info(self, obj):
        """Obtener informacion completa de la EDS asociada por clave_eds_fk (optimizado con batch)."""
        if not obj.clave_eds_fk:
            return None

        # Usar datos batch del contexto si están disponibles
        eds_map = self.context.get('eds_map', {})
        if eds_map:
            eds = eds_map.get(obj.clave_eds_fk)
            if eds:
                return EDSSerializer(eds).data
            return None

        # Fallback: query individual
        try:
            eds = EDS.objects.get(id_eds_pk=obj.clave_eds_fk)
            return EDSSerializer(eds).data
        except EDS.DoesNotExist:
            return None

    def get_assigned_forms(self, obj):
        """Total de work orders asignadas al usuario."""
        # Usar stats precalculados del contexto (optimización N+1)
        user_stats = self.context.get("user_stats", {})
        if user_stats:
            stat = user_stats.get(obj.id_usr_pk, {})
            return stat.get("assigned", 0)
        # Fallback: query directa (para detail view)
        return WorkOrder.objects.filter(user_id=obj.id_usr_pk).count()

    def get_completed_forms(self, obj):
        """Total de work orders completadas por el usuario.

        Una WorkOrder está completada cuando tiene respuestas >= preguntas del template.
        """
        # Usar stats precalculados del contexto (optimización N+1)
        user_stats = self.context.get("user_stats", {})
        if user_stats:
            stat = user_stats.get(obj.id_usr_pk, {})
            return stat.get("completed", 0)
        # Fallback: query directa (para detail view)
        completed = 0
        work_orders = WorkOrder.objects.filter(user_id=obj.id_usr_pk).select_related(
            "form_template"
        )
        for wo in work_orders:
            if wo.form_template:
                total_questions = wo.form_template.questions.count()
                total_answers = FormAnswers.objects.filter(work_order=wo).exclude(
                    answer__isnull=True
                ).exclude(answer__exact="").count()
                if total_questions > 0 and total_answers >= total_questions:
                    completed += 1
        return completed

    def create(self, validated_data):
        """Crear usuario con contraseña encriptada"""
        password = validated_data.pop("password", None)
        user = Users.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


# Serializers base primero
class FormQuestionsSerializer(serializers.ModelSerializer):
    form_template = serializers.PrimaryKeyRelatedField(read_only=True)
    form_template_id = serializers.PrimaryKeyRelatedField(
        queryset=FormTemplate.objects.all(),
        source="form_template",
        write_only=True,
    )

    class Meta:
        model = FormQuestions
        fields = [
            "id",
            "question",
            "type",
            "is_required",
            "question_order",
            "form_template",
            "form_template_id",
            "allow_comments",
            "allow_attachments",
            "expected_value",
        ]

    def create(self, validated_data):
        # Asegura que expected_value se guarde aunque sea null o string vacío
        expected_value = validated_data.get("expected_value", None)
        instance = FormQuestions.objects.create(**validated_data)
        if expected_value is not None:
            instance.expected_value = expected_value
            instance.save(update_fields=["expected_value"])
        return instance

    def update(self, instance, validated_data):
        # Asegura que expected_value se actualice correctamente
        expected_value = validated_data.get("expected_value", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if expected_value is not None:
            instance.expected_value = expected_value
        instance.save()
        return instance


class FormTemplateMinimalSerializer(serializers.ModelSerializer):
    """Serializer liviano para usar en listas de WorkOrder (sin campos calculados)."""

    class Meta:
        model = FormTemplate
        fields = ["id", "name", "description", "is_active", "is_persistent"]


class FormTemplateSerializer(serializers.ModelSerializer):
    questions = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    assignments_count = serializers.SerializerMethodField()
    completed_count = serializers.SerializerMethodField()
    assigned_users = serializers.SerializerMethodField()

    class Meta:
        model = FormTemplate
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
            "is_active",
            "is_persistent",
            "questions",
            "assignments_count",
            "completed_count",
            "assigned_users",
        ]

    def get_assignments_count(self, obj):
        """Cantidad de usuarios únicos asignados a este formulario."""
        return (
            WorkOrder.objects.filter(form_template=obj, user_id__isnull=False)
            .values("user_id")
            .distinct()
            .count()
        )

    def get_completed_count(self, obj):
        """Cantidad de work orders completadas para este formulario."""
        from django.db.models import Count, Q

        total_questions = obj.questions.count()
        if total_questions == 0:
            return 0

        # Query optimizada: anotar cada work order con conteo de respuestas
        return (
            WorkOrder.objects.filter(form_template=obj)
            .annotate(
                answers_count=Count(
                    "formanswers",
                    filter=Q(formanswers__answer__isnull=False)
                    & ~Q(formanswers__answer__exact=""),
                )
            )
            .filter(answers_count__gte=total_questions)
            .count()
        )

    def get_assigned_users(self, obj):
        """Lista de usuarios asignados con work_order_id para gestión."""
        work_orders = WorkOrder.objects.filter(form_template=obj).values(
            "id", "user_id", "clave_eds"
        )

        # Batch query de usuarios para evitar N+1
        user_ids = {wo["user_id"] for wo in work_orders if wo["user_id"]}
        users_map = {}
        if user_ids:
            users_map = {
                u.id_usr_pk: u for u in Users.objects.filter(id_usr_pk__in=user_ids)
            }

        result = []
        for wo in work_orders:
            user = users_map.get(wo["user_id"]) if wo["user_id"] else None
            result.append(
                {
                    "work_order_id": wo["id"],
                    "user_id": wo["user_id"],
                    "user_name": user.name if user else None,
                    "clave_eds": wo["clave_eds"],
                }
            )
        return result


# Ahora los serializers que los usan
class WorkOrderSerializer(serializers.ModelSerializer):
    form_template = FormTemplateSerializer()
    user = UsersSerializer(source="get_user", read_only=True)
    user_id = serializers.IntegerField(required=False, allow_null=True)  # Removed write_only to expose in GET responses
    eds_id = serializers.CharField(
        write_only=True, required=False, allow_null=True, allow_blank=True
    )
    total_questions = serializers.SerializerMethodField()
    total_answers = serializers.SerializerMethodField()
    completion_status = serializers.SerializerMethodField()
    completion_grade = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "date",
            "form_template",
            "form_template_id",
            "eds",
            "clave_eds",
            "user",
            "total_questions",
            "total_answers",
            "completion_status",
            "completion_grade",
            "start_date_time",
            "end_date_time",
            "work_area_id",
            "user_id",
            "eds_id",
            "answers",
        ]

    def get_total_questions(self, obj):
        return obj.form_template.questions.count() if obj.form_template else 0

    def get_total_answers(self, obj):
        return (
            FormAnswers.objects.filter(work_order=obj)
            .exclude(answer__isnull=True)
            .exclude(answer__exact="")
            .count()
        )

    def get_completion_status(self, obj):
        total_q = self.get_total_questions(obj)
        total_a = self.get_total_answers(obj)
        if total_a == 0:
            return "pending"
        if total_q > 0 and total_a < total_q:
            return "draft"
        if total_q > 0 and total_a >= total_q:
            return "completed"
        return "pending"

    def get_completion_grade(self, obj):
        """Calcula la calificación porcentual basada en las respuestas correctas."""

        if not obj.form_template:
            return None

        questions = list(obj.form_template.questions.all())
        total_questions = len(questions)
        if total_questions == 0:
            return None

        answers_by_question = {
            answer.question_id: answer
            for answer in FormAnswers.objects.filter(work_order=obj)
        }

        correct_answers = 0
        for question in questions:
            answer_obj = answers_by_question.get(question.id)
            if self._is_answer_correct(question, answer_obj):
                correct_answers += 1

        percentage = (correct_answers / total_questions) * 100
        return round(percentage, 2)

    def get_answers(self, obj):
        # Devuelve las respuestas por pregunta para esta orden de trabajo
        if not obj.form_template:
            return []

        answers = (
            FormAnswers.objects.filter(work_order=obj)
            .select_related("question", "work_order")
            .order_by("question_id", "-id")
        )

        serialized_answers = {}
        for answer in answers:
            if answer.question_id in serialized_answers:
                continue  # Already captured the latest entry for this question
            serialized_answers[answer.question_id] = FormAnswersSerializer(
                answer, context=self.context
            ).data

        result = []
        for question in obj.form_template.questions.all().order_by("question_order"):
            serialized = serialized_answers.get(question.id) or {}
            result.append(
                {
                    "question": question.id,
                    "question_text": question.question,
                    "type": question.type,
                    "allow_comments": question.allow_comments,
                    "allow_attachments": question.allow_attachments,
                    "answer": serialized.get("answer"),
                    "comments": serialized.get("comments"),
                    # Campos de imagen principal (retrocompatibilidad)
                    "image": serialized.get("image"),
                    "attachment": serialized.get("attachment"),
                    "has_attachment": serialized.get("has_attachment", False),
                    # Campos para múltiples imágenes
                    "image_2": serialized.get("image_2"),
                    "image_3": serialized.get("image_3"),
                    "images": serialized.get("images", []),
                }
            )
        return result

    @staticmethod
    def _is_answer_correct(question, answer_obj):
        if not answer_obj or answer_obj.answer in (None, ""):
            return False

        raw_value = answer_obj.answer

        expected = getattr(question, "expected_value", None)
        if expected not in (None, ""):
            return WorkOrderSerializer._compare_with_expected(
                question.type, expected, raw_value
            )

        if question.type == "boolean":
            # Consideramos "sí"/"si"/"true"/"1" como respuesta correcta
            if isinstance(raw_value, bool):
                return raw_value is True
            normalized = str(raw_value).strip().lower()
            return normalized in {"true", "1", "si", "sí", "yes"}

        if question.type == "percent":
            normalized = str(raw_value).strip().replace("%", "").replace(",", ".")
            try:
                value = Decimal(normalized)
            except (InvalidOperation, ValueError):
                return False
            return value == Decimal("100")

        # Para otros tipos se considera correcto si existe una respuesta
        return True

    @staticmethod
    def _compare_with_expected(qtype, expected_value, raw_value):
        """
        Compara la respuesta contra el expected_value según el tipo de pregunta.
        Si no se puede normalizar, se considera incorrecta.
        """

        if raw_value in (None, ""):
            return False

        if qtype == "boolean":

            def _to_bool(val):
                if isinstance(val, bool):
                    return val
                normalized = str(val).strip().lower()
                if normalized in {"true", "1", "si", "sí", "yes"}:
                    return True
                if normalized in {"false", "0", "no"}:
                    return False
                return None

            exp_bool = _to_bool(expected_value)
            ans_bool = _to_bool(raw_value)
            return (
                exp_bool is not None and ans_bool is not None and exp_bool == ans_bool
            )

        if qtype in {"number", "percent"}:

            def _to_decimal(val):
                try:
                    normalized = str(val).strip().replace("%", "").replace(",", ".")
                    return Decimal(normalized)
                except (InvalidOperation, ValueError):
                    return None

            exp_dec = _to_decimal(expected_value)
            ans_dec = _to_decimal(raw_value)
            return exp_dec is not None and ans_dec is not None and exp_dec >= ans_dec

        # Texto u otros tipos: comparar normalizado
        return str(raw_value).strip().lower() == str(expected_value).strip().lower()

    form_template = FormTemplateSerializer(read_only=True)
    form_template_id = serializers.PrimaryKeyRelatedField(
        queryset=FormTemplate.objects.all(), source="form_template", write_only=True
    )
    user = serializers.SerializerMethodField(read_only=True)
    eds = serializers.SerializerMethodField(read_only=True)

    def get_user(self, obj):
        try:
            if obj.user_id is None:
                return None
            user = Users.objects.get(id_usr_pk=obj.user_id)
            return UsersSerializer(user).data
        except Users.DoesNotExist:
            return None
        except Exception as e:
            logging.getLogger("django").warning(
                f"Error getting user for work_order {obj.id}: {e}"
            )
            return None

    def get_eds(self, obj):
        """Obtener informacion completa de la EDS por clave_eds o del usuario asignado"""
        try:
            clave_eds = obj.clave_eds

            # Fallback: si no hay clave_eds en el WorkOrder, usar la del usuario
            if not clave_eds and obj.user_id:
                try:
                    user = Users.objects.get(id_usr_pk=obj.user_id)
                    clave_eds = user.clave_eds_fk
                except Users.DoesNotExist:
                    pass

            if clave_eds:
                try:
                    eds = EDS.objects.get(id_eds_pk=clave_eds)
                    return EDSSerializer(eds).data
                except EDS.DoesNotExist:
                    return None
            return None
        except Exception as e:
            logging.getLogger("django").warning(
                f"Error getting EDS for work_order {obj.id}: {e}"
            )
            return None

    def validate(self, data):
        """Validar que end_date_time no sea anterior a start_date_time"""
        start = data.get('start_date_time') or (self.instance.start_date_time if self.instance else None)
        end = data.get('end_date_time')

        if start and end and end < start:
            raise serializers.ValidationError({
                "end_date_time": "La fecha/hora de fin no puede ser anterior a la de inicio"
            })

        return data

    def create(self, validated_data):
        """
        Ensure user_id is set either from payload or authenticated request.
        Avoids inserting NULL into the NOT NULL column.
        Also sets clave_eds from the user's EDS if not provided.
        """
        request = self.context.get("request")
        user_id = validated_data.get("user_id")

        if not user_id and request and getattr(request, "user", None):
            if request.user.is_authenticated:
                validated_data["user_id"] = getattr(request.user, "id_usr_pk", None)

        if not validated_data.get("user_id"):
            raise serializers.ValidationError(
                {"user_id": "user_id es requerido para la orden de trabajo."}
            )

        # Si no se proporciona clave_eds, usar la EDS del usuario asignado
        if not validated_data.get("clave_eds"):
            try:
                user = Users.objects.get(id_usr_pk=validated_data["user_id"])
                if user.clave_eds_fk:
                    validated_data["clave_eds"] = user.clave_eds_fk
            except Users.DoesNotExist:
                pass

        return super().create(validated_data)


class WorkOrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for WorkOrder list view.
    Excludes 'answers' field to avoid N+1 queries and timeout issues.

    Optimizado para usar:
    - Datos batch del contexto (users_map, eds_map)
    - Anotaciones del queryset (_answers_count, _total_questions)
    - FormTemplateMinimalSerializer (sin campos calculados)
    """
    form_template = FormTemplateMinimalSerializer(read_only=True)
    user = serializers.SerializerMethodField(read_only=True)
    eds = serializers.SerializerMethodField(read_only=True)
    total_questions = serializers.SerializerMethodField()
    total_answers = serializers.SerializerMethodField()
    completion_status = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "date",
            "form_template",
            "user",
            "user_id",
            "eds",
            "clave_eds",
            "total_questions",
            "total_answers",
            "completion_status",
            "start_date_time",
            "end_date_time",
        ]

    def get_user(self, obj):
        """Obtener usuario desde el batch map (evita N+1)."""
        if obj.user_id is None:
            return None

        # Usar datos batch del contexto si están disponibles
        users_map = self.context.get('users_map', {})
        if users_map:
            user = users_map.get(obj.user_id)
            if user:
                # Serializar sin contexto para evitar recursión
                return {
                    'id_usr_pk': user.id_usr_pk,
                    'name': user.name,
                    'email': user.email,
                    'role_name': user.role_name,
                    'clave_eds_fk': user.clave_eds_fk,
                }
            return None

        # Fallback: query individual (para detail views)
        try:
            user = Users.objects.get(id_usr_pk=obj.user_id)
            return {
                'id_usr_pk': user.id_usr_pk,
                'name': user.name,
                'email': user.email,
                'role_name': user.role_name,
                'clave_eds_fk': user.clave_eds_fk,
            }
        except Users.DoesNotExist:
            return None

    def get_eds(self, obj):
        """Obtener EDS desde el batch map (evita N+1) o del usuario asignado."""
        clave_eds = obj.clave_eds

        # Fallback: si no hay clave_eds en el WorkOrder, usar la del usuario
        if not clave_eds and obj.user_id:
            users_map = self.context.get('users_map', {})
            if users_map:
                user = users_map.get(obj.user_id)
                if user:
                    clave_eds = user.clave_eds_fk
            else:
                try:
                    user = Users.objects.get(id_usr_pk=obj.user_id)
                    clave_eds = user.clave_eds_fk
                except Users.DoesNotExist:
                    pass

        if not clave_eds:
            return None

        # Usar datos batch del contexto si están disponibles
        eds_map = self.context.get('eds_map', {})
        if eds_map:
            eds = eds_map.get(clave_eds)
            if eds:
                return {
                    'id_eds_pk': eds.id_eds_pk,
                    'name': eds.name,
                    'plaza': eds.plaza,
                    'state': eds.state,
                    'municipality': eds.municipality,
                }
            return None

        # Fallback: query individual
        try:
            eds = EDS.objects.get(id_eds_pk=clave_eds)
            return {
                'id_eds_pk': eds.id_eds_pk,
                'name': eds.name,
                'plaza': eds.plaza,
                'state': eds.state,
                'municipality': eds.municipality,
            }
        except EDS.DoesNotExist:
            return None

    def get_total_questions(self, obj):
        """Usar anotación si está disponible."""
        # Si viene anotado del queryset
        if hasattr(obj, '_total_questions'):
            return obj._total_questions or 0
        # Fallback
        return obj.form_template.questions.count() if obj.form_template else 0

    def get_total_answers(self, obj):
        """Usar anotación si está disponible."""
        # Si viene anotado del queryset
        if hasattr(obj, '_answers_count'):
            return obj._answers_count or 0
        # Fallback
        return (
            FormAnswers.objects.filter(work_order=obj)
            .exclude(answer__isnull=True)
            .exclude(answer__exact="")
            .count()
        )

    def get_completion_status(self, obj):
        """Calcular status usando anotaciones optimizadas."""
        total_q = self.get_total_questions(obj)
        total_a = self.get_total_answers(obj)
        if total_a == 0:
            return "pending"
        if total_q > 0 and total_a < total_q:
            return "draft"
        if total_q > 0 and total_a >= total_q:
            return "completed"
        return "pending"


class FormAnswersSerializer(serializers.ModelSerializer):
    def _upload_image_to_gcs(self, instance, image, logger, field_name="image"):
        """
        Sube una imagen a GCS y actualiza el campo correspondiente en la instancia.

        Args:
            instance: Instancia de FormAnswers
            image: Archivo de imagen a subir
            logger: Logger para registrar eventos
            field_name: Nombre del campo a actualizar (image, image_2, image_3)

        Returns:
            str: Path del archivo en GCS
        """
        question_id = getattr(instance, "question_id", None) or getattr(
            instance, "question", None
        )
        work_order_id = getattr(instance, "work_order_id", None) or getattr(
            instance, "work_order", None
        )
        question_id = (
            question_id.id
            if hasattr(question_id, "id")
            else question_id
            if question_id
            else "unknown"
        )
        work_order_id = (
            work_order_id.id
            if hasattr(work_order_id, "id")
            else work_order_id
            if work_order_id
            else "unknown"
        )
        base_name = getattr(image, "name", "attachment")
        # Incluir el field_name en el path para diferenciar las imágenes
        filename = (
            f"form_answers/wo_{work_order_id}/q_{question_id}/"
            f"{field_name}_{uuid.uuid4().hex}_{base_name}"
        )
        client = storage.Client(credentials=settings.GS_CREDENTIALS)
        bucket = client.bucket(settings.GS_BUCKET_NAME)
        blob = bucket.blob(filename)
        image.seek(0)
        blob.upload_from_file(
            image,
            content_type=getattr(image, "content_type", "application/octet-stream"),
        )
        setattr(instance, field_name, filename)
        instance.save(update_fields=[field_name])
        try:
            instance.refresh_from_db(fields=[field_name])
        except Exception:
            pass
        logger.info(
            "[FormAnswersSerializer] Imagen %s subida a GCS: %s", field_name, filename
        )
        return filename

    def create(self, validated_data):
        logger = logging.getLogger("django")
        # Extraer las 3 imágenes del validated_data
        image = validated_data.pop("image", None)
        image_2 = validated_data.pop("image_2", None)
        image_3 = validated_data.pop("image_3", None)
        logger.info(
            f"[FormAnswersSerializer.create] validated_data keys: {list(validated_data.keys())}, "
            f"image: {bool(image)}, image_2: {bool(image_2)}, image_3: {bool(image_3)}"
        )

        # Lógica para establecer clave_eds_fk
        # Si no se proporciona, usar la EDS del usuario asociado al work_order
        clave_eds = validated_data.get("clave_eds_fk")
        work_order = validated_data.get("work_order")

        if not clave_eds and work_order:
            # Obtener el usuario del work_order y usar su EDS por defecto
            try:
                user = Users.objects.get(id_usr_pk=work_order.user_id)
                if user.clave_eds_fk:
                    validated_data["clave_eds_fk"] = user.clave_eds_fk
                    logger.info(
                        f"[FormAnswersSerializer.create] Usando EDS del usuario: {user.clave_eds_fk}"
                    )
            except Users.DoesNotExist:
                logger.warning(
                    f"[FormAnswersSerializer.create] No se encontró usuario para work_order {work_order.id}"
                )

        instance = super(FormAnswersSerializer, self).create(validated_data)

        # Subir cada imagen que se haya recibido
        images_to_upload = [
            ("image", image),
            ("image_2", image_2),
            ("image_3", image_3),
        ]
        for field_name, img in images_to_upload:
            if img:
                try:
                    self._upload_image_to_gcs(instance, img, logger, field_name)
                except Exception as exc:
                    logger.error(
                        f"[FormAnswersSerializer.create] ERROR al subir {field_name} a GCS: {exc}",
                        exc_info=True,
                    )

        return instance

    def update(self, instance, validated_data):
        logger = logging.getLogger("django")
        # Extraer las 3 imágenes del validated_data
        image = validated_data.pop("image", None)
        image_2 = validated_data.pop("image_2", None)
        image_3 = validated_data.pop("image_3", None)

        instance = super(FormAnswersSerializer, self).update(instance, validated_data)

        # Subir cada imagen que se haya recibido
        images_to_upload = [
            ("image", image),
            ("image_2", image_2),
            ("image_3", image_3),
        ]
        for field_name, img in images_to_upload:
            if img:
                try:
                    self._upload_image_to_gcs(instance, img, logger, field_name)
                except Exception as exc:
                    logger.error(
                        f"[FormAnswersSerializer.update] ERROR al subir {field_name} a GCS: {exc}",
                        exc_info=True,
                    )

        return instance

    question = FormQuestionsSerializer(read_only=True)
    question_id = serializers.PrimaryKeyRelatedField(
        queryset=FormQuestions.objects.all(),
        source="question",
        write_only=True,
        required=True,
    )
    work_order = serializers.SerializerMethodField(read_only=True)
    work_order_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkOrder.objects.all(),
        source="work_order",
        write_only=True,
        required=True,
    )
    work_order_name = serializers.SerializerMethodField(read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    image_2 = serializers.ImageField(required=False, allow_null=True)
    image_3 = serializers.ImageField(required=False, allow_null=True)
    clave_eds_fk = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    eds_info = serializers.SerializerMethodField(read_only=True)

    def get_work_order(self, obj):
        return obj.work_order.id if obj.work_order else None

    def get_work_order_name(self, obj):
        return str(obj.work_order) if obj.work_order else None

    def get_eds_info(self, obj):
        """Obtener información completa de la EDS asociada a la respuesta"""
        if obj.clave_eds_fk:
            try:
                eds = EDS.objects.get(id_eds_pk=obj.clave_eds_fk)
                return EDSSerializer(eds).data
            except EDS.DoesNotExist:
                return None
            except Exception as e:
                # Handle case where EDS database is not available
                logging.getLogger("django").warning(
                    f"Error getting EDS info for answer {obj.id}: {e}"
                )
                return None
        return None

    class Meta:
        model = FormAnswers
        fields = [
            "id",
            "question",
            "question_id",
            "work_order",
            "work_order_id",
            "work_order_name",
            "answer",
            "area",
            "comments",
            "image",
            "image_2",
            "image_3",
            "clave_eds_fk",
            "eds_info",
        ]
        extra_kwargs = {
            "question": {"required": False},
            "work_order": {"required": False},
        }

    def _get_image_url(self, image_field, instance, logger):
        """
        Genera URL firmada para un campo de imagen.

        Args:
            image_field: Campo ImageField de la instancia
            instance: Instancia de FormAnswers
            logger: Logger para registrar eventos

        Returns:
            str or None: URL firmada de la imagen
        """
        if not image_field:
            return None

        attachment_url = None
        try:
            attachment_url = _build_signed_url(image_field)
        except Exception as exc:
            logger.exception("Error firmando URL de imagen: %s", exc)
            attachment_url = None

        if not attachment_url:
            attachment_url = _build_media_url(image_field)

        if not attachment_url:
            attachment_url = _build_backend_attachment_url(
                instance, self.context.get("request")
            )

        return attachment_url

    def to_representation(self, instance):
        logger = logging.getLogger("django")
        rep = super().to_representation(instance)
        rep["question_id"] = instance.question.id if instance.question else None
        rep["work_order_id"] = instance.work_order.id if instance.work_order else None

        # Generar URLs para las 3 imágenes
        image_url = self._get_image_url(instance.image, instance, logger)
        image_2_url = self._get_image_url(instance.image_2, instance, logger)
        image_3_url = self._get_image_url(instance.image_3, instance, logger)

        # Si no hay imagen principal, intentar buscar en GCS (fallback legacy)
        if not image_url and not instance.image:
            wo = getattr(instance, "work_order_id", None) or getattr(
                instance, "work_order", None
            )
            q = getattr(instance, "question_id", None) or getattr(
                instance, "question", None
            )
            wo_id = wo.id if hasattr(wo, "id") else wo
            q_id = q.id if hasattr(q, "id") else q
            bucket_name = getattr(settings, "GS_BUCKET_NAME", None)

            if bucket_name and storage is not None and wo_id and q_id:
                try:
                    gcs_client = storage.Client(
                        credentials=getattr(settings, "GS_CREDENTIALS", None)
                    )
                    bucket = gcs_client.bucket(bucket_name)
                    prefix = f"form_answers/wo_{wo_id}/q_{q_id}/"
                    blobs = list(bucket.list_blobs(prefix=prefix))

                    if blobs:
                        # Ordenar por fecha, más reciente primero
                        sorted_blobs = sorted(
                            blobs,
                            key=lambda b: b.updated or b.time_created,
                            reverse=True,
                        )

                        class FakeImage:
                            def __init__(self, name):
                                self.name = name
                                self.storage = bucket

                        # Asignar hasta 3 imágenes encontradas
                        for i, blob in enumerate(sorted_blobs[:3]):
                            fake_image = FakeImage(blob.name)
                            url = _build_signed_url(fake_image)
                            if not url:
                                url = _build_media_url(fake_image)
                            if i == 0:
                                image_url = url
                            elif i == 1:
                                image_2_url = url
                            elif i == 2:
                                image_3_url = url
                except Exception as exc:
                    logger.error(
                        f"[DEBUG-FA] Error buscando imágenes en GCS: {exc}", exc_info=True
                    )

        # Actualizar representación con URLs de las 3 imágenes
        rep["image"] = image_url
        rep["image_2"] = image_2_url
        rep["image_3"] = image_3_url

        # Mantener retrocompatibilidad con campos antiguos
        rep["attachment"] = image_url
        rep["has_attachment"] = bool(image_url or image_2_url or image_3_url)

        # Lista de todas las imágenes para facilitar iteración en frontend
        rep["images"] = [url for url in [image_url, image_2_url, image_3_url] if url]

        return rep


class PermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permissions
        fields = "__all__"


class RolesSerializer(serializers.ModelSerializer):
    permissions = PermissionsSerializer(many=True, read_only=True)
    permissions_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permissions.objects.all(),
        many=True,
        write_only=True,
        source="permissions",
        required=False,
    )

    class Meta:
        model = Roles
        fields = [
            "id_rol_pk",
            "name",
            "created_at",
            "updated_at",
            "usr_created_at",
            "usr_updated_at",
            "permissions",
            "permissions_ids",
            "role_status",
        ]
