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

    class Meta:
        model = Users
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True, "required": False},  # Opcional
            "email": {"required": False},  # Email también opcional
        }

    def get_eds_info(self, obj):
        """Obtener informacion completa de la EDS asociada por clave_eds_fk"""
        if obj.clave_eds_fk:
            try:
                # id_eds_pk es cod_eds en erelis = clave_eds
                eds = EDS.objects.get(id_eds_pk=obj.clave_eds_fk)
                return EDSSerializer(eds).data
            except EDS.DoesNotExist:
                return None
        return None

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


class FormTemplateSerializer(serializers.ModelSerializer):
    questions = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = FormTemplate
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
            "is_active",
            "questions",
        ]


# Ahora los serializers que los usan
class WorkOrderSerializer(serializers.ModelSerializer):
    form_template = FormTemplateSerializer()
    user = UsersSerializer(source="get_user", read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
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
        # Solo contar respuestas que no estén vacías ni nulas
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
        for question in obj.form_template.questions.all():
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
                    "image": serialized.get("image"),
                    "attachment": serialized.get("attachment"),
                    "has_attachment": serialized.get("has_attachment", False),
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
            user = Users.objects.get(id_usr_pk=obj.user_id)
            return UsersSerializer(user).data
        except Users.DoesNotExist:
            return None

    def get_eds(self, obj):
        """Obtener informacion completa de la EDS por clave_eds"""
        if obj.clave_eds:
            try:
                # id_eds_pk es cod_eds en erelis = clave_eds
                eds = EDS.objects.get(id_eds_pk=obj.clave_eds)
                return EDSSerializer(eds).data
            except EDS.DoesNotExist:
                return None
        return None

    def create(self, validated_data):
        """
        Ensure user_id is set either from payload or authenticated request.
        Avoids inserting NULL into the NOT NULL column.
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

        return super().create(validated_data)


class FormAnswersSerializer(serializers.ModelSerializer):
    def _upload_image_to_gcs(self, instance, image, logger):
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
        filename = (
            f"form_answers/wo_{work_order_id}/q_{question_id}/"
            f"{uuid.uuid4().hex}_{base_name}"
        )
        client = storage.Client(credentials=settings.GS_CREDENTIALS)
        bucket = client.bucket(settings.GS_BUCKET_NAME)
        blob = bucket.blob(filename)
        image.seek(0)
        blob.upload_from_file(
            image,
            content_type=getattr(image, "content_type", "application/octet-stream"),
        )
        instance.image = filename
        instance.save(update_fields=["image"])
        try:
            instance.refresh_from_db(fields=["image"])
        except Exception:
            pass
        logger.error(
            "[FormAnswersSerializer] Imagen subida manualmente a GCS: %s", filename
        )
        return filename

    def create(self, validated_data):
        logger = logging.getLogger("django")
        image = validated_data.pop("image", None)
        logger.error(
            f"[FormAnswersSerializer.create] validated_data keys: {list(validated_data.keys())}, image: {image}, type: {type(image)}"
        )
        instance = super(FormAnswersSerializer, self).create(validated_data)
        if image:
            try:
                self._upload_image_to_gcs(instance, image, logger)
            except Exception as exc:
                logger.error(
                    f"[FormAnswersSerializer.create] ERROR al subir imagen manualmente a GCS: {exc}",
                    exc_info=True,
                )
        else:
            logger.error(
                "[FormAnswersSerializer.create] No se recibió imagen para guardar."
            )
        return instance

    def update(self, instance, validated_data):
        image = validated_data.pop("image", None)
        instance = super(FormAnswersSerializer, self).update(instance, validated_data)
        if image:
            try:
                self._upload_image_to_gcs(instance, image, logging.getLogger("django"))
            except Exception as exc:
                logging.getLogger("django").error(
                    f"[FormAnswersSerializer.update] ERROR al subir imagen manualmente a GCS: {exc}",
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

    def get_work_order(self, obj):
        return obj.work_order.id if obj.work_order else None

    def get_work_order_name(self, obj):
        return str(obj.work_order) if obj.work_order else None

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
        ]
        extra_kwargs = {
            "question": {"required": False},
            "work_order": {"required": False},
        }

    def to_representation(self, instance):
        logger = logging.getLogger("django")
        rep = super().to_representation(instance)
        rep["question_id"] = instance.question.id if instance.question else None
        rep["work_order_id"] = instance.work_order.id if instance.work_order else None
        attachment_url = None
        logger.error(
            f"[DEBUG-FA] instance.id={getattr(instance, 'id', None)} image={getattr(instance, 'image', None)} image.name={getattr(getattr(instance, 'image', None), 'name', None)}"
        )
        if instance.image:
            try:
                attachment_url = _build_signed_url(instance.image)
                logger.error(f"[DEBUG-FA] _build_signed_url result: {attachment_url}")
            except Exception as exc:  # pragma: no cover
                logger.exception("Error firmando URL de imagen (FA): %s", exc)
                attachment_url = None
            if not attachment_url:
                attachment_url = _build_media_url(instance.image)
                logger.error(f"[DEBUG-FA] _build_media_url result: {attachment_url}")
                if attachment_url:
                    logger.info(
                        "[FormAnswersSerializer] URL pública usada para %s",
                        getattr(instance.image, "name", None),
                    )
            if not attachment_url:
                logger.error(
                    "[FormAnswersSerializer] Usando endpoint backend como fallback para imagen %s",
                    getattr(instance.image, "name", None),
                )
                attachment_url = _build_backend_attachment_url(
                    instance, self.context.get("request")
                )
                logger.error(
                    f"[DEBUG-FA] _build_backend_attachment_url result: {attachment_url}"
                )
        else:
            # Intentar inferir el path de la imagen desde GCS si sabemos work_order y question
            logger.error(
                "[DEBUG-FA] instance.image is None or empty, intentando buscar en GCS"
            )
            wo = getattr(instance, "work_order_id", None) or getattr(
                instance, "work_order", None
            )
            q = getattr(instance, "question_id", None) or getattr(
                instance, "question", None
            )
            wo_id = wo.id if hasattr(wo, "id") else wo
            q_id = q.id if hasattr(q, "id") else q
            bucket_name = getattr(settings, "GS_BUCKET_NAME", None)
            gcs_client = None
            if bucket_name and storage is not None and wo_id and q_id:
                try:
                    gcs_client = storage.Client(
                        credentials=getattr(settings, "GS_CREDENTIALS", None)
                    )
                    bucket = gcs_client.bucket(bucket_name)
                    prefix = f"form_answers/wo_{wo_id}/q_{q_id}/"
                    blobs = list(bucket.list_blobs(prefix=prefix))
                    logger.error(
                        f"[DEBUG-FA] blobs encontrados en {prefix}: {[b.name for b in blobs]}"
                    )
                    if blobs:
                        # Tomar el más reciente por updated o el primero
                        blob = sorted(
                            blobs,
                            key=lambda b: b.updated or b.time_created,
                            reverse=True,
                        )[0]

                        class FakeImage:
                            def __init__(self, name):
                                self.name = name
                                self.storage = bucket

                        fake_image = FakeImage(blob.name)
                        attachment_url = _build_signed_url(fake_image)
                        logger.error(
                            f"[DEBUG-FA] _build_signed_url (fake) result: {attachment_url}"
                        )
                        if not attachment_url:
                            attachment_url = _build_media_url(fake_image)
                            logger.error(
                                f"[DEBUG-FA] _build_media_url (fake) result: {attachment_url}"
                            )
                except Exception as exc:
                    logger.error(
                        f"[DEBUG-FA] Error buscando imagen en GCS: {exc}", exc_info=True
                    )
            rep["image"] = attachment_url
            rep["attachment"] = attachment_url
            rep["has_attachment"] = bool(attachment_url)
            return rep
        rep["image"] = attachment_url
        rep["attachment"] = attachment_url
        rep["has_attachment"] = bool(attachment_url)
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
