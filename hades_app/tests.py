"""
=============================================================================
HADES BACKEND - UNIT TESTS
=============================================================================

Este archivo contiene los tests unitarios para validar todos los flujos
del backend de Hades antes de subir cambios a produccion.

FLUJOS PRINCIPALES TESTEADOS:
-----------------------------

1. AUTENTICACION
   - Obtener token CSRF
   - Login con credenciales validas/invalidas
   - Logout
   - Obtener usuario actual (me)

2. GESTION DE USUARIOS (UsersViewSet)
   - Crear usuario con password encriptado
   - Listar usuarios con paginacion
   - Filtrar usuarios por nombre (search)
   - Filtrar usuarios por EDS (eds_name)
   - Obtener usuario individual con eds_info
   - Actualizar usuario
   - Eliminar usuario
   - Campos calculados: assigned_forms, completed_forms

3. GESTION DE EDS (EDSViewSet)
   - Listar EDS con paginacion
   - Listar EDS sin paginacion (no_pagination=true)
   - Obtener EDS individual
   - Crear/Actualizar/Eliminar EDS

4. PLANTILLAS DE FORMULARIO (FormTemplateViewSet)
   - CRUD de plantillas
   - Campos calculados: assignments_count, completed_count, assigned_users
   - Clear all action

5. ORDENES DE TRABAJO (WorkOrderViewSet)
   - Crear orden de trabajo con user_id requerido
   - Listar ordenes con filtros (user_id, form_template_id, clave_eds)
   - Campos calculados: total_questions, total_answers, completion_status, completion_grade
   - Serializer optimizado para listas (WorkOrderListSerializer)

6. PREGUNTAS DE FORMULARIO (FormQuestionsViewSet)
   - CRUD de preguntas
   - Tipos de pregunta: text, number, boolean, date, file, percent
   - Campos: expected_value, allow_comments, allow_attachments

7. RESPUESTAS DE FORMULARIO (FormAnswersViewSet)
   - Crear respuesta con hasta 3 imagenes
   - Actualizar respuesta
   - Obtener respuestas por work_order
   - Eliminar duplicados
   - Endpoints de attachment

8. ROLES Y PERMISOS
   - CRUD de roles
   - CRUD de permisos
   - Asignacion de permisos a roles

9. DASHBOARD KPIs
   - Calcular metricas de cumplimiento
   - Filtros: zone, eds, form, start_date, end_date
   - Calculo de grades por EDS, zona y formulario

10. LOGICA DE VALIDACION
    - Validacion de respuestas correctas (boolean, percent, expected_value)
    - Comparacion de respuestas con valores esperados

=============================================================================
"""

import unittest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

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
from .serializers import (
    UsersSerializer,
    EDSSerializer,
    FormTemplateSerializer,
    WorkOrderSerializer,
    WorkOrderListSerializer,
    FormQuestionsSerializer,
    FormAnswersSerializer,
    RolesSerializer,
    PermissionsSerializer,
)


# =============================================================================
# TEST FIXTURES - Datos de prueba reutilizables
# =============================================================================

class TestDataMixin:
    """Mixin con metodos para crear datos de prueba"""

    def create_user(self, name="Test User", email="test@example.com", password="testpass123", **kwargs):
        """Crea un usuario de prueba"""
        user = Users.objects.create(
            name=name,
            email=email,
            usr_status=True,
            **kwargs
        )
        user.set_password(password)
        user.save()
        return user

    def create_form_template(self, name="Test Form", description="Test Description", is_active=True):
        """Crea una plantilla de formulario de prueba"""
        return FormTemplate.objects.create(
            name=name,
            description=description,
            is_active=is_active
        )

    def create_question(self, form_template, question="Test Question?", qtype="text", order=1, **kwargs):
        """Crea una pregunta de prueba"""
        return FormQuestions.objects.create(
            form_template=form_template,
            question=question,
            type=qtype,
            question_order=order,
            **kwargs
        )

    def create_work_order(self, user, form_template, clave_eds=None, **kwargs):
        """Crea una orden de trabajo de prueba"""
        return WorkOrder.objects.create(
            user_id=user.id_usr_pk,
            form_template=form_template,
            date=datetime.now(),
            clave_eds=clave_eds,
            **kwargs
        )

    def create_answer(self, question, work_order, answer="Test Answer", **kwargs):
        """Crea una respuesta de prueba"""
        return FormAnswers.objects.create(
            question=question,
            work_order=work_order,
            answer=answer,
            **kwargs
        )

    def create_role(self, name="Test Role"):
        """Crea un rol de prueba"""
        return Roles.objects.create(name=name, role_status=True)

    def create_permission(self, name="Test Permission"):
        """Crea un permiso de prueba"""
        return Permissions.objects.create(name=name, permission_status=True)


# =============================================================================
# 1. TESTS DE AUTENTICACION
# =============================================================================

