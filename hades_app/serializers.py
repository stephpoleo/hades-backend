from rest_framework import serializers
from .models import Users, EDS, FormTemplate, WorkOrder, FormQuestions, FormAnswers


class UsersSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)  # Opcional
    
    class Meta:
        model = Users
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},  # Opcional
            'email': {'required': False}  # Email también opcional
        }
    
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
    template_name = serializers.CharField(source='id_form_template_fk.name', read_only=True)
    name = serializers.CharField(read_only=True)  # Propiedad calculada
    description = serializers.CharField(read_only=True)  # Propiedad calculada
    
    class Meta:
        model = WorkOrder
        fields = '__all__'


class FormAnswersSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='id_question_form_fk.question', read_only=True)
    work_order_name = serializers.CharField(source='work_order_id.name', read_only=True)
    
    class Meta:
        model = FormAnswers
        fields = '__all__'
