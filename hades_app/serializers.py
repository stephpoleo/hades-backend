from rest_framework import serializers
from .models import Users, EDS, FormTemplate, WorkOrder, FormQuestions, FormAnswers


class UsersSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)  # Opcional
    eds_info = serializers.SerializerMethodField(read_only=True)  # Información completa de EDS
    
    class Meta:
        model = Users
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},  # Opcional
            'email': {'required': False}  # Email también opcional
        }
    
    def get_eds_info(self, obj):
        """Obtener información completa de la EDS asociada"""
        if obj.id_eds_fk:
            try:
                eds = EDS.objects.get(id_eds_pk=obj.id_eds_fk)
                return {
                    'id': eds.id_eds_pk,
                    'name': eds.name,
                    'plaza': eds.plaza,
                    'state': eds.state,
                    'municipality': eds.municipality,
                    'zip_code': eds.zip_code,
                    'plaza_status': eds.plaza_status
                }
            except EDS.DoesNotExist:
                return None
        return None
    
    def create(self, validated_data):
        """Crear usuario con contraseña encriptada"""
        password = validated_data.pop('password', None)
        user = Users.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
    def update(self, instance, validated_data):
        """Actualizar usuario, encriptando contraseña si se proporciona"""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class EDSSerializer(serializers.ModelSerializer):
    class Meta:
        model = EDS
        fields = '__all__'


class FormTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormTemplate
        fields = '__all__'


class FormQuestionsSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='id_form_template_fk.name', read_only=True)
    
    class Meta:
        model = FormQuestions
        fields = '__all__'


class WorkOrderSerializer(serializers.ModelSerializer):

    total_questions = serializers.SerializerMethodField(read_only=True)
    total_answers = serializers.SerializerMethodField(read_only=True)
    completion_status = serializers.SerializerMethodField(read_only=True)

    def get_total_questions(self, obj):
        return obj.form_template.questions.count() if obj.form_template else 0

    def get_total_answers(self, obj):
        return FormAnswers.objects.filter(work_order=obj).count()

    def get_completion_status(self, obj):
        total_q = self.get_total_questions(obj)
        total_a = self.get_total_answers(obj)
        if total_a == 0:
            return 'draft'
        elif total_a < total_q:
            return 'pending'
        elif total_a >= total_q and total_q > 0:
            return 'completed'
        return 'draft'


    form_template = FormTemplateSerializer(read_only=True)
    form_template_id = serializers.PrimaryKeyRelatedField(
        queryset=FormTemplate.objects.all(), source='form_template', write_only=True
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
        fields = '__all__'


class FormAnswersSerializer(serializers.ModelSerializer):
    question = FormQuestionsSerializer(read_only=True)
    question_id = serializers.PrimaryKeyRelatedField(
        queryset=FormQuestions.objects.all(), source='question', write_only=True, required=True
    )
    work_order = serializers.SerializerMethodField(read_only=True)
    work_order_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkOrder.objects.all(), source='work_order', write_only=True, required=True
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
            'id', 'question', 'question_id', 'work_order', 'work_order_id', 'work_order_name',
            'answer', 'area', 'comments', 'image'
        ]
        extra_kwargs = {
            'question': {'required': False},
            'work_order': {'required': False},
        }

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['question_id'] = instance.question.id if instance.question else None
        rep['work_order_id'] = instance.work_order.id if instance.work_order else None
        return rep