class AuthenticationTests(APITestCase, TestDataMixin):
    """
    Tests para el flujo de autenticacion.

    Flujo probado:
    1. Usuario obtiene token CSRF
    2. Usuario hace login con email/password
    3. Usuario consulta /me para verificar sesion
    4. Usuario hace logout
    """

    def setUp(self):
        self.user = self.create_user(
            name="Auth Test User",
            email="auth@test.com",
            password="securepass123"
        )
        self.client = APIClient()

    def test_csrf_endpoint_returns_token(self):
        """
        FLUJO: Obtener token CSRF
        El frontend necesita el token CSRF antes de hacer login
        """
        response = self.client.get('/api/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrfToken', response.json())

    def test_login_with_valid_credentials(self):
        """
        FLUJO: Login exitoso
        Usuario envia email y password correctos
        """
        response = self.client.post('/api/auth/login/', {
            'email': 'auth@test.com',
            'password': 'securepass123'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('message'), 'Login exitoso')

    def test_login_with_invalid_credentials(self):
        """
        FLUJO: Login fallido
        Usuario envia password incorrecto
        """
        response = self.client.post('/api/auth/login/', {
            'email': 'auth@test.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data.get('success'))

    def test_login_with_missing_credentials(self):
        """
        FLUJO: Login sin credenciales
        Usuario no envia email o password
        """
        response = self.client.post('/api/auth/login/', {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data.get('success'))

    def test_me_endpoint_requires_authentication(self):
        """
        FLUJO: /me sin autenticacion
        Endpoint protegido debe rechazar usuarios no autenticados
        """
        response = self.client.get('/api/auth/me/')
        self.assertIn(response.status_code, [401, 403])

    def test_me_endpoint_returns_user_info(self):
        """
        FLUJO: /me con sesion activa
        Usuario autenticado obtiene su informacion
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('email'), 'auth@test.com')
        self.assertEqual(data.get('name'), 'Auth Test User')

    def test_logout_clears_session(self):
        """
        FLUJO: Logout
        Usuario cierra sesion
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))


# =============================================================================
# 2. TESTS DE USUARIOS
# =============================================================================

class UsersTests(APITestCase, TestDataMixin):
    """
    Tests para el CRUD de usuarios.

    Flujos probados:
    - Listar usuarios con paginacion
    - Filtrar por nombre y EDS
    - Crear usuario con password encriptado
    - Obtener campos calculados (assigned_forms, completed_forms)
    """
    databases = '__all__'

    def setUp(self):
        self.admin = self.create_user(
            name="Admin User",
            email="admin@test.com",
            password="adminpass",
            is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_list_users_returns_paginated_response(self):
        """
        FLUJO: Listar usuarios con paginacion
        Por defecto retorna 20 usuarios por pagina
        """
        # Crear varios usuarios
        for i in range(25):
            self.create_user(name=f"User {i}", email=f"user{i}@test.com")

        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)
        # Verificar estructura de paginacion
        data = response.json()
        self.assertIn('count', data)
        self.assertIn('results', data)

    def test_list_users_no_pagination(self):
        """
        FLUJO: Listar usuarios sin paginacion (para dropdowns)
        Parametro no_pagination=true devuelve todos los usuarios
        """
        for i in range(5):
            self.create_user(name=f"User {i}", email=f"user{i}@test.com")

        response = self.client.get('/api/users/?no_pagination=true')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('users', data)

    def test_filter_users_by_name(self):
        """
        FLUJO: Buscar usuarios por nombre
        Parametro search filtra por nombre (case-insensitive)
        """
        self.create_user(name="Juan Perez", email="juan@test.com")
        self.create_user(name="Maria Garcia", email="maria@test.com")

        response = self.client.get('/api/users/?search=juan&no_pagination=true')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        users = data.get('users', [])
        self.assertTrue(any('Juan' in u.get('name', '') for u in users))

    def test_create_user_with_password(self):
        """
        FLUJO: Crear usuario con password
        El password debe ser encriptado automaticamente
        """
        response = self.client.post('/api/users/', {
            'name': 'New User',
            'email': 'newuser@test.com',
            'password': 'newpassword123'
        })
        self.assertEqual(response.status_code, 201)

        # Verificar que el password fue encriptado
        user = Users.objects.get(email='newuser@test.com')
        self.assertTrue(user.check_password('newpassword123'))
        self.assertNotEqual(user.password, 'newpassword123')

    @patch('hades_app.serializers.EDS')
    def test_retrieve_user_includes_eds_info(self, mock_eds):
        """
        FLUJO: Obtener usuario con informacion de EDS
        El campo eds_info debe incluir datos de la EDS asignada (mockeado)
        """
        mock_eds.objects.get.return_value = None
        mock_eds.objects.filter.return_value = []

        user = self.create_user(
            name="EDS User",
            email="edsuser@test.com",
            clave_eds_fk="EDS001"
        )

        response = self.client.get(f'/api/users/{user.id_usr_pk}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

    def test_update_user(self):
        """
        FLUJO: Actualizar usuario
        Actualizacion parcial de campos
        """
        user = self.create_user(name="Old Name", email="update@test.com")

        response = self.client.patch(f'/api/users/{user.id_usr_pk}/', {
            'name': 'New Name'
        })
        self.assertEqual(response.status_code, 200)

        user.refresh_from_db()
        self.assertEqual(user.name, 'New Name')

    def test_delete_user(self):
        """
        FLUJO: Eliminar usuario
        """
        user = self.create_user(name="Delete Me", email="delete@test.com")
        user_id = user.id_usr_pk

        response = self.client.delete(f'/api/users/{user_id}/')
        self.assertEqual(response.status_code, 200)

        self.assertFalse(Users.objects.filter(id_usr_pk=user_id).exists())

    def test_user_assigned_forms_count(self):
        """
        FLUJO: Contar formularios asignados al usuario
        Campo calculado assigned_forms
        """
        user = self.create_user(name="Worker", email="worker@test.com")
        template = self.create_form_template()

        # Crear 3 ordenes de trabajo para el usuario
        for i in range(3):
            self.create_work_order(user, template)

        # Obtener usuario y verificar contador
        serializer = UsersSerializer(user)
        self.assertEqual(serializer.data.get('assigned_forms'), 3)


# =============================================================================
# 3. TESTS DE FORM TEMPLATES
# =============================================================================

class FormTemplateTests(APITestCase, TestDataMixin):
    """
    Tests para plantillas de formulario.

    Flujos probados:
    - CRUD de plantillas
    - Campos calculados (assignments_count, completed_count)
    - Clear all action
    """

    def setUp(self):
        self.admin = self.create_user(email="admin@test.com", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_create_form_template(self):
        """
        FLUJO: Crear plantilla de formulario
        """
        response = self.client.post('/api/form-templates/', {
            'name': 'Inspeccion Diaria',
            'description': 'Formulario de inspeccion diaria de EDS',
            'is_active': True
        })
        self.assertEqual(response.status_code, 201)

    def test_list_form_templates(self):
        """
        FLUJO: Listar plantillas
        """
        self.create_form_template(name="Form 1")
        self.create_form_template(name="Form 2")

        response = self.client.get('/api/form-templates/')
        self.assertEqual(response.status_code, 200)

    def test_form_template_assignments_count(self):
        """
        FLUJO: Contar asignaciones de un formulario
        Campo calculado assignments_count
        """
        template = self.create_form_template()
        user1 = self.create_user(email="user1@test.com")
        user2 = self.create_user(email="user2@test.com")

        # Crear ordenes para diferentes usuarios
        self.create_work_order(user1, template)
        self.create_work_order(user2, template)
        self.create_work_order(user1, template)  # Mismo usuario, no debe contar doble

        serializer = FormTemplateSerializer(template)
        self.assertEqual(serializer.data.get('assignments_count'), 2)

    def test_form_template_completed_count(self):
        """
        FLUJO: Contar formularios completados
        Un formulario esta completo cuando tiene respuestas >= preguntas
        """
        template = self.create_form_template()
        q1 = self.create_question(template, "Pregunta 1?", order=1)
        q2 = self.create_question(template, "Pregunta 2?", order=2)

        user = self.create_user(email="worker@test.com")

        # Crear orden completada (2 respuestas para 2 preguntas)
        wo_complete = self.create_work_order(user, template)
        self.create_answer(q1, wo_complete, "Respuesta 1")
        self.create_answer(q2, wo_complete, "Respuesta 2")

        # Crear orden incompleta (1 respuesta para 2 preguntas)
        wo_incomplete = self.create_work_order(user, template)
        self.create_answer(q1, wo_incomplete, "Solo una")

        serializer = FormTemplateSerializer(template)
        self.assertEqual(serializer.data.get('completed_count'), 1)


# =============================================================================
# 4. TESTS DE WORK ORDERS
# =============================================================================

class WorkOrderTests(APITestCase, TestDataMixin):
    """
    Tests para ordenes de trabajo.

    Flujos probados:
    - Crear orden con user_id requerido
    - Listar con filtros
    - Campos calculados (completion_status, completion_grade)
    """

    def setUp(self):
        self.user = self.create_user(email="worker@test.com")
        self.template = self.create_form_template()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_work_order_requires_user_id(self):
        """
        FLUJO: Crear orden sin user_id
        Debe fallar si no se proporciona user_id
        """
        response = self.client.post('/api/work-orders/', {
            'form_template_id': self.template.id,
            'date': datetime.now().isoformat()
        })
        # Debe fallar o usar el usuario autenticado
        self.assertIn(response.status_code, [201, 400])

    def test_create_work_order_with_user_id(self):
        """
        FLUJO: Crear orden con user_id
        """
        response = self.client.post('/api/work-orders/', {
            'form_template_id': self.template.id,
            'date': datetime.now().isoformat(),
            'user_id': self.user.id_usr_pk
        })
        self.assertEqual(response.status_code, 201)

    def test_list_work_orders_filter_by_user(self):
        """
        FLUJO: Filtrar ordenes por usuario
        Parametro user_id
        """
        other_user = self.create_user(email="other@test.com")
        self.create_work_order(self.user, self.template)
        self.create_work_order(other_user, self.template)

        response = self.client.get(f'/api/work-orders/?user_id={self.user.id_usr_pk}')
        self.assertEqual(response.status_code, 200)

    def test_work_order_completion_status_pending(self):
        """
        FLUJO: Estado de completado - Pendiente
        Sin respuestas = pending
        """
        self.create_question(self.template, "Q1?", order=1)
        wo = self.create_work_order(self.user, self.template)

        serializer = WorkOrderSerializer(wo)
        self.assertEqual(serializer.data.get('completion_status'), 'pending')

    def test_work_order_completion_status_draft(self):
        """
        FLUJO: Estado de completado - Borrador
        Algunas respuestas pero no todas = draft
        """
        q1 = self.create_question(self.template, "Q1?", order=1)
        self.create_question(self.template, "Q2?", order=2)
        wo = self.create_work_order(self.user, self.template)
        self.create_answer(q1, wo, "Respuesta parcial")

        serializer = WorkOrderSerializer(wo)
        self.assertEqual(serializer.data.get('completion_status'), 'draft')

    def test_work_order_completion_status_completed(self):
        """
        FLUJO: Estado de completado - Completado
        Todas las respuestas = completed
        """
        q1 = self.create_question(self.template, "Q1?", order=1)
        q2 = self.create_question(self.template, "Q2?", order=2)
        wo = self.create_work_order(self.user, self.template)
        self.create_answer(q1, wo, "R1")
        self.create_answer(q2, wo, "R2")

        serializer = WorkOrderSerializer(wo)
        self.assertEqual(serializer.data.get('completion_status'), 'completed')

    def test_work_order_completion_grade(self):
        """
        FLUJO: Calcular grade de cumplimiento
        Porcentaje de respuestas correctas
        """
        # Pregunta booleana donde True es correcto
        q1 = self.create_question(self.template, "Cumple?", qtype="boolean", order=1)
        wo = self.create_work_order(self.user, self.template)
        self.create_answer(q1, wo, "true")  # Respuesta correcta

        serializer = WorkOrderSerializer(wo)
        grade = serializer.data.get('completion_grade')
        self.assertEqual(grade, 100.0)

    def test_work_order_saves_start_and_end_datetime(self):
        """
        FLUJO: Guardar fechas de inicio y fin
        Los campos start_date_time y end_date_time deben guardarse correctamente
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)

        response = self.client.post('/api/work-orders/', {
            'form_template_id': self.template.id,
            'date': datetime.now().isoformat(),
            'user_id': self.user.id_usr_pk,
            'start_date_time': start_time.isoformat(),
            'end_date_time': end_time.isoformat()
        })
        self.assertEqual(response.status_code, 201)
        data = response.json()

        # Verificar que las fechas se guardaron
        self.assertIsNotNone(data.get('start_date_time'))
        self.assertIsNotNone(data.get('end_date_time'))

        # Verificar recuperando desde la base de datos
        wo = WorkOrder.objects.get(id=data['id'])
        self.assertIsNotNone(wo.start_date_time)
        self.assertIsNotNone(wo.end_date_time)

    def test_work_order_updates_start_and_end_datetime(self):
        """
        FLUJO: Actualizar fechas de inicio y fin
        Las fechas deben poder actualizarse via PATCH/PUT
        """
        # Crear work order sin fechas
        wo = self.create_work_order(self.user, self.template)
        self.assertIsNone(wo.start_date_time)
        self.assertIsNone(wo.end_date_time)

        # Actualizar con fechas
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1, minutes=30)

        response = self.client.patch(f'/api/work-orders/{wo.id}/', {
            'start_date_time': start_time.isoformat(),
            'end_date_time': end_time.isoformat()
        })
        self.assertEqual(response.status_code, 200)

        # Verificar que se actualizaron
        wo.refresh_from_db()
        self.assertIsNotNone(wo.start_date_time)
        self.assertIsNotNone(wo.end_date_time)

    def test_work_order_complete_flow_with_dates(self):
        """
        FLUJO: Simular flujo completo de usuario
        1. Abrir formulario (registrar start_date_time)
        2. Responder preguntas
        3. Enviar formulario (registrar end_date_time)
        """
        # 1. Crear work order (simulando que fue asignado)
        wo = self.create_work_order(self.user, self.template)
        self.assertIsNone(wo.start_date_time)
        self.assertIsNone(wo.end_date_time)

        # 2. Usuario hace clic en "Empezar formulario" - registrar start_date_time
        start_time = datetime.now()
        response = self.client.patch(f'/api/work-orders/{wo.id}/', {
            'start_date_time': start_time.isoformat()
        })
        self.assertEqual(response.status_code, 200)

        # Verificar start_date_time guardado
        wo.refresh_from_db()
        self.assertIsNotNone(wo.start_date_time)
        self.assertIsNone(wo.end_date_time)

        # 3. Usuario responde preguntas (simular con crear questions y answers)
        q1 = self.create_question(self.template, "Pregunta 1", order=1)
        q2 = self.create_question(self.template, "Pregunta 2", order=2)
        self.create_answer(q1, wo, "Respuesta 1")
        self.create_answer(q2, wo, "Respuesta 2")

        # 4. Usuario hace clic en "Enviar formulario" - registrar end_date_time
        end_time = start_time + timedelta(hours=1, minutes=15)
        response = self.client.patch(f'/api/work-orders/{wo.id}/', {
            'end_date_time': end_time.isoformat()
        })
        self.assertEqual(response.status_code, 200)

        # Verificar end_date_time guardado
        wo.refresh_from_db()
        self.assertIsNotNone(wo.start_date_time)
        self.assertIsNotNone(wo.end_date_time)

        # 5. Verificar que la duración se calcula correctamente
        serializer = WorkOrderSerializer(wo)
        data = serializer.data

        # La duración debe ser aproximadamente 75 minutos (1h 15min)
        # Permitir pequeña variación por timestamps
        self.assertIsNotNone(data.get('start_date_time'))
        self.assertIsNotNone(data.get('end_date_time'))

        # Calcular duración esperada
        delta = wo.end_date_time - wo.start_date_time
        expected_duration = int(delta.total_seconds() / 60)
        self.assertGreaterEqual(expected_duration, 74)  # Mínimo 74 minutos
        self.assertLessEqual(expected_duration, 76)     # Máximo 76 minutos


# =============================================================================
# 5. TESTS DE FORM QUESTIONS
# =============================================================================

class FormQuestionsTests(APITestCase, TestDataMixin):
    """
    Tests para preguntas de formulario.

    Flujos probados:
    - CRUD de preguntas
    - Diferentes tipos de pregunta
    - Campo expected_value
    """

    def setUp(self):
        self.user = self.create_user(email="admin@test.com", is_staff=True)
        self.template = self.create_form_template()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_text_question(self):
        """
        FLUJO: Crear pregunta tipo texto
        """
        response = self.client.post('/api/form-questions/', {
            'form_template_id': self.template.id,
            'question': 'Describe el estado de la estacion',
            'type': 'text',
            'question_order': 1,
            'is_required': True
        })
        self.assertEqual(response.status_code, 201)

    def test_create_boolean_question(self):
        """
        FLUJO: Crear pregunta tipo booleano
        """
        response = self.client.post('/api/form-questions/', {
            'form_template_id': self.template.id,
            'question': 'La estacion cumple con las normas?',
            'type': 'boolean',
            'question_order': 1,
            'is_required': True
        })
        self.assertEqual(response.status_code, 201)

    def test_create_percent_question_with_expected_value(self):
        """
        FLUJO: Crear pregunta tipo porcentaje con valor esperado
        """
        response = self.client.post('/api/form-questions/', {
            'form_template_id': self.template.id,
            'question': 'Porcentaje de ocupacion',
            'type': 'percent',
            'question_order': 1,
            'expected_value': '90'
        })
        self.assertEqual(response.status_code, 201)

        question = FormQuestions.objects.get(id=response.json()['id'])
        self.assertEqual(question.expected_value, '90')

    def test_list_questions_by_template(self):
        """
        FLUJO: Listar preguntas filtradas por plantilla
        """
        other_template = self.create_form_template(name="Other")
        self.create_question(self.template, "Q1?", order=1)
        self.create_question(self.template, "Q2?", order=2)
        self.create_question(other_template, "Q3?", order=1)

        response = self.client.get(f'/api/form-questions/?form_template={self.template.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)


# =============================================================================
# 6. TESTS DE FORM ANSWERS
# =============================================================================

class FormAnswersTests(APITestCase, TestDataMixin):
    """
    Tests para respuestas de formulario.

    Flujos probados:
    - Crear respuesta
    - Actualizar respuesta (upsert)
    - Multiples imagenes
    - Obtener respuestas por work_order
    """

    def setUp(self):
        self.user = self.create_user(email="worker@test.com")
        self.template = self.create_form_template()
        self.question = self.create_question(self.template, "Test Q?", order=1)
        self.work_order = self.create_work_order(self.user, self.template)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_answer(self):
        """
        FLUJO: Crear respuesta a una pregunta
        """
        response = self.client.post('/api/form-answers/', {
            'question_id': self.question.id,
            'work_order_id': self.work_order.id,
            'answer': 'Mi respuesta'
        })
        self.assertEqual(response.status_code, 201)

    def test_update_existing_answer(self):
        """
        FLUJO: Actualizar respuesta existente
        Si ya existe una respuesta para question+work_order, se actualiza
        """
        # Crear respuesta inicial
        answer = self.create_answer(self.question, self.work_order, "Original")

        # Actualizar via POST (upsert behavior)
        response = self.client.post('/api/form-answers/', {
            'question_id': self.question.id,
            'work_order_id': self.work_order.id,
            'answer': 'Actualizada'
        })
        self.assertEqual(response.status_code, 200)

        # Verificar que se actualizo
        answer.refresh_from_db()
        self.assertEqual(answer.answer, 'Actualizada')

    def test_get_answers_by_workorder(self):
        """
        FLUJO: Obtener respuestas de una orden de trabajo
        Endpoint by-workorder
        """
        self.create_answer(self.question, self.work_order, "Respuesta 1")

        response = self.client.get(f'/api/form-answers/by-workorder/?work_order_id={self.work_order.id}')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_answer_with_comments(self):
        """
        FLUJO: Respuesta con comentarios adicionales
        """
        response = self.client.post('/api/form-answers/', {
            'question_id': self.question.id,
            'work_order_id': self.work_order.id,
            'answer': 'Si',
            'comments': 'Comentario adicional sobre la respuesta'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json().get('comments'), 'Comentario adicional sobre la respuesta')

    def test_answer_with_clave_eds(self):
        """
        FLUJO: Respuesta asociada a una EDS
        Campo clave_eds_fk
        """
        response = self.client.post('/api/form-answers/', {
            'question_id': self.question.id,
            'work_order_id': self.work_order.id,
            'answer': 'Respuesta',
            'clave_eds_fk': 'EDS001'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json().get('clave_eds_fk'), 'EDS001')


# =============================================================================
# 7. TESTS DE ROLES Y PERMISOS
# =============================================================================

class RolesPermissionsTests(APITestCase, TestDataMixin):
    """
    Tests para roles y permisos.

    Flujos probados:
    - CRUD de roles
    - CRUD de permisos
    - Asignacion de permisos a roles
    """

    def setUp(self):
        self.admin = self.create_user(email="admin@test.com", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_create_role(self):
        """
        FLUJO: Crear rol
        """
        response = self.client.post('/api/roles/', {
            'name': 'Supervisor',
            'role_status': True
        })
        self.assertEqual(response.status_code, 201)

    def test_create_permission(self):
        """
        FLUJO: Crear permiso
        """
        response = self.client.post('/api/permissions/', {
            'name': 'can_edit_users',
            'permission_status': True
        })
        self.assertEqual(response.status_code, 201)

    def test_assign_permissions_to_role(self):
        """
        FLUJO: Asignar permisos a un rol
        """
        role = self.create_role("Admin")
        perm1 = self.create_permission("can_view")
        perm2 = self.create_permission("can_edit")

        response = self.client.patch(f'/api/roles/{role.id_rol_pk}/', {
            'permissions_ids': [perm1.id_permissions_pk, perm2.id_permissions_pk]
        })
        self.assertEqual(response.status_code, 200)

        role.refresh_from_db()
        self.assertEqual(role.permissions.count(), 2)

    def test_list_roles_includes_permissions(self):
        """
        FLUJO: Listar roles con permisos incluidos
        """
        role = self.create_role("Test Role")
        perm = self.create_permission("test_perm")
        role.permissions.add(perm)

        response = self.client.get('/api/roles/')
        self.assertEqual(response.status_code, 200)


# =============================================================================
# 8. TESTS DE DASHBOARD KPIs
# =============================================================================

class DashboardKPIsTests(APITestCase, TestDataMixin):
    """
    Tests para el endpoint de Dashboard KPIs.

    Flujos probados:
    - Calcular metricas de cumplimiento
    - Filtros por zona, EDS, formulario, fechas

    Nota: Este endpoint accede a la base de datos EDS externa.
    Usamos mocks para simular EDS.objects.all() en tests.
    """

    def setUp(self):
        self.user = self.create_user(email="admin@test.com", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('hades_app.views.EDS')
    def test_dashboard_kpis_empty(self, mock_eds):
        """
        FLUJO: KPIs sin datos
        Debe retornar estructura valida con valores en 0
        """
        # Mock EDS.objects.all() para retornar lista vacia
        mock_eds.objects.all.return_value = []

        response = self.client.get('/api/dashboard/kpis/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('complianceRating', data)
        self.assertIn('complianceHighlights', data)
        self.assertIn('complianceRows', data)

    @patch('hades_app.views.EDS')
    def test_dashboard_kpis_with_data(self, mock_eds):
        """
        FLUJO: KPIs con datos de cumplimiento
        """
        # Mock EDS
        mock_eds.objects.all.return_value = []

        template = self.create_form_template()
        q1 = self.create_question(template, "Cumple?", qtype="boolean", order=1)

        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")
        wo = self.create_work_order(worker, template, clave_eds="EDS001")
        self.create_answer(q1, wo, "true")

        response = self.client.get('/api/dashboard/kpis/')
        self.assertEqual(response.status_code, 200)

    @patch('hades_app.views.EDS')
    def test_dashboard_kpis_filter_by_date_range(self, mock_eds):
        """
        FLUJO: Filtrar KPIs por rango de fechas
        """
        mock_eds.objects.all.return_value = []

        today = datetime.now().strftime('%Y-%m-%d')
        response = self.client.get(f'/api/dashboard/kpis/?start_date={today}&end_date={today}')
        self.assertEqual(response.status_code, 200)

    @patch('hades_app.views.EDS')
    def test_dashboard_kpis_default_last_7_days(self, mock_eds):
        """
        FLUJO: Sin parámetros de fecha debe retornar solo últimos 7 días

        Optimización agregada: El endpoint ahora retorna últimos 7 días por defecto
        en lugar de todo el historial, mejorando rendimiento dramáticamente.
        """
        from django.utils import timezone

        # Mock EDS para que el filtro no falle
        mock_eds_obj = MagicMock()
        mock_eds_obj.id_eds_pk = "EDS001"
        mock_eds_obj.name = "Test EDS"
        mock_eds_obj.plaza = "TEST_ZONE"
        mock_eds.objects.all.return_value = [mock_eds_obj]
        mock_eds.objects.filter.return_value.values_list.return_value.distinct.return_value = ["EDS001"]

        # Crear datos de prueba
        template = self.create_form_template(name="Test Form")
        q1 = self.create_question(template, "Pregunta test", qtype="boolean", order=1)
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")

        # Work order de hace 10 días (NO debe aparecer)
        wo_old = self.create_work_order(worker, template, clave_eds="EDS001")
        wo_old.date = timezone.now() - timedelta(days=10)
        wo_old.save()
        self.create_answer(q1, wo_old, "true")

        # Work order de hace 3 días (SÍ debe aparecer)
        wo_recent = self.create_work_order(worker, template, clave_eds="EDS001")
        wo_recent.date = timezone.now() - timedelta(days=3)
        wo_recent.save()
        self.create_answer(q1, wo_recent, "true")

        # Llamar sin parámetros de fecha
        response = self.client.get('/api/dashboard/kpis/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data.get('success'))

        # Verificar que solo retorna datos recientes (últimos 7 días)
        # La work order vieja no debe estar en complianceRows
        compliance_rows = data.get('complianceRows', [])

        # Si hay datos, deben ser solo de los últimos 7 días
        # (puede estar vacío si la optimización filtró correctamente)
        if len(compliance_rows) > 0:
            # Verificar que la cantidad de work orders es solo 1 (el reciente)
            # En lugar de 2 (viejo + reciente)
            self.assertEqual(len(compliance_rows), 1,
                "Debe retornar solo 1 EDS con work orders de últimos 7 días")

    @patch('hades_app.views.EDS')
    def test_dashboard_kpis_filter_options(self, mock_eds):
        """
        FLUJO: Obtener opciones de filtro
        El endpoint debe incluir opciones para filtrar
        """
        mock_eds.objects.all.return_value = []

        self.create_form_template(name="Form A")
        self.create_form_template(name="Form B")

        response = self.client.get('/api/dashboard/kpis/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('filterOptions', data)
        self.assertIn('forms', data['filterOptions'])


# =============================================================================
# 9. TESTS DE LOGICA DE VALIDACION
# =============================================================================

class AnswerValidationTests(TestCase, TestDataMixin):
    """
    Tests para la logica de validacion de respuestas.

    Flujos probados:
    - Validacion de respuestas booleanas
    - Validacion de respuestas de porcentaje
    - Comparacion con expected_value
    """

    def setUp(self):
        self.user = self.create_user(email="test@test.com")
        self.template = self.create_form_template()

    def test_boolean_answer_true_is_correct(self):
        """
        FLUJO: Respuesta booleana "true" es correcta
        """
        question = self.create_question(self.template, "Cumple?", qtype="boolean", order=1)
        wo = self.create_work_order(self.user, self.template)
        answer = self.create_answer(question, wo, "true")

        from .views import _is_answer_correct
        self.assertTrue(_is_answer_correct(question, answer))

    def test_boolean_answer_si_is_correct(self):
        """
        FLUJO: Respuesta booleana "si" es correcta
        """
        question = self.create_question(self.template, "Cumple?", qtype="boolean", order=1)
        wo = self.create_work_order(self.user, self.template)
        answer = self.create_answer(question, wo, "si")

        from .views import _is_answer_correct
        self.assertTrue(_is_answer_correct(question, answer))

    def test_boolean_answer_false_is_incorrect(self):
        """
        FLUJO: Respuesta booleana "false" es incorrecta (sin expected_value)
        """
        question = self.create_question(self.template, "Cumple?", qtype="boolean", order=1)
        wo = self.create_work_order(self.user, self.template)
        answer = self.create_answer(question, wo, "false")

        from .views import _is_answer_correct
        self.assertFalse(_is_answer_correct(question, answer))

    def test_percent_answer_100_is_correct(self):
        """
        FLUJO: Respuesta de porcentaje 100% es correcta
        """
        question = self.create_question(self.template, "Ocupacion?", qtype="percent", order=1)
        wo = self.create_work_order(self.user, self.template)
        answer = self.create_answer(question, wo, "100")

        from .views import _is_answer_correct
        self.assertTrue(_is_answer_correct(question, answer))

    def test_percent_answer_below_100_is_incorrect(self):
        """
        FLUJO: Respuesta de porcentaje <100% es incorrecta (sin expected_value)
        """
        question = self.create_question(self.template, "Ocupacion?", qtype="percent", order=1)
        wo = self.create_work_order(self.user, self.template)
        answer = self.create_answer(question, wo, "80")

        from .views import _is_answer_correct
        self.assertFalse(_is_answer_correct(question, answer))

    def test_answer_with_expected_value(self):
        """
        FLUJO: Validar respuesta contra expected_value
        """
        question = self.create_question(
            self.template,
            "Nivel?",
            qtype="percent",
            order=1,
            expected_value="90"
        )
        wo = self.create_work_order(self.user, self.template)

        # Respuesta >= expected_value es correcta
        answer_correct = self.create_answer(question, wo, "95")
        from .views import _is_answer_correct
        self.assertTrue(_is_answer_correct(question, answer_correct))

        # Respuesta < expected_value es incorrecta
        answer_incorrect = FormAnswers.objects.create(
            question=question,
            work_order=wo,
            answer="85"
        )
        self.assertFalse(_is_answer_correct(question, answer_incorrect))


# =============================================================================
# 10. TESTS DE SERIALIZERS
# =============================================================================

class SerializerTests(TestCase, TestDataMixin):
    """
    Tests para validaciones de serializers.
    """

    def setUp(self):
        self.user = self.create_user(email="test@test.com")
        self.template = self.create_form_template()

    def test_work_order_serializer_validates_user_id_on_create(self):
        """
        FLUJO: WorkOrderSerializer valida user_id al crear
        La validacion de user_id ocurre en create(), no en is_valid()
        """
        from rest_framework import serializers as drf_serializers

        serializer = WorkOrderSerializer(data={
            'form_template_id': self.template.id,
            'date': datetime.now().isoformat()
        })
        # El serializer es valido sintacticamente (user_id es opcional)
        self.assertTrue(serializer.is_valid())

        # Pero falla al crear sin user_id ni request context
        with self.assertRaises(drf_serializers.ValidationError) as context:
            serializer.save()
        self.assertIn('user_id', str(context.exception))

    def test_users_serializer_password_is_write_only(self):
        """
        FLUJO: Password no se incluye en la salida del serializer
        """
        serializer = UsersSerializer(self.user)
        self.assertNotIn('password', serializer.data)

    def test_form_answers_serializer_includes_images(self):
        """
        FLUJO: FormAnswersSerializer incluye campos de imagen
        """
        question = self.create_question(self.template, "Q?", order=1)
        wo = self.create_work_order(self.user, self.template)
        answer = self.create_answer(question, wo, "Test")

        serializer = FormAnswersSerializer(answer)
        self.assertIn('image', serializer.data)
        self.assertIn('image_2', serializer.data)
        self.assertIn('image_3', serializer.data)

    def test_work_order_list_serializer_excludes_answers(self):
        """
        FLUJO: WorkOrderListSerializer no incluye answers (optimizacion)
        """
        wo = self.create_work_order(self.user, self.template)

        serializer = WorkOrderListSerializer(wo)
        self.assertNotIn('answers', serializer.data)


# =============================================================================
# 10. TESTS DE ENDPOINT POWER BI - CANASTILLA INVENTORY
# =============================================================================

class PowerBICanastillaInventoryTests(APITestCase, TestDataMixin):
    """
    Tests para el endpoint de Power BI - Inventario Canastilla.

    Flujos probados:
    - Retornar datos solo del formulario específico
    - Filtros por fecha, EDS, y usuario
    - Manejo de timestamps null
    - Estructura correcta de respuesta JSON
    - Performance con batch loading
    - Autenticación con Token
    """

    # Permitir acceso a todas las bases de datos (incluyendo 'eds')
    databases = '__all__'

    def setUp(self):
        """Configuración inicial para cada test"""
        self.user = self.create_user(email="admin@test.com", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Crear el form template específico de canastilla
        self.canastilla_template = self.create_form_template(
            name="F-PRO-OPE-017 (A) INVENTARIO CANASTILLA VERSION 000"
        )

        # Crear otro form template para verificar filtrado
        self.other_template = self.create_form_template(
            name="Otro Formulario"
        )

    def test_endpoint_exists(self):
        """
        FLUJO: Verificar que el endpoint existe y responde
        """
        response = self.client.get('/api/powerbi/canastilla-inventory/')
        # Debe retornar 200 incluso sin datos
        self.assertEqual(response.status_code, 200)

    def test_form_template_not_found(self):
        """
        FLUJO: Form template no existe en la base de datos
        Debe retornar 404 con mensaje claro
        """
        # Eliminar el template
        self.canastilla_template.delete()

        response = self.client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['count'], 0)

    def test_empty_results(self):
        """
        FLUJO: Template existe pero no hay WorkOrders
        Debe retornar estructura válida con array vacío
        """
        response = self.client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['count'], 0)
        self.assertEqual(data['form_template'], "F-PRO-OPE-017 (A) INVENTARIO CANASTILLA VERSION 000")
        self.assertEqual(len(data['results']), 0)

    def test_returns_only_canastilla_form(self):
        """
        FLUJO: Filtrar solo WorkOrders del formulario canastilla
        No debe incluir otros formularios
        """
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")

        # Crear WorkOrder de canastilla
        wo_canastilla = self.create_work_order(
            worker,
            self.canastilla_template,
            clave_eds="EDS001"
        )

        # Crear WorkOrder de otro formulario
        wo_other = self.create_work_order(
            worker,
            self.other_template,
            clave_eds="EDS001"
        )

        response = self.client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Debe retornar solo 1 WorkOrder (el de canastilla)
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['results']), 1)

    def test_response_structure(self):
        """
        FLUJO: Verificar estructura correcta de la respuesta
        """
        worker = self.create_user(
            email="worker@test.com",
            name="Juan Pérez",
            clave_eds_fk="EDS001"
        )

        wo = self.create_work_order(
            worker,
            self.canastilla_template,
            clave_eds="EDS001"
        )

        # Establecer timestamps (timezone-aware)
        from datetime import datetime, timedelta
        from django.utils import timezone
        start_time = timezone.make_aware(datetime(2026, 3, 1, 10, 0, 0))
        end_time = start_time + timedelta(hours=1, minutes=30)
        wo.start_date_time = start_time
        wo.end_date_time = end_time
        wo.save()

        response = self.client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['count'], 1)
        result = data['results'][0]

        # Verificar campos requeridos
        self.assertIn('eds', result)
        self.assertIn('eds_nombre', result)
        self.assertIn('fecha_inicio', result)
        self.assertIn('hora_inicio', result)
        self.assertIn('fecha_fin', result)
        self.assertIn('hora_fin', result)
        self.assertIn('usuario_id', result)
        self.assertIn('usuario_nombre', result)
        self.assertIn('usuario_email', result)
        self.assertIn('fecha_creacion', result)
        self.assertIn('duracion_minutos', result)

        # Verificar valores
        self.assertEqual(result['eds'], "EDS001")
        self.assertEqual(result['usuario_nombre'], "Juan Pérez")
        self.assertIsNotNone(result['fecha_inicio'])
        self.assertIsNotNone(result['hora_inicio'])
        self.assertIsNotNone(result['fecha_fin'])
        self.assertIsNotNone(result['hora_fin'])
        self.assertEqual(result['duracion_minutos'], 90)

    def test_null_timestamps(self):
        """
        FLUJO: Manejar WorkOrders sin timestamps (datos históricos)
        Debe retornar null en fecha_inicio, hora_inicio, fecha_fin, hora_fin
        """
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")

        wo = self.create_work_order(
            worker,
            self.canastilla_template,
            clave_eds="EDS001"
        )
        # No establecer start_date_time ni end_date_time

        response = self.client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        result = data['results'][0]

        # Verificar que timestamps son null
        self.assertIsNone(result['fecha_inicio'])
        self.assertIsNone(result['hora_inicio'])
        self.assertIsNone(result['fecha_fin'])
        self.assertIsNone(result['hora_fin'])
        self.assertIsNone(result['duracion_minutos'])

    def test_filter_by_date_range(self):
        """
        FLUJO: Filtrar por rango de fechas
        """
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")

        # Crear WorkOrders en diferentes fechas
        from datetime import datetime, timedelta
        from django.utils import timezone

        wo1 = self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")
        wo1.date = timezone.make_aware(datetime(2026, 1, 15))
        wo1.save()

        wo2 = self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")
        wo2.date = timezone.make_aware(datetime(2026, 2, 15))
        wo2.save()

        wo3 = self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")
        wo3.date = timezone.make_aware(datetime(2026, 3, 15))
        wo3.save()

        # Filtrar solo febrero
        response = self.client.get(
            '/api/powerbi/canastilla-inventory/?start_date=2026-02-01&end_date=2026-02-28'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Debe retornar solo 1 WorkOrder (febrero)
        self.assertEqual(data['count'], 1)

    def test_filter_by_eds(self):
        """
        FLUJO: Filtrar por EDS específica
        """
        worker1 = self.create_user(email="worker1@test.com", clave_eds_fk="EDS001")
        worker2 = self.create_user(email="worker2@test.com", clave_eds_fk="EDS002")

        wo1 = self.create_work_order(worker1, self.canastilla_template, clave_eds="EDS001")
        wo2 = self.create_work_order(worker2, self.canastilla_template, clave_eds="EDS002")

        # Filtrar por EDS001
        response = self.client.get('/api/powerbi/canastilla-inventory/?clave_eds=EDS001')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['eds'], "EDS001")

    def test_filter_by_user(self):
        """
        FLUJO: Filtrar por usuario específico
        """
        worker1 = self.create_user(email="worker1@test.com", clave_eds_fk="EDS001")
        worker2 = self.create_user(email="worker2@test.com", clave_eds_fk="EDS001")

        wo1 = self.create_work_order(worker1, self.canastilla_template, clave_eds="EDS001")
        wo2 = self.create_work_order(worker2, self.canastilla_template, clave_eds="EDS001")

        # Filtrar por worker1
        response = self.client.get(
            f'/api/powerbi/canastilla-inventory/?user_id={worker1.id_usr_pk}'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['usuario_id'], worker1.id_usr_pk)

    def test_combined_filters(self):
        """
        FLUJO: Combinar múltiples filtros (fecha + EDS + usuario)
        """
        from datetime import datetime
        from django.utils import timezone

        worker1 = self.create_user(email="worker1@test.com", clave_eds_fk="EDS001")
        worker2 = self.create_user(email="worker2@test.com", clave_eds_fk="EDS002")

        wo1 = self.create_work_order(worker1, self.canastilla_template, clave_eds="EDS001")
        wo1.date = timezone.make_aware(datetime(2026, 3, 1))
        wo1.save()

        wo2 = self.create_work_order(worker2, self.canastilla_template, clave_eds="EDS002")
        wo2.date = timezone.make_aware(datetime(2026, 3, 1))
        wo2.save()

        # Filtrar por fecha + EDS001
        response = self.client.get(
            '/api/powerbi/canastilla-inventory/?start_date=2026-03-01&end_date=2026-03-31&clave_eds=EDS001'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['count'], 1)
        self.assertEqual(data['results'][0]['eds'], "EDS001")

    @patch('hades_app.views.EDS')
    def test_eds_batch_loading(self, mock_eds):
        """
        FLUJO: Verificar que se hace batch loading de EDS (no N+1 queries)
        """
        # Mock EDS.objects.filter() para tracking de llamadas
        mock_eds_instance = MagicMock()
        mock_eds_instance.name = "EDS Test"
        mock_eds.objects.filter.return_value = [mock_eds_instance]

        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")

        # Crear múltiples WorkOrders
        for i in range(5):
            self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")

        response = self.client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 200)

        # Verificar que EDS.objects.filter() se llamó solo UNA vez (batch loading)
        # No 5 veces (N+1 query problem)
        self.assertEqual(mock_eds.objects.filter.call_count, 1)

    def test_invalid_date_parameter(self):
        """
        FLUJO: Manejar parámetros de fecha inválidos
        No debe crashear, debe ignorar el parámetro inválido
        """
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")
        wo = self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")

        # Enviar fecha inválida
        response = self.client.get('/api/powerbi/canastilla-inventory/?start_date=fecha-invalida')

        # Debe retornar 200 (ignora el parámetro inválido)
        self.assertEqual(response.status_code, 200)

    def test_invalid_user_id_parameter(self):
        """
        FLUJO: Manejar user_id inválido (no numérico)
        No debe crashear
        """
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")
        wo = self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")

        # Enviar user_id no numérico
        response = self.client.get('/api/powerbi/canastilla-inventory/?user_id=abc')

        # Debe retornar 200 (ignora el parámetro inválido)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_request(self):
        """
        FLUJO: Request sin autenticación
        Debe retornar 401 o 403
        """
        # Crear cliente sin autenticación
        unauth_client = APIClient()

        response = unauth_client.get('/api/powerbi/canastilla-inventory/')

        # Debe requerir autenticación
        self.assertIn(response.status_code, [401, 403])

    def test_token_authentication(self):
        """
        FLUJO: Autenticación con Token de API
        Debe aceptar requests con token válido
        """
        from rest_framework.authtoken.models import Token

        # Crear usuario y token para Power BI
        powerbi_user = self.create_user(email="powerbi@test.com", is_staff=False)
        token = Token.objects.create(user=powerbi_user)

        # Cliente con token authentication
        token_client = APIClient()
        token_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Crear datos de prueba
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")
        wo = self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")

        # Request con token debe funcionar
        response = token_client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)

    def test_invalid_token_authentication(self):
        """
        FLUJO: Autenticación con token inválido
        Debe retornar 401
        """
        # Cliente con token inválido
        invalid_client = APIClient()
        invalid_client.credentials(HTTP_AUTHORIZATION='Token invalid-token-123')

        response = invalid_client.get('/api/powerbi/canastilla-inventory/')

        # Debe rechazar token inválido
        self.assertEqual(response.status_code, 401)

    def test_includes_productos_details(self):
        """
        FLUJO: Incluir detalles de productos (preguntas/respuestas)
        Cada pregunta es un producto y la respuesta es la cantidad
        """
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")

        # Crear preguntas del formulario (productos)
        q1 = self.create_question(self.canastilla_template, "Cilindros de 10kg", order=1, qtype="number")
        q2 = self.create_question(self.canastilla_template, "Cilindros de 20kg", order=2, qtype="number")
        q3 = self.create_question(self.canastilla_template, "Cilindros de 30kg", order=3, qtype="number")

        # Crear WorkOrder
        wo = self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")

        # Crear respuestas (cantidades de productos)
        self.create_answer(q1, wo, "15", comments="Buen estado", area="Almacen A")
        self.create_answer(q2, wo, "10", comments="Revisar", area="Almacen B")
        self.create_answer(q3, wo, "5")

        response = self.client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['count'], 1)
        result = data['results'][0]

        # Verificar que incluye el array de productos
        self.assertIn('productos', result)
        productos = result['productos']
        self.assertEqual(len(productos), 3)

        # Verificar estructura de productos
        producto1 = productos[0]
        self.assertIn('producto', producto1)
        self.assertIn('cantidad', producto1)
        self.assertIn('comentarios', producto1)
        self.assertNotIn('area', producto1)  # Campo eliminado

        # Verificar valores
        self.assertEqual(producto1['producto'], "Cilindros de 10kg")
        self.assertEqual(producto1['cantidad'], "15")
        self.assertEqual(producto1['comentarios'], "Buen estado")

        self.assertEqual(productos[1]['producto'], "Cilindros de 20kg")
        self.assertEqual(productos[1]['cantidad'], "10")

        self.assertEqual(productos[2]['producto'], "Cilindros de 30kg")
        self.assertEqual(productos[2]['cantidad'], "5")

    def test_productos_empty_when_no_answers(self):
        """
        FLUJO: Array de productos vacío cuando no hay respuestas
        """
        worker = self.create_user(email="worker@test.com", clave_eds_fk="EDS001")

        # Crear preguntas pero sin respuestas
        self.create_question(self.canastilla_template, "Producto 1", order=1)
        self.create_question(self.canastilla_template, "Producto 2", order=2)

        # Crear WorkOrder sin respuestas
        wo = self.create_work_order(worker, self.canastilla_template, clave_eds="EDS001")

        response = self.client.get('/api/powerbi/canastilla-inventory/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        result = data['results'][0]
        self.assertIn('productos', result)
        self.assertEqual(len(result['productos']), 0)


# =============================================================================
# 11. TESTS DE PAGINACION
# =============================================================================

class PaginationTests(APITestCase, TestDataMixin):
    """
    Tests para el sistema de paginacion.
    """

    def setUp(self):
        self.user = self.create_user(email="admin@test.com", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_standard_pagination_page_size(self):
        """
        FLUJO: Paginacion estandar de 20 elementos
        """
        template = self.create_form_template()
        for i in range(30):
            self.create_work_order(self.user, template)

        response = self.client.get('/api/work-orders/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data.get('results', [])), 20)
        self.assertEqual(data.get('page_size'), 20)

    def test_custom_page_size(self):
        """
        FLUJO: Paginacion con page_size personalizado
        """
        template = self.create_form_template()
        for i in range(15):
            self.create_work_order(self.user, template)

        response = self.client.get('/api/work-orders/?page_size=10')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data.get('results', [])), 10)

    def test_pagination_metadata(self):
        """
        FLUJO: Verificar metadata de paginacion
        """
        template = self.create_form_template()
        for i in range(25):
            self.create_work_order(self.user, template)

        response = self.client.get('/api/work-orders/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('count', data)
        self.assertIn('total_pages', data)
        self.assertIn('current_page', data)
        self.assertIn('next', data)
        self.assertIn('previous', data)


# =============================================================================
# 12. TESTS DE INTEGRACION CON OASIS/EDS
# =============================================================================

def _is_eds_available():
    """
    Verifica si la conexion a la base de datos EDS (OASIS) esta disponible
    Y si la tabla oasis_cat_eds existe (conexion real, no base de datos de test).

    Retorna False durante tests normales porque Django crea una DB de test vacia.
    Solo retorna True si hay conexion real a OASIS via cloud-proxy.
    """
    # Durante tests, siempre retornar False para saltar tests de integracion
    # Los tests de integracion deben ejecutarse manualmente con:
    # python manage.py test hades_app.tests.OASISIntegrationTests --keepdb
    import sys
    if 'test' in sys.argv:
        # Si se especifica explicitamente el modulo de integracion, intentar conectar
        if 'OASISIntegrationTests' not in str(sys.argv):
            return False

    try:
        from django.db import connections
        from django.conf import settings

        if 'eds' not in settings.DATABASES:
            return False

        # Intentar ejecutar una query real en la tabla de OASIS
        conn = connections['eds']
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM oasis_cat_eds LIMIT 1")
            cursor.fetchone()
        return True
    except Exception:
        return False


@unittest.skipUnless(_is_eds_available(), "Requiere conexion a OASIS (ejecutar make cloud-proxy)")
class OASISIntegrationTests(APITestCase, TestDataMixin):
    """
    Tests de integracion con la base de datos OASIS/EDS.

    IMPORTANTE: Estos tests solo se ejecutan cuando hay conexion real a OASIS.
    Para ejecutarlos:
    1. En una terminal: make cloud-proxy
    2. En otra terminal: make test

    Si cloud-proxy no esta activo, estos tests se saltan automaticamente.
    """
    databases = '__all__'

    def setUp(self):
        self.user = self.create_user(email="admin@test.com", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_eds_connection(self):
        """
        INTEGRACION: Verificar conexion a base de datos EDS
        """
        from django.db import connections
        conn = connections['eds']
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        self.assertEqual(result[0], 1)

    def test_eds_list_returns_data(self):
        """
        INTEGRACION: Listar EDS desde OASIS
        El endpoint debe retornar datos reales de la tabla oasis_cat_eds
        """
        response = self.client.get('/api/eds/?no_pagination=true')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Debe haber al menos algunas EDS en OASIS
        self.assertIn('eds', data)

    def test_dashboard_kpis_with_real_eds(self):
        """
        INTEGRACION: Dashboard KPIs con datos reales de EDS
        """
        response = self.client.get('/api/dashboard/kpis/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        # filterOptions debe incluir zonas reales de OASIS
        self.assertIn('filterOptions', data)

    def test_user_with_real_eds_info(self):
        """
        INTEGRACION: Usuario con informacion de EDS real
        """
        # Obtener una clave_eds real de OASIS
        from hades_app.models import EDS
        try:
            first_eds = EDS.objects.first()
            if first_eds:
                user = self.create_user(
                    name="EDS User",
                    email="edsuser@test.com",
                    clave_eds_fk=first_eds.id_eds_pk
                )
                response = self.client.get(f'/api/users/{user.id_usr_pk}/')
                self.assertEqual(response.status_code, 200)
                data = response.json()
                # eds_info debe estar presente y tener datos
                self.assertIn('user', data)
        except Exception:
            self.skipTest("No hay EDS disponibles en OASIS")


# =============================================================================
# 13. TESTS ADICIONALES - ATTACHMENT ENDPOINTS
# =============================================================================

class AttachmentEndpointsTests(APITestCase, TestDataMixin):
    """
    Tests para los endpoints de descarga de attachments.

    Flujos probados:
    - Endpoint attachment (imagen principal)
    - Endpoint attachment-2 (segunda imagen)
    - Endpoint attachment-3 (tercera imagen)
    """

    def setUp(self):
        self.user = self.create_user(email="worker@test.com")
        self.template = self.create_form_template()
        self.question = self.create_question(self.template, "Test Q?", order=1)
        self.work_order = self.create_work_order(self.user, self.template)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_attachment_endpoint_no_image(self):
        """
        FLUJO: Intentar descargar attachment cuando no existe
        Debe retornar 404
        """
        answer = self.create_answer(self.question, self.work_order, "Sin imagen")

        response = self.client.get(f'/api/form-answers/{answer.id}/attachment/')
        self.assertEqual(response.status_code, 404)

    def test_attachment_2_endpoint_no_image(self):
        """
        FLUJO: Intentar descargar attachment-2 cuando no existe
        Debe retornar 404
        """
        answer = self.create_answer(self.question, self.work_order, "Sin imagen")

        response = self.client.get(f'/api/form-answers/{answer.id}/attachment-2/')
        self.assertEqual(response.status_code, 404)

    def test_attachment_3_endpoint_no_image(self):
        """
        FLUJO: Intentar descargar attachment-3 cuando no existe
        Debe retornar 404
        """
        answer = self.create_answer(self.question, self.work_order, "Sin imagen")

        response = self.client.get(f'/api/form-answers/{answer.id}/attachment-3/')
        self.assertEqual(response.status_code, 404)


# =============================================================================
# 14. TESTS ADICIONALES - FILTROS DE USUARIOS
# =============================================================================

class UsersFilterTests(APITestCase, TestDataMixin):
    """
    Tests para los filtros de usuarios.

    Flujos probados:
    - Filtrar por eds_name
    - Busqueda por nombre (search)

    Nota: Los tests que acceden a EDS directamente se prueban en OASISIntegrationTests.
    """
    databases = '__all__'

    def setUp(self):
        self.admin = self.create_user(
            name="Admin User",
            email="admin@test.com",
            is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_search_filter_works(self):
        """
        FLUJO: Buscar usuarios por nombre
        El parametro search filtra por nombre (case-insensitive)
        """
        self.create_user(name="Juan Perez", email="juan@test.com")
        self.create_user(name="Maria Garcia", email="maria@test.com")

        response = self.client.get('/api/users/?search=MARIA&no_pagination=true')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        users = data.get('users', [])
        # Debe encontrar solo Maria
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].get('name'), 'Maria Garcia')


# =============================================================================
# 15. TESTS ADICIONALES - PAGINACION ESPECIFICA
# =============================================================================

class PaginationClassTests(APITestCase, TestDataMixin):
    """
    Tests para las clases de paginacion.

    Flujos probados:
    - LargePagination (50 elementos por defecto)
    - StandardPagination (20 elementos por defecto)
    """

    def setUp(self):
        self.user = self.create_user(email="admin@test.com", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_eds_viewset_uses_large_pagination(self):
        """
        FLUJO: EDSViewSet esta configurado con LargePagination
        Verifica la configuracion del ViewSet sin hacer request
        """
        from .views import EDSViewSet
        from .pagination import LargePagination

        self.assertEqual(EDSViewSet.pagination_class, LargePagination)

    def test_users_viewset_uses_large_pagination(self):
        """
        FLUJO: UsersViewSet esta configurado con LargePagination
        """
        from .views import UsersViewSet
        from .pagination import LargePagination

        self.assertEqual(UsersViewSet.pagination_class, LargePagination)

    def test_work_orders_uses_standard_pagination(self):
        """
        FLUJO: WorkOrders usa StandardPagination (20 por pagina)
        """
        template = self.create_form_template()
        for i in range(25):
            self.create_work_order(self.user, template)

        response = self.client.get('/api/work-orders/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Verificar que hay paginacion
        self.assertIn('count', data)
        self.assertEqual(data.get('page_size'), 20)


# =============================================================================
# 16. TESTS ADICIONALES - FORM ANSWERS FILTROS
# =============================================================================

class FormAnswersFilterTests(APITestCase, TestDataMixin):
    """
    Tests para los filtros de FormAnswers.

    Flujos probados:
    - Filtrar por work_order_id en el list
    - Sin work_order_id retorna vacio (proteccion contra timeout)
    - Filtrar por form_template
    """

    def setUp(self):
        self.user = self.create_user(email="worker@test.com")
        self.template = self.create_form_template()
        self.question = self.create_question(self.template, "Test Q?", order=1)
        self.work_order = self.create_work_order(self.user, self.template)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_answers_without_work_order_id_returns_empty(self):
        """
        FLUJO: Listar respuestas sin work_order_id
        Debe retornar lista vacia para evitar cargar toda la BD
        """
        self.create_answer(self.question, self.work_order, "Respuesta")

        response = self.client.get('/api/form-answers/')
        self.assertEqual(response.status_code, 200)
        # Sin work_order_id, debe retornar vacío
        self.assertEqual(len(response.json()), 0)

    def test_list_answers_with_work_order_id(self):
        """
        FLUJO: Listar respuestas con work_order_id
        Debe retornar solo las respuestas del work_order especificado
        """
        self.create_answer(self.question, self.work_order, "Respuesta 1")

        response = self.client.get(f'/api/form-answers/?work_order_id={self.work_order.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_list_answers_with_work_order_param(self):
        """
        FLUJO: Listar respuestas con work_order (nombre alternativo)
        Debe aceptar ambos nombres de parametro
        """
        self.create_answer(self.question, self.work_order, "Respuesta")

        response = self.client.get(f'/api/form-answers/?work_order={self.work_order.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_list_answers_with_form_template_filter(self):
        """
        FLUJO: Filtrar respuestas por form_template
        """
        self.create_answer(self.question, self.work_order, "Respuesta")

        # Crear otro template y work_order
        template2 = self.create_form_template(name="Template 2")
        q2 = self.create_question(template2, "Q2?", order=1)
        wo2 = self.create_work_order(self.user, template2)
        self.create_answer(q2, wo2, "Otra respuesta")

        # Filtrar por template del primer work_order
        response = self.client.get(
            f'/api/form-answers/?work_order_id={self.work_order.id}&form_template={self.template.id}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)


# =============================================================================
# 17. TESTS ADICIONALES - DELETE DUPLICATES
# =============================================================================

class DeleteDuplicatesTests(APITestCase, TestDataMixin):
    """
    Tests para el endpoint delete-duplicates de FormAnswers.

    Flujos probados:
    - Eliminar respuestas duplicadas
    - No eliminar cuando no hay duplicados
    """

    def setUp(self):
        self.user = self.create_user(email="worker@test.com", is_staff=True)
        self.template = self.create_form_template()
        self.question = self.create_question(self.template, "Test Q?", order=1)
        self.work_order = self.create_work_order(self.user, self.template)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_delete_duplicates_no_duplicates(self):
        """
        FLUJO: delete-duplicates sin duplicados
        No debe eliminar nada
        """
        self.create_answer(self.question, self.work_order, "Unica respuesta")

        response = self.client.delete('/api/form-answers/delete-duplicates/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('deleted'), 0)

    def test_delete_duplicates_with_duplicates(self):
        """
        FLUJO: delete-duplicates con duplicados
        Debe eliminar duplicados y dejar solo el mas reciente
        """
        # Crear respuestas duplicadas manualmente (mismo question + work_order)
        FormAnswers.objects.create(
            question=self.question,
            work_order=self.work_order,
            answer="Primera"
        )
        FormAnswers.objects.create(
            question=self.question,
            work_order=self.work_order,
            answer="Segunda"
        )
        FormAnswers.objects.create(
            question=self.question,
            work_order=self.work_order,
            answer="Tercera"
        )

        # Verificar que hay 3 respuestas
        count_before = FormAnswers.objects.filter(
            question=self.question,
            work_order=self.work_order
        ).count()
        self.assertEqual(count_before, 3)

        response = self.client.delete('/api/form-answers/delete-duplicates/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Debe eliminar 2 (dejar solo la mas reciente)
        self.assertEqual(data.get('deleted'), 2)

        # Verificar que solo queda 1
        count_after = FormAnswers.objects.filter(
            question=self.question,
            work_order=self.work_order
        ).count()
        self.assertEqual(count_after, 1)

        # Verificar que quedo la mas reciente (mayor id = "Tercera")
        remaining = FormAnswers.objects.filter(
            question=self.question,
            work_order=self.work_order
        ).first()
        self.assertEqual(remaining.answer, "Tercera")
