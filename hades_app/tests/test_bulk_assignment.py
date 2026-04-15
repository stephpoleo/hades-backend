"""
Tests para el sistema de asignación masiva de formularios.

Cubre:
1. get_assigned_users - retorna solo el WO más reciente por usuario
2. _check_persistent_form - crea WO nuevo al completar un formulario persistente
3. _check_persistent_form - respeta preguntas obligatorias vs opcionales
4. _check_persistent_form - no crea duplicados si ya hay WO pendiente

Ejecutar con:
    python manage.py test hades_app.tests.test_bulk_assignment
"""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.test import APIClient
from rest_framework import status

from hades_app.models import Users, FormTemplate, WorkOrder, FormQuestions, FormAnswers
from hades_app.serializers import FormTemplateSerializer


def make_admin(email="admin@test.com"):
    user = Users.objects.create_user(email=email, name="Admin", password="adminpass")
    user.id_role_fk = 2
    user.is_staff = True
    user.save()
    return user


def make_employee(email="emp@test.com"):
    user = Users.objects.create_user(email=email, name="Employee", password="emppass")
    user.id_role_fk = 1
    user.save()
    return user


def make_template(name="Form A", persistent=False, questions_count=2, required=True):
    template = FormTemplate.objects.create(
        name=name, is_active=True, is_persistent=persistent
    )
    for i in range(questions_count):
        FormQuestions.objects.create(
            question=f"Question {i + 1}",
            form_template=template,
            question_order=i + 1,
            is_required=required,
            type="text",
        )
    return template


def make_work_order(user, template, clave_eds=None):
    return WorkOrder.objects.create(
        date=timezone.now(),
        user_id=user.id_usr_pk,
        form_template=template,
        clave_eds=clave_eds,
    )


def answer_all_questions(work_order):
    """Responde todas las preguntas de un WO."""
    for question in work_order.form_template.questions.all():
        FormAnswers.objects.create(
            question=question,
            work_order=work_order,
            answer="respuesta",
        )


# =============================================================================
# 1. get_assigned_users: solo retorna el WO más reciente por usuario
# =============================================================================

class GetAssignedUsersTest(TestCase):
    """Valida que get_assigned_users devuelva únicamente el WO más reciente."""

    def setUp(self):
        self.admin = make_admin()
        self.employee = make_employee()
        self.template = make_template(persistent=True)

    def test_returns_one_entry_per_user_for_persistent_form(self):
        """Para formulario persistente, solo aparece 1 entrada por usuario (el WO más reciente)."""
        wo1 = make_work_order(self.employee, self.template)
        answer_all_questions(wo1)
        # _check_persistent_form auto-crearía wo2; lo creamos manualmente aquí
        wo2 = make_work_order(self.employee, self.template)

        serializer = FormTemplateSerializer(self.template)
        assigned = serializer.data["assigned_users"]

        user_ids = [a["user_id"] for a in assigned]
        self.assertEqual(
            len(user_ids),
            len(set(user_ids)),
            "No deben aparecer user_ids duplicados en assigned_users",
        )

    def test_returns_latest_work_order_for_user(self):
        """El WO retornado debe ser el más reciente (mayor ID)."""
        wo1 = make_work_order(self.employee, self.template)
        wo2 = make_work_order(self.employee, self.template)

        serializer = FormTemplateSerializer(self.template)
        assigned = serializer.data["assigned_users"]

        entry = next(
            (a for a in assigned if a["user_id"] == self.employee.id_usr_pk), None
        )
        self.assertIsNotNone(entry)
        self.assertEqual(
            entry["work_order_id"],
            wo2.id,
            "Debe retornar el WO más reciente, no el primero",
        )

    def test_multiple_users_each_get_one_entry(self):
        """Múltiples usuarios asignados: cada uno aparece exactamente una vez."""
        emp2 = make_employee("emp2@test.com")
        make_work_order(self.employee, self.template)
        make_work_order(emp2, self.template)

        serializer = FormTemplateSerializer(self.template)
        assigned = serializer.data["assigned_users"]

        self.assertEqual(len(assigned), 2)
        user_ids = {a["user_id"] for a in assigned}
        self.assertIn(self.employee.id_usr_pk, user_ids)
        self.assertIn(emp2.id_usr_pk, user_ids)

    def test_empty_when_no_work_orders(self):
        """Sin WOs asignados, la lista debe estar vacía."""
        serializer = FormTemplateSerializer(self.template)
        self.assertEqual(serializer.data["assigned_users"], [])

    def test_completed_wo_is_excluded_from_assigned_users(self):
        """Un WO donde todas las preguntas obligatorias fueron respondidas NO debe
        aparecer en assigned_users (el usuario ya terminó el formulario)."""
        wo = make_work_order(self.employee, self.template)
        answer_all_questions(wo)  # template tiene 2 preguntas required=True

        serializer = FormTemplateSerializer(self.template)
        assigned = serializer.data["assigned_users"]

        self.assertEqual(
            len(assigned),
            0,
            "Un WO completado no debe aparecer en assigned_users",
        )

    def test_partially_answered_wo_still_appears_in_assigned_users(self):
        """Un WO con respuestas parciales (borrador) SÍ debe aparecer en assigned_users."""
        wo = make_work_order(self.employee, self.template)
        # Responder solo 1 de las 2 preguntas obligatorias
        question = self.template.questions.first()
        FormAnswers.objects.create(question=question, work_order=wo, answer="parcial")

        serializer = FormTemplateSerializer(self.template)
        assigned = serializer.data["assigned_users"]

        self.assertEqual(len(assigned), 1)
        self.assertEqual(assigned[0]["work_order_id"], wo.id)


