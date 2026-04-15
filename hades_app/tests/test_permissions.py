"""
Tests de permisos por rol para Hades Backend.

Cubre los tres roles (Empleado=1, Administrador=2, Supervisor=3)
y el caso sin autenticación.

Ejecutar con:
    python manage.py test hades_app.tests.test_permissions
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from hades_app.models import Users, FormTemplate, WorkOrder, FormQuestions


def make_user(email, role_id, name="Test User"):
    user = Users.objects.create_user(
        email=email,
        name=name,
        password="testpass123",
    )
    user.id_role_fk = role_id
    user.save()
    return user


class SupervisorPermissionsTest(TestCase):
    """Supervisor (rol 3) puede ver dashboard, respuestas de formularios y preguntas."""

    def setUp(self):
        self.client = APIClient()
        self.supervisor = make_user("supervisor@test.com", role_id=3, name="Supervisor")
        self.client.force_authenticate(user=self.supervisor)

        self.template = FormTemplate.objects.create(name="Test Template", is_active=True)
        self.work_order = WorkOrder.objects.create(
            date="2026-01-01T00:00:00Z",
            status="pending",
            user_id=self.supervisor.id_usr_pk,
            form_template=self.template,
        )

    # --- Supervisor PUEDE ---

    def test_supervisor_can_view_dashboard_kpis(self):
        response = self.client.get("/api/dashboard/kpis/")
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_can_list_form_answers(self):
        response = self.client.get(
            f"/api/form-answers/?work_order_id={self.work_order.id}"
        )
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_can_retrieve_form_answer_list(self):
        response = self.client.get(
            f"/api/form-answers/?work_order_id={self.work_order.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_supervisor_can_create_form_answer(self):
        """POST /api/form-answers/ debe estar permitido para Supervisor (rol 3)."""
        question = FormQuestions.objects.create(
            question="¿Pregunta?",
            type="text",
            question_order=1,
            form_template=self.template,
        )
        response = self.client.post(
            "/api/form-answers/",
            {
                "question": question.id,
                "work_order": self.work_order.id,
                "answer": "Respuesta",
            },
        )
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_can_list_users(self):
        # Supervisor needs users list for responses module filters
        response = self.client.get("/api/users/")
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_can_list_eds(self):
        # Supervisor needs EDS list for responses module filters (EDS is unmanaged, 500 = permission passed)
        response = self.client.get("/api/eds/")
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_can_list_work_orders(self):
        # Supervisor needs work orders for the responses module
        response = self.client.get("/api/work-orders/")
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_can_list_form_questions(self):
        # Supervisor needs form questions to view work order details in responses module
        response = self.client.get(f"/api/form-questions/?form_template={self.template.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_supervisor_cannot_list_form_templates(self):
        response = self.client.get("/api/form-templates/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_cannot_create_work_order(self):
        response = self.client.post(
            "/api/work-orders/",
            {
                "date": "2026-01-15T10:00:00Z",
                "status": "pending",
                "user_id": self.supervisor.id_usr_pk,
                "form_template": self.template.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_cannot_delete_form_answer(self):
        response = self.client.delete("/api/form-answers/9999/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminPermissionsTest(TestCase):
    """Administrador (rol 2) tiene acceso total."""

    def setUp(self):
        self.client = APIClient()
        self.admin = make_user("admin@test.com", role_id=2, name="Admin")
        self.client.force_authenticate(user=self.admin)

        self.template = FormTemplate.objects.create(name="Admin Template", is_active=True)
        self.work_order = WorkOrder.objects.create(
            date="2026-01-01T00:00:00Z",
            status="pending",
            user_id=self.admin.id_usr_pk,
            form_template=self.template,
        )

    def test_admin_can_list_users(self):
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_list_eds(self):
        # EDS is an unmanaged external table; 500 means permission passed but DB unavailable in test env
        response = self.client.get("/api/eds/")
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_form_templates(self):
        response = self.client.get("/api/form-templates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_list_work_orders(self):
        response = self.client.get("/api/work-orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_view_dashboard_kpis(self):
        response = self.client.get("/api/dashboard/kpis/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_list_form_answers(self):
        response = self.client.get(
            f"/api/form-answers/?work_order_id={self.work_order.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_create_work_order(self):
        response = self.client.post(
            "/api/work-orders/",
            {
                "date": "2026-01-15T10:00:00Z",
                "status": "pending",
                "user_id": self.admin.id_usr_pk,
                "form_template": self.template.id,
            },
            format="json",
        )
        # 403 would mean permission denied; 400 is a validation error (permission passed)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_roles(self):
        response = self.client.get("/api/roles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EmployeePermissionsTest(TestCase):
    """Empleado (rol 1) puede enviar respuestas y ver sus work orders y plantillas."""

    def setUp(self):
        self.client = APIClient()
        self.employee = make_user("employee@test.com", role_id=1, name="Empleado")
        self.client.force_authenticate(user=self.employee)

        self.template = FormTemplate.objects.create(name="Employee Template", is_active=True)
        self.work_order = WorkOrder.objects.create(
            date="2026-01-01T00:00:00Z",
            status="pending",
            user_id=self.employee.id_usr_pk,
            form_template=self.template,
        )

    # --- Empleado PUEDE ---

    def test_employee_can_view_form_templates(self):
        response = self.client.get("/api/form-templates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_can_view_form_questions(self):
        response = self.client.get("/api/form-questions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_can_view_eds(self):
        # EDS is an unmanaged external table; 500 means permission passed but DB unavailable in test env
        response = self.client.get("/api/eds/")
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_view_own_work_orders(self):
        response = self.client.get(f"/api/work-orders/?user_id={self.employee.id_usr_pk}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_can_create_form_answer(self):
        question = FormQuestions.objects.create(
            question="¿Pregunta?",
            type="text",
            question_order=1,
            form_template=self.template,
        )
        response = self.client.post(
            "/api/form-answers/",
            {
                "question": question.id,
                "work_order": self.work_order.id,
                "answer": "Respuesta",
            },
        )
        self.assertIn(
            response.status_code,
            [status.HTTP_201_CREATED, status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST],
        )
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Empleado NO PUEDE ---

    def test_employee_cannot_view_dashboard(self):
        response = self.client.get("/api/dashboard/kpis/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_list_form_answers(self):
        response = self.client.get(
            f"/api/form-answers/?work_order_id={self.work_order.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_list_users(self):
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_manage_form_templates(self):
        response = self.client.post(
            "/api/form-templates/",
            {"name": "Nueva plantilla", "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_create_work_order(self):
        response = self.client.post(
            "/api/work-orders/",
            {
                "date": "2026-01-15T10:00:00Z",
                "status": "pending",
                "user_id": self.employee.id_usr_pk,
                "form_template": self.template.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UnauthenticatedPermissionsTest(TestCase):
    """Sin autenticación → 401/403 en todos los endpoints protegidos."""

    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_cannot_access_dashboard(self):
        response = self.client.get("/api/dashboard/kpis/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_cannot_access_users(self):
        response = self.client.get("/api/users/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_cannot_access_form_templates(self):
        response = self.client.get("/api/form-templates/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_cannot_access_work_orders(self):
        response = self.client.get("/api/work-orders/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_cannot_access_form_questions(self):
        response = self.client.get("/api/form-questions/")
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_unauthenticated_cannot_post_form_answers(self):
        response = self.client.post("/api/form-answers/", {"answer": "test"})
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )
