from rest_framework import serializers
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


# Serializer para EDS
class EDSSerializer(serializers.ModelSerializer):
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
        """Obtener información completa de la EDS asociada"""
        if obj.id_eds_fk:
            try:
                eds = EDS.objects.get(id_eds_pk=obj.id_eds_fk)
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
        ]


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
    total_questions = serializers.SerializerMethodField()
    total_answers = serializers.SerializerMethodField()
    completion_status = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "date",
            "status",
            "form_template",
            "user",
            "total_questions",
            "total_answers",
            "completion_status",
            "start_date_time",
            "end_date_time",
            "work_area_id",
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
            return "draft"
        elif total_a < total_q:
            return "incomplete"
        elif total_a == total_q and total_q > 0:
            return "completed"
        return "unknown"

    def get_answers(self, obj):
        # Devuelve las respuestas por pregunta para esta orden de trabajo
        answers = FormAnswers.objects.filter(work_order=obj)
        result = []
        for question in obj.form_template.questions.all():
            answer_obj = answers.filter(question=question).first()
            result.append(
                {
                    "question": question.id,
                    "question_text": question.question,
                    "type": question.type,
                    "answer": answer_obj.answer if answer_obj else None,
                    "comments": answer_obj.comments if answer_obj else None,
                    "image": (
                        answer_obj.image.url
                        if answer_obj and answer_obj.image
                        else None
                    ),
                }
            )
        return result

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
        try:
            eds = EDS.objects.get(id_eds_pk=obj.eds_id)
            return EDSSerializer(eds).data
        except EDS.DoesNotExist:
            return None

    class Meta:
        model = WorkOrder
        fields = "__all__"


class FormAnswersSerializer(serializers.ModelSerializer):
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
        rep = super().to_representation(instance)
        rep["question_id"] = instance.question.id if instance.question else None
        rep["work_order_id"] = instance.work_order.id if instance.work_order else None
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