# =============================================================================
# 2 & 3. _check_persistent_form: lógica de creación del siguiente WO
# =============================================================================

class CheckPersistentFormTest(TestCase):
    """Valida la creación automática del siguiente WO al completar un formulario persistente."""

    def setUp(self):
        self.client = APIClient()
        self.employee = make_employee()
        self.client.force_authenticate(user=self.employee)

    def test_creates_new_work_order_when_required_questions_answered(self):
        """Al responder todas las preguntas obligatorias de un formulario persistente,
        se crea automáticamente un nuevo WorkOrder pendiente."""
        template = make_template(persistent=True, questions_count=2, required=True)
        wo = make_work_order(self.employee, template)

        # Responder todas las preguntas vía API
        for question in template.questions.all():
            response = self.client.post(
                "/api/form-answers/",
                {
                    "question_id": question.id,
                    "work_order_id": wo.id,
                    "answer": "respuesta test",
                },
                format="multipart",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Debe haberse creado un nuevo WO pendiente
        new_wo_count = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk,
            form_template=template,
        ).exclude(id=wo.id).count()
        self.assertEqual(
            new_wo_count, 1, "Debe crearse exactamente 1 nuevo WO persistente"
        )

    def test_does_not_create_new_wo_when_optional_questions_skipped(self):
        """Si solo hay preguntas opcionales y no se responden, NO se crea un nuevo WO."""
        template = make_template(persistent=True, questions_count=2, required=False)
        wo = make_work_order(self.employee, template)

        # No responder ninguna pregunta - el WO queda "incompleto"
        new_wo_count = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk,
            form_template=template,
        ).exclude(id=wo.id).count()
        self.assertEqual(
            new_wo_count, 0, "Sin respuestas obligatorias, no debe crearse nuevo WO"
        )

    def test_required_questions_completion_triggers_persistent_wo(self):
        """Con preguntas mixtas (obligatorias + opcionales), basta responder las
        obligatorias para activar la creación del siguiente WO."""
        template = FormTemplate.objects.create(
            name="Mixed Form", is_active=True, is_persistent=True
        )
        required_q = FormQuestions.objects.create(
            question="Obligatoria",
            form_template=template,
            question_order=1,
            is_required=True,
            type="text",
        )
        FormQuestions.objects.create(
            question="Opcional",
            form_template=template,
            question_order=2,
            is_required=False,
            type="text",
        )

        wo = make_work_order(self.employee, template)

        # Solo responder la pregunta obligatoria
        self.client.post(
            "/api/form-answers/",
            {"question_id": required_q.id, "work_order_id": wo.id, "answer": "sí"},
            format="multipart",
        )

        new_wo_count = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk,
            form_template=template,
        ).exclude(id=wo.id).count()
        self.assertEqual(
            new_wo_count,
            1,
            "Responder solo las preguntas obligatorias debe activar el formulario persistente",
        )

    def test_does_not_create_duplicate_wo_if_pending_exists(self):
        """Si ya existe un WO sin respuestas para ese usuario/EDS/template,
        no se crea otro duplicado."""
        template = make_template(persistent=True, questions_count=1, required=True)
        wo = make_work_order(self.employee, template)

        # Responder la pregunta (dispara _check_persistent_form)
        question = template.questions.first()
        self.client.post(
            "/api/form-answers/",
            {"question_id": question.id, "work_order_id": wo.id, "answer": "ok"},
            format="multipart",
        )

        # Enviar la misma respuesta de nuevo (simula doble-envío o race condition)
        self.client.post(
            "/api/form-answers/",
            {"question_id": question.id, "work_order_id": wo.id, "answer": "ok2"},
            format="multipart",
        )

        new_wo_count = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk,
            form_template=template,
        ).exclude(id=wo.id).count()
        self.assertEqual(
            new_wo_count,
            1,
            "No debe crearse un segundo WO si ya existe uno pendiente sin respuestas",
        )

    def test_non_persistent_form_does_not_create_new_wo(self):
        """Un formulario NO persistente nunca crea un WO nuevo al completarse."""
        template = make_template(persistent=False, questions_count=2, required=True)
        wo = make_work_order(self.employee, template)

        for question in template.questions.all():
            self.client.post(
                "/api/form-answers/",
                {"question_id": question.id, "work_order_id": wo.id, "answer": "ok"},
                format="multipart",
            )

        new_wo_count = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk,
            form_template=template,
        ).exclude(id=wo.id).count()
        self.assertEqual(
            new_wo_count, 0, "Formulario no persistente no debe generar nuevo WO"
        )


# =============================================================================
# 4. Asignación masiva: WorkOrder se crea correctamente para múltiples usuarios
# =============================================================================

class BulkWorkOrderCreationTest(TestCase):
    """Valida que la creación de WOs para múltiples usuarios funcione correctamente."""

    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin()
        self.client.force_authenticate(user=self.admin)
        self.template = make_template()

    def test_creates_work_order_for_each_user(self):
        """Crear WOs para N usuarios genera exactamente N registros."""
        users = [make_employee(f"emp{i}@test.com") for i in range(5)]

        for user in users:
            response = self.client.post(
                "/api/work-orders/",
                {
                    "date": "2026-03-22T00:00:00Z",
                    "user_id": user.id_usr_pk,
                    "form_template_id": self.template.id,
                    "status": "pending",
                },
                format="multipart",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"Falló la creación de WO para usuario {user.email}",
            )

        total = WorkOrder.objects.filter(form_template=self.template).count()
        self.assertEqual(total, 5)

    def test_assigned_users_reflects_all_assigned(self):
        """Después de asignar a N usuarios, get_assigned_users retorna N entradas."""
        users = [make_employee(f"bulk{i}@test.com") for i in range(3)]

        for user in users:
            make_work_order(user, self.template)

        serializer = FormTemplateSerializer(self.template)
        assigned = serializer.data["assigned_users"]
        self.assertEqual(len(assigned), 3)

    def test_assigned_users_not_inflated_after_persistence_cycle(self):
        """Después de un ciclo completo persistente (asignar → completar → auto-reasignar),
        assigned_users no debe mostrar entradas duplicadas para el mismo usuario."""
        template = make_template(persistent=True, questions_count=1, required=True)
        employee = make_employee("cycle@test.com")

        # Ciclo 1: asignar y completar
        wo1 = make_work_order(employee, template)
        answer_all_questions(wo1)

        # Simular que _check_persistent_form creó wo2
        wo2 = make_work_order(employee, template)

        serializer = FormTemplateSerializer(template)
        assigned = serializer.data["assigned_users"]

        user_ids = [a["user_id"] for a in assigned]
        self.assertEqual(
            user_ids.count(employee.id_usr_pk),
            1,
            "Un usuario no debe aparecer más de una vez en assigned_users",
        )
        # Además, debe mostrar el WO más reciente
        entry = assigned[0]
        self.assertEqual(entry["work_order_id"], wo2.id)


# =============================================================================
# 5. Escenario real: asignación masiva a 40 usuarios con formulario persistente
# =============================================================================

class MassAssignmentPersistentFormTest(TestCase):
    """
    Simula el escenario reportado: asignar un formulario persistente a 40 usuarios,
    todos completan el formulario, y se verifica que a TODOS les vuelve a aparecer
    en pendientes.

    Dos fases:
    - Fase 1: Todos los 40 usuarios deben tener el formulario en pendientes tras la asignación.
    - Fase 2: Todos los 40 usuarios completan el formulario y deben recibir uno nuevo en pendientes.
    """

    NUM_USERS = 40

    @classmethod
    def setUpTestData(cls):
        # Los empleados, admin y template se crean UNA SOLA VEZ para toda la clase.
        # Django envuelve cada test individual en un SAVEPOINT, por lo que los WOs
        # y respuestas creados en cada test se revierten entre tests automáticamente.
        cls.admin = make_admin("massadmin@test.com")
        cls.template = make_template(
            name="Formulario Persistente Masivo",
            persistent=True,
            questions_count=2,
            required=True,
        )
        cls.questions = list(cls.template.questions.all())
        cls.employees = [
            make_employee(f"massemp{i}@test.com") for i in range(cls.NUM_USERS)
        ]

    def setUp(self):
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(user=self.admin)

    # ------------------------------------------------------------------
    # FASE 1: Asignación masiva — todos deben tener el formulario pendiente
    # ------------------------------------------------------------------

    def test_fase1_all_40_users_receive_pending_work_order_after_assignment(self):
        """
        Al asignar el formulario a 40 usuarios, los 40 deben tener un WorkOrder pendiente.
        Ninguno debe quedar sin formulario asignado.
        """
        # Asignar a los 40 usuarios (simula el flujo del frontend: un POST por usuario)
        for employee in self.employees:
            response = self.admin_client.post(
                "/api/work-orders/",
                {
                    "date": "2026-03-22T00:00:00Z",
                    "user_id": employee.id_usr_pk,
                    "form_template_id": self.template.id,
                    "status": "pending",
                },
                format="multipart",
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"El usuario {employee.email} no recibió WO (status {response.status_code})",
            )

        # Verificar que los 40 tienen exactamente 1 WO pendiente
        users_without_wo = []
        users_with_multiple_wo = []

        for employee in self.employees:
            wo_count = WorkOrder.objects.filter(
                user_id=employee.id_usr_pk,
                form_template=self.template,
            ).count()
            if wo_count == 0:
                users_without_wo.append(employee.email)
            elif wo_count > 1:
                users_with_multiple_wo.append(employee.email)

        self.assertEqual(
            len(users_without_wo),
            0,
            f"Los siguientes usuarios NO recibieron el formulario: {users_without_wo}",
        )
        self.assertEqual(
            len(users_with_multiple_wo),
            0,
            f"Los siguientes usuarios tienen WOs duplicados: {users_with_multiple_wo}",
        )

        total_wos = WorkOrder.objects.filter(form_template=self.template).count()
        self.assertEqual(
            total_wos,
            self.NUM_USERS,
            f"Deben existir exactamente {self.NUM_USERS} WOs, encontrados: {total_wos}",
        )

    # ------------------------------------------------------------------
    # FASE 2: Todos completan → todos deben volver a aparecer en pendientes
    # ------------------------------------------------------------------

    def test_fase2_all_users_get_new_pending_wo_after_completing_persistent_form(self):
        """
        Tras completar el formulario persistente (vía ORM directo + _check_persistent_form),
        todos los usuarios deben recibir un nuevo WorkOrder pendiente automáticamente.

        Nota: se usa ORM en lugar de HTTP porque CheckPersistentFormTest ya cubre la API.
        Esto permite escalar a NUM_USERS sin que el test tarde minutos.
        """
        from hades_app.views import FormAnswersViewSet

        # Asignar a todos (ORM directo)
        work_orders = [(emp, make_work_order(emp, self.template)) for emp in self.employees]

        # Completar cada WO: crear respuestas vía ORM y llamar _check_persistent_form
        viewset = FormAnswersViewSet()
        for employee, wo in work_orders:
            for question in self.questions:
                FormAnswers.objects.create(
                    question=question,
                    work_order=wo,
                    answer=f"respuesta de {employee.name}",
                )
            viewset._check_persistent_form(wo.id)

        # Verificar que TODOS tienen un nuevo WO pendiente (sin respuestas)
        users_without_new_wo = [
            employee.email
            for employee, original_wo in work_orders
            if not WorkOrder.objects.filter(
                user_id=employee.id_usr_pk,
                form_template=self.template,
            ).exclude(id=original_wo.id).annotate(
                ans_count=Count(
                    "formanswers",
                    filter=Q(formanswers__answer__isnull=False) & ~Q(formanswers__answer=""),
                )
            ).filter(ans_count=0).exists()
        ]

        self.assertEqual(
            len(users_without_new_wo),
            0,
            f"{len(users_without_new_wo)}/{self.NUM_USERS} usuarios NO recibieron el "
            f"formulario de vuelta: {users_without_new_wo}",
        )

    # ------------------------------------------------------------------
    # FASE 1+2 combinadas: ciclo completo end-to-end
    # ------------------------------------------------------------------

    def test_full_cycle_assign_complete_reassign(self):
        """
        Ciclo completo para NUM_USERS usuarios:
        1. Asignar formulario persistente (vía API — prueba el endpoint real).
        2. Completar todos los formularios (vía ORM — eficiente a escala).
        3. Verificar que todos reciben el formulario de vuelta en pendientes.
        4. assigned_users no debe tener duplicados.
        """
        from hades_app.views import FormAnswersViewSet

        # --- Asignación vía API (prueba el endpoint real) ---
        for employee in self.employees:
            self.admin_client.post(
                "/api/work-orders/",
                {
                    "date": "2026-03-22T00:00:00Z",
                    "user_id": employee.id_usr_pk,
                    "form_template_id": self.template.id,
                    "status": "pending",
                },
                format="multipart",
            )

        initial_wos = {
            wo.user_id: wo
            for wo in WorkOrder.objects.filter(form_template=self.template)
        }
        self.assertEqual(
            len(initial_wos), self.NUM_USERS,
            f"Fase 1: deben existir {self.NUM_USERS} WOs iniciales",
        )

        # --- Completar vía ORM (eficiente) ---
        viewset = FormAnswersViewSet()
        for employee in self.employees:
            wo = initial_wos[employee.id_usr_pk]
            for question in self.questions:
                FormAnswers.objects.create(question=question, work_order=wo, answer="ok")
            viewset._check_persistent_form(wo.id)

        # --- Verificar re-asignación automática ---
        users_without_new_wo = [
            employee.email
            for employee in self.employees
            if not WorkOrder.objects.filter(
                user_id=employee.id_usr_pk,
                form_template=self.template,
            ).exclude(id=initial_wos[employee.id_usr_pk].id).exists()
        ]

        self.assertEqual(
            len(users_without_new_wo),
            0,
            f"Fase 2: {len(users_without_new_wo)}/{self.NUM_USERS} usuarios no recibieron el "
            f"formulario de vuelta: {users_without_new_wo}",
        )

        # --- Verificar que assigned_users no tiene duplicados ---
        serializer = FormTemplateSerializer(self.template)
        assigned = serializer.data["assigned_users"]
        user_ids = [a["user_id"] for a in assigned]
        duplicates = [uid for uid in set(user_ids) if user_ids.count(uid) > 1]
        self.assertEqual(
            duplicates,
            [],
            f"assigned_users tiene user_ids duplicados: {duplicates}",
        )


# =============================================================================
# 6. Producto cartesiano en anotaciones — completion_status no debe inflarse
# =============================================================================

class CompletionStatusAnnotationTest(TestCase):
    """
    Regresión: las anotaciones _answers_count y _total_questions en
    WorkOrderViewSet.get_queryset() producían un producto cartesiano cuando
    Django hacía JOIN simultáneo de formanswers y form_template__questions.
    Sin distinct=True, N_answers × M_questions infla ambos conteos al mismo
    valor, haciendo que cualquier WO con al menos 1 respuesta no-vacía
    apareciera como "completed" aunque no estuvieran todas las preguntas
    contestadas. Esto impedía que el portal permitiera al usuario finalizar
    el formulario y bloqueaba la creación del WO persistente.
    """

    def setUp(self):
        self.client = APIClient()
        self.employee = make_employee()
        self.client.force_authenticate(user=self.employee)

    def _get_wo_status_via_api(self, user_id, wo_id):
        """Consulta el completion_status de un WO a través del endpoint real."""
        response = self.client.get(f"/api/work-orders/?user_id={user_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        items = data.get("results", data) if isinstance(data, dict) else data
        for item in items:
            if item["id"] == wo_id:
                return item["completion_status"]
        return None

    def test_partial_submission_shows_draft_not_completed(self):
        """
        Un WO con solo ALGUNAS preguntas respondidas debe mostrar 'draft',
        no 'completed'. Sin distinct=True en las anotaciones, la inflaciòn
        del producto cartesiano hace que N_nonEmpty × M == M × N_total
        y el WO aparece como completed erróneamente.
        """
        # 5 preguntas requeridas: formulario con más preguntas para que el
        # producto cartesiano sea detectable (5×3 ≠ 5×5 con distinct).
        template = FormTemplate.objects.create(
            name="Test Cartesian", is_active=True, is_persistent=True
        )
        questions = [
            FormQuestions.objects.create(
                question=f"Q{i}", form_template=template,
                question_order=i, is_required=True, type="text"
            )
            for i in range(1, 6)
        ]

        wo = make_work_order(self.employee, template)

        # Responder solo 3 de 5 preguntas (sin empty-answer para las otras 2)
        for q in questions[:3]:
            FormAnswers.objects.create(
                question=q, work_order=wo, answer="respuesta"
            )

        status = self._get_wo_status_via_api(self.employee.id_usr_pk, wo.id)
        self.assertEqual(
            status,
            "draft",
            "Un WO con 3/5 preguntas respondidas debe ser 'draft', no 'completed'. "
            "Si falla, probablemente falta distinct=True en las anotaciones del queryset."
        )

    def test_fully_answered_wo_shows_completed(self):
        """Con todas las preguntas respondidas, el WO debe mostrar 'completed'."""
        template = make_template(persistent=True, questions_count=3, required=True)
        wo = make_work_order(self.employee, template)
        answer_all_questions(wo)

        status = self._get_wo_status_via_api(self.employee.id_usr_pk, wo.id)
        self.assertEqual(status, "completed")

    def test_unanswered_wo_shows_pending(self):
        """Un WO sin ninguna respuesta debe mostrar 'pending'."""
        template = make_template(persistent=True, questions_count=3, required=True)
        wo = make_work_order(self.employee, template)

        status = self._get_wo_status_via_api(self.employee.id_usr_pk, wo.id)
        self.assertEqual(status, "pending")

    def test_persistent_form_not_created_for_partial_submission(self):
        """
        Al responder parcialmente un formulario persistente, NO debe
        crearse un nuevo WO (el WO actual no está completo todavía).
        """
        template = FormTemplate.objects.create(
            name="Persistent Partial", is_active=True, is_persistent=True
        )
        questions = [
            FormQuestions.objects.create(
                question=f"Q{i}", form_template=template,
                question_order=i, is_required=True, type="text"
            )
            for i in range(1, 4)
        ]
        wo = make_work_order(self.employee, template)

        # Responder solo 2 de 3 preguntas requeridas via API
        for q in questions[:2]:
            self.client.post(
                "/api/form-answers/",
                {"question_id": q.id, "work_order_id": wo.id, "answer": "ok"},
                format="multipart",
            )

        new_wo_count = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk,
            form_template=template,
        ).exclude(id=wo.id).count()
        self.assertEqual(
            new_wo_count,
            0,
            "Con solo 2/3 preguntas requeridas respondidas, no debe crearse nuevo WO",
        )


# =============================================================================
# 7. Escenario jttpl: formulario persistente asignado múltiples veces,
#    el usuario contesta el WO con ID más alto, pero hay WOs más antiguos
#    sin contestar. El usuario debe seguir apareciendo como asignado.
# =============================================================================

class PersistentFormMultipleAssignmentsTest(TestCase):
    """
    Reproduce el bug reportado con jttpl@natgas.com.mx:

    Situación: se le asignó el mismo formulario persistente varias veces
    (WO1 < WO2 < WO3 por ID). El usuario contesta WO3 (el más reciente por ID).
    WO1 y WO2 siguen sin respuestas.

    Comportamiento esperado:
    - get_assigned_users debe seguir mostrando al usuario como asignado
      (tiene WO2 pendiente, el más reciente de los incompletos).
    - El portal (latest_per_template) debe mostrar el formulario como PENDIENTE,
      no como COMPLETADO.
    - _check_persistent_form NO debe crear un WO extra (ya existe WO pendiente).
    - Si el usuario contesta todos los WOs pendientes, ENTONCES se crea uno nuevo.
    - Formulario NO persistente: tras contestarlo se desasigna al usuario.
    """

    def setUp(self):
        self.client = APIClient()
        self.employee = make_employee("jttpl_test@natgas.com.mx")
        self.client.force_authenticate(user=self.employee)

    def _make_persistent_template(self, n_questions=3):
        return make_template(
            name="F-PRO-OPE-013 BAÑOS DAMAS (TEST)",
            persistent=True,
            questions_count=n_questions,
            required=True,
        )

    # ------------------------------------------------------------------
    # Escenario principal
    # ------------------------------------------------------------------

    def test_user_remains_assigned_after_answering_latest_wo_when_older_pending_exist(self):
        """
        Simula el caso exacto de jttpl:
        - Se crean 3 WOs para el mismo usuario/formulario (asignaciones múltiples).
        - El usuario contesta el WO con ID más alto (WO3) vía API.
        - WO1 y WO2 siguen pendientes.
        Resultado esperado:
        - get_assigned_users muestra al usuario como asignado (con WO2, el más reciente incompleto).
        - El portal (latest_per_template) devuelve el WO2 como PENDIENTE.
        - NO se crea un WO extra por persistencia (WO2 ya es el nuevo pendiente).
        """
        from hades_app.views import FormAnswersViewSet

        template = self._make_persistent_template(n_questions=2)
        questions = list(template.questions.all())

        # 3 asignaciones consecutivas (simula el admin asignando varias veces)
        # clave_eds=None para no depender de la BD externa de EDS en tests
        wo1 = make_work_order(self.employee, template)
        wo2 = make_work_order(self.employee, template)
        wo3 = make_work_order(self.employee, template)

        self.assertLess(wo1.id, wo2.id)
        self.assertLess(wo2.id, wo3.id)

        # El usuario contesta WO3 (el más reciente) vía API
        for q in questions:
            resp = self.client.post(
                "/api/form-answers/",
                {"question_id": q.id, "work_order_id": wo3.id, "answer": "contestado"},
                format="multipart",
            )
            self.assertEqual(resp.status_code, 201)

        # WO3 está contestado; WO1 y WO2 siguen pendientes
        total_wos = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk, form_template=template
        ).count()
        self.assertEqual(total_wos, 3, "No debe haberse creado un WO extra (WO2 ya es el pendiente)")

        # get_assigned_users debe mostrar al usuario con WO2 (último incompleto)
        from hades_app.serializers import FormTemplateSerializer
        serializer = FormTemplateSerializer(template)
        assigned = serializer.data["assigned_users"]
        self.assertEqual(len(assigned), 1, "El usuario debe seguir apareciendo como asignado")
        self.assertEqual(
            assigned[0]["work_order_id"], wo2.id,
            "Debe mostrar WO2 (el más reciente de los incompletos), no WO3 (completado)",
        )

        # El portal (latest_per_template) debe devolver WO2 como PENDIENTE y WO3 como COMPLETADO
        portal_resp = self.client.get(
            f"/api/work-orders/?user_id={self.employee.id_usr_pk}"
            f"&latest_per_template=true&no_pagination=true"
        )
        self.assertEqual(portal_resp.status_code, 200)
        portal_data = portal_resp.data if isinstance(portal_resp.data, list) else portal_resp.data.get("results", portal_resp.data)
        form_wos = [w for w in portal_data if w.get("form_template", {}).get("id") == template.id]

        # Debe haber exactamente 2 entradas: 1 pendiente + 1 completada
        self.assertEqual(len(form_wos), 2, "El portal debe mostrar 1 WO pendiente + 1 WO completado")

        pending_wos = [w for w in form_wos if w["completion_status"] == "pending"]
        completed_wos = [w for w in form_wos if w["completion_status"] == "completed"]

        # Debe haber un WO pendiente (WO2, el más reciente incompleto)
        self.assertEqual(len(pending_wos), 1, "Debe haber exactamente 1 WO pendiente")
        self.assertEqual(
            pending_wos[0]["id"], wo2.id,
            "El WO pendiente debe ser WO2 (el incompleto más reciente)",
        )

        # El formulario contestado (WO3) debe aparecer en completados
        self.assertEqual(len(completed_wos), 1, "El formulario contestado debe aparecer en completados")
        self.assertEqual(
            completed_wos[0]["id"], wo3.id,
            "El WO completado debe ser WO3 (el que se contestó)",
        )

    def test_user_gets_new_wo_only_after_all_pending_wos_are_answered(self):
        """
        Si el usuario contesta TODOS los WOs pendientes uno a uno, recién
        al contestar el último se debe crear 1 nuevo WO por persistencia.
        """
        from hades_app.views import FormAnswersViewSet

        template = self._make_persistent_template(n_questions=1)
        questions = list(template.questions.all())

        wo1 = make_work_order(self.employee, template)
        wo2 = make_work_order(self.employee, template)

        viewset = FormAnswersViewSet()

        # Contestar WO2 (el más reciente): no debe crear nuevo WO porque WO1 existe
        for q in questions:
            FormAnswers.objects.create(question=q, work_order=wo2, answer="ok")
        viewset._check_persistent_form(wo2.id)

        total_after_wo2 = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk, form_template=template
        ).count()
        self.assertEqual(total_after_wo2, 2, "Con WO1 aún pendiente, no debe crearse WO extra")

        # Contestar WO1 (el único pendiente restante): AHORA sí debe crear WO nuevo
        for q in questions:
            FormAnswers.objects.create(question=q, work_order=wo1, answer="ok")
        viewset._check_persistent_form(wo1.id)

        total_after_wo1 = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk, form_template=template
        ).count()
        self.assertEqual(total_after_wo1, 3, "Al contestar el último pendiente, debe crearse 1 WO nuevo")

        # get_assigned_users debe mostrar al usuario con el WO nuevo
        from hades_app.serializers import FormTemplateSerializer
        serializer = FormTemplateSerializer(template)
        assigned = serializer.data["assigned_users"]
        self.assertEqual(len(assigned), 1)
        new_wo = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk, form_template=template
        ).exclude(id__in=[wo1.id, wo2.id]).first()
        self.assertIsNotNone(new_wo)
        self.assertEqual(assigned[0]["work_order_id"], new_wo.id)

    def test_non_persistent_form_unassigns_user_after_completion(self):
        """
        Formulario NO persistente: al contestarlo el usuario debe desaparecer
        de assigned_users y el portal no debe mostrarlo como pendiente.
        """
        template = make_template(
            name="Formulario NO persistente (TEST)",
            persistent=False,
            questions_count=2,
            required=True,
        )
        questions = list(template.questions.all())

        wo = make_work_order(self.employee, template)

        # Contestar vía API
        for q in questions:
            resp = self.client.post(
                "/api/form-answers/",
                {"question_id": q.id, "work_order_id": wo.id, "answer": "listo"},
                format="multipart",
            )
            self.assertEqual(resp.status_code, 201)

        # No debe crearse un WO nuevo
        total_wos = WorkOrder.objects.filter(
            user_id=self.employee.id_usr_pk, form_template=template
        ).count()
        self.assertEqual(total_wos, 1, "Formulario no persistente no debe crear WO nuevo")

        # get_assigned_users no debe mostrar al usuario
        from hades_app.serializers import FormTemplateSerializer
        serializer = FormTemplateSerializer(template)
        assigned = serializer.data["assigned_users"]
        self.assertEqual(len(assigned), 0, "Usuario debe estar desasignado tras completar form no persistente")

        # El portal debe mostrar el formulario como COMPLETADO (historial), no pendiente
        portal_resp = self.client.get(
            f"/api/work-orders/?user_id={self.employee.id_usr_pk}"
            f"&latest_per_template=true&no_pagination=true"
        )
        self.assertEqual(portal_resp.status_code, 200)
        portal_data = portal_resp.data if isinstance(portal_resp.data, list) else portal_resp.data.get("results", portal_resp.data)
        form_wos = [w for w in portal_data if w.get("form_template", {}).get("id") == template.id]
        self.assertEqual(len(form_wos), 1)
        self.assertEqual(
            form_wos[0]["completion_status"], "completed",
            "Portal debe mostrar el form no persistente como COMPLETADO, no pendiente",
        )
