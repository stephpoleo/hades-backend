import logging
import os
from django.conf import settings
import base64
import uuid
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpResponse
from google.cloud import storage
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .models import (
    Users,
    EDS,
    FormTemplate,
    WorkOrder,
    FormQuestions,
    FormAnswers,
    Permissions,
    Roles,
)
from django.db import transaction
from django.db.models import Count, Max, Avg, Q, F
from django.db.models.functions import Coalesce
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from .serializers import (
    UsersSerializer,
    EDSSerializer,
    FormTemplateSerializer,
    WorkOrderSerializer,
    WorkOrderListSerializer,
    FormQuestionsSerializer,
    FormAnswersSerializer,
    PermissionsSerializer,
    RolesSerializer,
)
from .pagination import StandardPagination, LargePagination


# Endpoint: /api/auth/csrf/
@api_view(["GET"])
@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


# Endpoint: /api/auth/login/
@api_view(["POST"])
def login_view(request):
    data = request.data or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    logger = logging.getLogger("django")
    logger.info(
        "Login intento email=%s body_keys=%s csrf=%s",
        email,
        sorted(data.keys()),
        request.headers.get("X-CSRFToken"),
    )

    if not email or not password:
        return JsonResponse(
            {"success": False, "message": "Faltan credenciales"}, status=400
        )

    user = authenticate(request, username=email, password=password)

    if user is None:
        # Fallback para revisar credenciales almacenadas y facilitar el debug en ambientes de pruebas
        from .models import Users

        candidate = Users.objects.filter(email__iexact=email).first()
        if candidate and candidate.check_password(password):
            user = candidate

    if user is None:
        return JsonResponse(
            {"success": False, "message": "Credenciales inválidas"}, status=401
        )

    login(request, user)
    return JsonResponse({"success": True, "message": "Login exitoso"})


# Endpoint: /api/auth/logout/
@api_view(["POST"])
def logout_view(request):
    logout(request)
    return JsonResponse({"success": True, "message": "Logout exitoso"})


# Endpoint: /api/auth/me/
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    logger = logging.getLogger("django")
    user = request.user
    logger.warning(
        "/api/auth/me/: session_key=%s cookies=%s user=%s is_authenticated=%s",
        request.session.session_key,
        {k: "***" if "session" in k else v for k, v in request.COOKIES.items()},
        getattr(user, "email", None),
        user.is_authenticated,
    )

    return JsonResponse(
        {
            "id": getattr(user, "id_usr_pk", None),
            "email": getattr(user, "email", None),
            "username": user.get_username() if hasattr(user, "get_username") else None,
            "name": getattr(user, "name", None),
            "role": getattr(user, "role_name", None),
            "is_superuser": getattr(user, "is_superuser", None),
            "is_staff": getattr(user, "is_staff", None),
            "is_active": getattr(user, "is_active", None),
        }
    )


# EDS ViewSet - Standardized CRUD
class EDSViewSet(viewsets.ModelViewSet):
    """API para gestionar EDS (Estaciones de Servicio)"""

    queryset = EDS.objects.all()
    serializer_class = EDSSerializer
    pagination_class = LargePagination

    def get_pagination_class(self):
        """Permite desactivar paginación con ?no_pagination=true para dropdowns"""
        if self.request.query_params.get('no_pagination') == 'true':
            return None
        return self.pagination_class

    def create(self, request, *args, **kwargs):
        """Crear nueva EDS con mensaje de confirmación"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                eds = serializer.save()

                return Response(
                    {
                        "success": True,
                        "message": f'EDS "{eds.name}" creada exitosamente',
                        "eds": {
                            "clave_eds": eds.id_eds_pk,
                            "name": eds.name,
                            "plaza": eds.plaza,
                            "state": eds.state,
                            "municipality": eds.municipality,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": "Datos de EDS inválidos",
                        "message": "Por favor verifica los campos requeridos",
                        "details": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"success": False, "error": "Error al crear EDS", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        """Obtener una EDS específica con mensaje"""
        try:
            instance = self.get_object()

            return Response(
                {
                    "success": True,
                    "message": f'EDS "{instance.name}" encontrada',
                    "eds": {
                        "clave_eds": instance.id_eds_pk,
                        "name": instance.name,
                        "plaza": instance.plaza,
                        "state": instance.state,
                        "municipality": instance.municipality,
                        "zip_code": instance.zip_code,
                        "plaza_status": instance.plaza_status,
                        "longitude": (
                            str(instance.long_eds) if instance.long_eds else None
                        ),
                        "latitude": (
                            str(instance.latit_eds) if instance.latit_eds else None
                        ),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except EDS.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "EDS no encontrada",
                    "message": "La EDS solicitada no existe",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {"success": False, "error": "Error al obtener EDS", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        """Actualizar EDS con mensaje de confirmación"""
        try:
            instance = self.get_object()
            old_name = instance.name

            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                eds = serializer.save()

                return Response(
                    {
                        "success": True,
                        "message": f'EDS "{old_name}" actualizada exitosamente',
                        "eds": {
                            "clave_eds": eds.id_eds_pk,
                            "name": eds.name,
                            "plaza": eds.plaza,
                            "state": eds.state,
                            "municipality": eds.municipality,
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": "Datos de actualización inválidos",
                        "message": "Por favor verifica los campos a actualizar",
                        "details": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except EDS.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "EDS no encontrada",
                    "message": "La EDS que intentas actualizar no existe",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Error al actualizar EDS",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def list(self, request, *args, **kwargs):
        """Listar EDS con mensaje (incluyendo longitud y latitud)"""
        try:
            queryset = self.filter_queryset(self.get_queryset())

            # Permitir desactivar paginación para dropdowns
            no_pagination = request.query_params.get('no_pagination') == 'true'

            # Construir eds_data directamente del queryset (evita N+1)
            def build_eds_data(qs):
                return [
                    {
                        "clave_eds": eds.id_eds_pk,
                        "name": eds.name,
                        "plaza": eds.plaza,
                        "state": eds.state,
                        "municipality": eds.municipality,
                        "status": eds.plaza_status,
                        "longitude": str(eds.long_eds) if eds.long_eds else None,
                        "latitude": str(eds.latit_eds) if eds.latit_eds else None,
                    }
                    for eds in qs
                ]

            if no_pagination:
                eds_data = build_eds_data(queryset)
                return Response(
                    {
                        "success": True,
                        "message": f"{len(eds_data)} EDS encontradas",
                        "eds_list": eds_data,
                    },
                    status=status.HTTP_200_OK,
                )

            page = self.paginate_queryset(queryset)
            if page is not None:
                eds_data = build_eds_data(page)
                return self.get_paginated_response(eds_data)

            eds_data = build_eds_data(queryset)
            return Response(
                {
                    "success": True,
                    "message": f"{len(eds_data)} EDS encontradas",
                    "eds_list": eds_data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"success": False, "error": "Error al listar EDS", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        """Eliminar EDS con mensaje de confirmacion"""
        try:
            instance = self.get_object()
            eds_name = instance.name
            eds_clave = instance.id_eds_pk

            self.perform_destroy(instance)

            return Response(
                {
                    "success": True,
                    "message": f'EDS "{eds_name}" (Clave: {eds_clave}) eliminada exitosamente',
                    "deleted_eds": {"clave_eds": eds_clave, "name": eds_name},
                },
                status=status.HTTP_200_OK,
            )

        except EDS.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "EDS no encontrada",
                    "message": "La EDS que intentas eliminar no existe",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {"success": False, "error": "Error al eliminar EDS", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Users Views
class UsersViewSet(viewsets.ModelViewSet):
    """API para gestionar usuarios"""

    queryset = Users.objects.all()
    serializer_class = UsersSerializer
    pagination_class = LargePagination

    def get_pagination_class(self):
        """Permite desactivar paginación con ?no_pagination=true para dropdowns"""
        if self.request.query_params.get('no_pagination') == 'true':
            return None
        return self.pagination_class

    def create(self, request, *args, **kwargs):
        """Crear nuevo usuario con mensaje de confirmación"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                if "password" in request.data:
                    user.set_password(request.data["password"])
                    user.save()

                return Response(
                    {
                        "success": True,
                        "message": f'Usuario "{user.name}" creado exitosamente',
                        "user": {
                            "id": user.id_usr_pk,
                            "name": user.name,
                            "email": user.email,
                            "role": user.role_name,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": "Datos de usuario inválidos",
                        "message": "Por favor verifica los campos requeridos",
                        "details": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Error al crear usuario",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        """Obtener un usuario específico con mensaje"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return Response(
                {
                    "success": True,
                    "message": f'Usuario "{instance.name}" encontrado',
                    "user": {
                        "id": instance.id_usr_pk,
                        "name": instance.name,
                        "email": instance.email,
                        "role": instance.role_name,
                        "status": instance.usr_status,
                        "eds_info": serializer.data.get("eds_info"),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Users.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "Usuario no encontrado",
                    "message": "El usuario solicitado no existe",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Error al obtener usuario",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        """Actualizar usuario con mensaje de confirmación"""
        try:
            instance = self.get_object()
            old_name = instance.name

            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                user = serializer.save()

                if "password" in request.data:
                    user.set_password(request.data["password"])
                    user.save()

                return Response(
                    {
                        "success": True,
                        "message": f'Usuario "{old_name}" actualizado exitosamente',
                        "user": {
                            "id": user.id_usr_pk,
                            "name": user.name,
                            "email": user.email,
                            "role": user.role_name,
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": "Datos de actualización inválidos",
                        "message": "Por favor verifica los campos a actualizar",
                        "details": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Users.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "Usuario no encontrado",
                    "message": "El usuario que intentas actualizar no existe",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Error al actualizar usuario",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def list(self, request, *args, **kwargs):
        """Listar usuarios con mensaje y todos los campos del serializer (incluyendo eds_info)"""
        try:
            from collections import defaultdict

            queryset = self.filter_queryset(self.get_queryset())

            # Permitir desactivar paginación para dropdowns
            no_pagination = request.query_params.get('no_pagination') == 'true'

            # Search filter: busca por nombre (case-insensitive)
            search = request.query_params.get('search', '').strip()
            if search:
                queryset = queryset.filter(name__icontains=search)

            # EDS filter: filtra por nombre de EDS
            eds_name = request.query_params.get('eds_name', '').strip()
            if eds_name:
                # Primero obtener las claves de EDS que coinciden con el nombre
                matching_eds_claves = list(
                    EDS.objects.filter(name__iexact=eds_name).values_list('id_eds_pk', flat=True)
                )
                queryset = queryset.filter(clave_eds_fk__in=matching_eds_claves)

            # Calcular stats de work orders en batch para evitar N+1
            # 1. Contar asignadas por usuario
            assigned_stats = (
                WorkOrder.objects.values("user_id")
                .annotate(assigned=Count("id"))
            )
            user_stats = defaultdict(lambda: {"assigned": 0, "completed": 0})
            for stat in assigned_stats:
                user_stats[stat["user_id"]]["assigned"] = stat["assigned"]

            # 2. Calcular completadas (answers >= questions del template)
            work_orders = (
                WorkOrder.objects.select_related("form_template")
                .prefetch_related("form_template__questions")
                .annotate(
                    answers_count=Count(
                        "formanswers",
                        filter=~Q(formanswers__answer__isnull=True)
                        & ~Q(formanswers__answer__exact=""),
                    )
                )
            )

            for wo in work_orders:
                if wo.form_template and wo.user_id:
                    total_questions = wo.form_template.questions.count()
                    if total_questions > 0 and wo.answers_count >= total_questions:
                        user_stats[wo.user_id]["completed"] += 1

            # Pasar stats al contexto del serializer
            context = self.get_serializer_context()
            context["user_stats"] = dict(user_stats)

            # Batch load EDS para evitar N+1 en get_eds_info
            eds_claves = set(queryset.values_list('clave_eds_fk', flat=True))
            eds_claves.discard(None)
            eds_claves.discard('')
            if eds_claves:
                eds_map = {e.id_eds_pk: e for e in EDS.objects.filter(id_eds_pk__in=eds_claves)}
                context["eds_map"] = eds_map

            if no_pagination:
                serializer = self.get_serializer(queryset, many=True, context=context)
                return Response(
                    {
                        "success": True,
                        "message": f"{len(serializer.data)} usuarios encontrados",
                        "users": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context=context)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True, context=context)
            return Response(
                {
                    "success": True,
                    "message": f"{len(serializer.data)} usuarios encontrados",
                    "users": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Error al listar usuarios",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        """Eliminar usuario con mensaje de confirmación"""
        try:
            instance = self.get_object()
            user_name = instance.name
            user_id = instance.id_usr_pk

            self.perform_destroy(instance)

            return Response(
                {
                    "success": True,
                    "message": f'Usuario "{user_name}" (ID: {user_id}) eliminado exitosamente',
                    "deleted_user": {"id": user_id, "name": user_name},
                },
                status=status.HTTP_200_OK,
            )

        except Users.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "Usuario no encontrado",
                    "message": "El usuario que intentas eliminar no existe",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Error al eliminar usuario",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# FormTemplate ViewSet
class FormTemplateViewSet(viewsets.ModelViewSet):
    """API para gestionar plantillas de formularios."""

    queryset = FormTemplate.objects.all()
    serializer_class = FormTemplateSerializer
    pagination_class = StandardPagination  # Paginación estándar para formularios

    @action(detail=False, methods=["delete"], url_path="clear-all")
    def clear_all(self, request):
        """Elimina todas las plantillas, preguntas, ordenes de trabajo y respuestas asociadas."""
        with transaction.atomic():
            answers_deleted, _ = FormAnswers.objects.all().delete()
            work_orders_deleted, _ = WorkOrder.objects.all().delete()
            questions_deleted, _ = FormQuestions.objects.all().delete()
            templates_deleted, _ = FormTemplate.objects.all().delete()

        return Response(
            {
                "success": True,
                "message": "Plantillas, preguntas, ordenes de trabajo y respuestas eliminadas.",
                "deleted": {
                    "templates": templates_deleted,
                    "questions": questions_deleted,
                    "work_orders": work_orders_deleted,
                    "answers": answers_deleted,
                },
            },
            status=status.HTTP_200_OK,
        )


# WorkOrder ViewSet
class WorkOrderViewSet(viewsets.ModelViewSet):
    """API para gestionar órdenes de trabajo"""

    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializer
    pagination_class = StandardPagination

    def get_serializer_class(self):
        # Use lightweight serializer for list to avoid timeout
        if self.action == 'list':
            return WorkOrderListSerializer
        return WorkOrderSerializer

    def list(self, request, *args, **kwargs):
        """
        Listar work orders con paginación y batch loading optimizado.

        Query params:
        - page: número de página (default: 1)
        - page_size: registros por página (default: 50, max: 200)
        - no_pagination: 'true' para desactivar paginación
        - user_id: filtrar por usuario
        - form_template_id: filtrar por formulario
        - clave_eds: filtrar por EDS
        """
        logger = logging.getLogger("django")
        try:
            queryset = self.filter_queryset(self.get_queryset())

            # Permitir desactivar paginación si es necesario
            no_pagination = request.query_params.get('no_pagination') == 'true'

            # Batch load: obtener todos los user_ids y clave_eds únicos
            # para cargar en una sola query
            wo_data = queryset.values_list('user_id', 'clave_eds')
            user_ids = set()
            eds_claves = set()
            for user_id, clave_eds in wo_data:
                if user_id:
                    user_ids.add(user_id)
                if clave_eds:
                    eds_claves.add(clave_eds)

            # Batch load users
            users_map = {}
            if user_ids:
                users_map = {
                    u.id_usr_pk: u
                    for u in Users.objects.filter(id_usr_pk__in=user_ids)
                }

            # Batch load EDS
            eds_map = {}
            if eds_claves:
                eds_map = {
                    e.id_eds_pk: e
                    for e in EDS.objects.filter(id_eds_pk__in=eds_claves)
                }

            # Pasar datos batch al contexto del serializer
            context = self.get_serializer_context()
            context['users_map'] = users_map
            context['eds_map'] = eds_map

            if no_pagination:
                serializer = self.get_serializer(queryset, many=True, context=context)
                return Response(serializer.data)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context=context)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True, context=context)
            return Response(serializer.data)

        except Exception as exc:
            logger.exception("Error GET /api/work-orders/")
            return Response({"detail": str(exc)}, status=500)

    # Aseguramos que kwargs (ej. image) lleguen al .save()
    def perform_create(self, serializer, **kwargs):
        serializer.save(**kwargs)

    def perform_update(self, serializer, **kwargs):
        serializer.save(**kwargs)

    def get_queryset(self):
        """
        QuerySet optimizado con:
        - select_related para form_template
        - prefetch_related para questions
        - annotate para answers_count (evita N+1)
        """
        queryset = WorkOrder.objects.select_related(
            'form_template'
        ).prefetch_related(
            'form_template__questions'
        ).annotate(
            _answers_count=Count(
                'formanswers',
                filter=~Q(formanswers__answer__isnull=True) & ~Q(formanswers__answer__exact='')
            ),
            _total_questions=Count('form_template__questions')
        )

        # Filtros opcionales
        user_id = self.request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        form_template_id = self.request.query_params.get("form_template_id")
        if form_template_id:
            queryset = queryset.filter(form_template_id=form_template_id)

        clave_eds = self.request.query_params.get("clave_eds")
        if clave_eds:
            queryset = queryset.filter(clave_eds=clave_eds)

        return queryset.order_by('-date', '-id')

    @action(detail=False, methods=["delete"], url_path="clear-all")
    def clear_all(self, request):
        """Elimina todas las ordenes de trabajo y respuestas asociadas."""
        with transaction.atomic():
            answers_deleted, _ = FormAnswers.objects.all().delete()
            work_orders_deleted, _ = WorkOrder.objects.all().delete()

        return Response(
            {
                "success": True,
                "message": "Ordenes de trabajo y respuestas eliminadas.",
                "deleted": {
                    "work_orders": work_orders_deleted,
                    "answers": answers_deleted,
                },
            },
            status=status.HTTP_200_OK,
        )


# FormQuestions ViewSet
class FormQuestionsViewSet(viewsets.ModelViewSet):
    """API para gestionar preguntas de formularios.

    Sin paginación: las preguntas de un formulario deben devolverse completas.

    Filtros soportados:
        - form_template: ID del template para filtrar preguntas
          Ejemplo: GET /api/form-questions/?form_template=5
    """

    queryset = FormQuestions.objects.all()
    serializer_class = FormQuestionsSerializer
    pagination_class = None  # Deshabilitar paginación para preguntas

    def get_queryset(self):
        """Filtra las preguntas por form_template si se proporciona."""
        queryset = FormQuestions.objects.all().order_by("question_order")

        form_template_id = self.request.query_params.get("form_template")
        if form_template_id:
            queryset = queryset.filter(form_template_id=form_template_id)

        return queryset


# FormAnswers ViewSet
class FormAnswersViewSet(viewsets.ModelViewSet):
    """API para gestionar respuestas de formularios.

    Sin paginación: las respuestas se cargan por work_order completas.
    """

    # Asegura que DRF procese multipart/form-data y lea request.FILES
    parser_classes = (MultiPartParser, FormParser)
    pagination_class = None  # Deshabilitar paginación para respuestas

    @action(detail=False, methods=["get"], url_path="by-workorder")
    def by_workorder(self, request):
        """
        Devuelve todas las respuestas para un work_order_id dado.
        Uso: /api/form-answers/by-workorder/?work_order_id=1
        """
        work_order_id = request.query_params.get("work_order_id")
        if not work_order_id:
            return Response(
                {"detail": "work_order_id es requerido como parámetro."}, status=400
            )
        queryset = self.get_queryset().filter(work_order_id=work_order_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    from rest_framework.decorators import action
    from django.db.models import Count, Max

    @action(detail=False, methods=["delete"], url_path="delete-duplicates")
    def delete_duplicates(self, request):
        """
        Elimina respuestas duplicadas por (question_id, work_order_id), dejando solo la más reciente (mayor id).
        """
        duplicates = (
            FormAnswers.objects.values("question_id", "work_order_id")
            .annotate(count=Count("id"), max_id=Max("id"))
            .filter(count__gt=1)
        )
        total_deleted = 0
        for dup in duplicates:
            to_delete = FormAnswers.objects.filter(
                question_id=dup["question_id"], work_order_id=dup["work_order_id"]
            ).exclude(id=dup["max_id"])
            deleted, _ = to_delete.delete()
            total_deleted += deleted
        return Response(
            {"deleted": total_deleted, "message": "Respuestas duplicadas eliminadas."}
        )

    """API para gestionar respuestas de formularios"""
    queryset = FormAnswers.objects.all()
    serializer_class = FormAnswersSerializer

    def list(self, request, *args, **kwargs):
        logger = logging.getLogger("django")
        try:
            return super().list(request, *args, **kwargs)
        except Exception as exc:
            logger.exception("Error GET /api/form-answers/")
            return Response({"detail": str(exc)}, status=500)

    def _decode_base64_image(self, data_str, logger):
        """
        Decodifica una imagen base64/data URI a ContentFile.

        Args:
            data_str: String con datos base64 o data URI
            logger: Logger para registrar eventos

        Returns:
            ContentFile or None
        """
        if not data_str or not isinstance(data_str, str):
            return None

        file_name = f"{uuid.uuid4().hex}.jpg"
        try:
            img_str = data_str
            if img_str.startswith("data:") and "," in img_str:
                header, encoded = img_str.split(",", 1)
                if ";base64" in header:
                    img_str = encoded
                    try:
                        ext = header.split("/")[1].split(";")[0]
                        file_name = f"{uuid.uuid4().hex}.{ext}"
                    except Exception:
                        pass
            decoded_file = base64.b64decode(img_str)
            return ContentFile(decoded_file, name=file_name)
        except Exception as decode_exc:
            logger.error(
                "No se pudo decodificar image base64: %s",
                decode_exc,
                exc_info=True,
            )
            return None

    def _extract_images_from_request(self, request, data, logger):
        """
        Extrae hasta 3 imágenes desde request.FILES y/o data (base64).

        Busca en los siguientes keys:
        - image, image_2, image_3 (nombres primarios)
        - attachment, attachment_2, attachment_3 (nombres alternativos)
        - file, file_2, file_3 (nombres alternativos)

        Args:
            request: HTTP request
            data: Request data (puede ser modificado)
            logger: Logger para registrar eventos

        Returns:
            dict: {image: file, image_2: file, image_3: file}
        """
        image_files = {"image": None, "image_2": None, "image_3": None}

        # Mapeo de nombres alternativos a nombres canónicos
        field_mapping = {
            "image": ["image", "attachment", "file"],
            "image_2": ["image_2", "attachment_2", "file_2"],
            "image_3": ["image_3", "attachment_3", "file_3"],
        }

        # 1) Extraer archivos desde request.FILES
        for canonical, alternatives in field_mapping.items():
            for key in alternatives:
                if key in request.FILES:
                    image_files[canonical] = request.FILES[key]
                    break

        # 2) Si hay archivos sueltos sin nombre específico, asignarlos en orden
        assigned_files = {k for k, v in image_files.items() if v is not None}
        unassigned_slots = [k for k in ["image", "image_2", "image_3"] if k not in assigned_files]

        for key in request.FILES:
            if key not in sum(field_mapping.values(), []):
                if unassigned_slots:
                    slot = unassigned_slots.pop(0)
                    image_files[slot] = request.FILES[key]

        # 3) Procesar base64 en data si no hay archivo
        try:
            data = data.copy()
        except Exception:
            pass

        for canonical, alternatives in field_mapping.items():
            if image_files[canonical] is None:
                for key in alternatives:
                    value = data.get(key)
                    if value and isinstance(value, str):
                        decoded = self._decode_base64_image(value, logger)
                        if decoded:
                            image_files[canonical] = decoded
                            data[canonical] = decoded
                            break

        # 4) Inyectar archivos en data si no están
        for canonical, file in image_files.items():
            if file and not data.get(canonical):
                data[canonical] = file

        return image_files, data

    def create(self, request, *args, **kwargs):
        logger = logging.getLogger("django")
        try:
            data = request.data

            # Extraer hasta 3 imágenes
            image_files, data = self._extract_images_from_request(request, data, logger)

            logger.info(
                "POST /api/form-answers/ files=%s data_keys=%s images_found=%s",
                list(request.FILES.keys()),
                list(getattr(data, "keys", lambda: [])()),
                {k: bool(v) for k, v in image_files.items()},
            )

            # Si es un array, procesar cada respuesta
            if isinstance(data, list):
                results = []
                errors = []
                for item in data:
                    question_id = item.get("question_id")
                    work_order_id = item.get("work_order_id")
                    if not question_id or not work_order_id:
                        errors.append(
                            {
                                "detail": "question_id y work_order_id son requeridos.",
                                "data": item,
                            }
                        )
                        continue
                    instance = FormAnswers.objects.filter(
                        question_id=question_id, work_order_id=work_order_id
                    ).first()
                    if instance:
                        serializer = self.get_serializer(
                            instance, data=item, partial=True
                        )
                        serializer.is_valid(raise_exception=True)
                        self.perform_update(serializer)
                        results.append(serializer.data)
                    else:
                        serializer = self.get_serializer(data=item)
                        serializer.is_valid(raise_exception=True)
                        self.perform_create(serializer)
                        results.append(serializer.data)
                status_code = 200 if not errors else 207
                return Response(
                    {"results": results, "errors": errors}, status=status_code
                )

            # Si es un solo objeto, procesar
            question_id = data.get("question_id")
            work_order_id = data.get("work_order_id")
            if not question_id or not work_order_id:
                return Response(
                    {"detail": "question_id y work_order_id son requeridos."},
                    status=400,
                )

            instance = FormAnswers.objects.filter(
                question_id=question_id, work_order_id=work_order_id
            ).first()

            # Preparar kwargs con las imágenes
            save_kwargs = {}
            for field_name in ["image", "image_2", "image_3"]:
                img = image_files.get(field_name)
                if img:
                    save_kwargs[field_name] = img

            if instance:
                serializer = self.get_serializer(instance, data=data, partial=True)
                serializer.is_valid(raise_exception=True)
                logger.info(
                    "FormAnswers update validated keys=%s images=%s",
                    list(serializer.validated_data.keys()),
                    {k: bool(v) for k, v in save_kwargs.items()},
                )

                # Merge con validated_data si no viene en save_kwargs
                for field_name in ["image", "image_2", "image_3"]:
                    if field_name not in save_kwargs:
                        val = serializer.validated_data.get(field_name)
                        if val:
                            save_kwargs[field_name] = val

                obj = serializer.save(**save_kwargs)
                return Response(
                    FormAnswersSerializer(obj, context={"request": request}).data,
                    status=200
                )
            else:
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                logger.info(
                    "FormAnswers create validated keys=%s images=%s",
                    list(serializer.validated_data.keys()),
                    {k: bool(v) for k, v in save_kwargs.items()},
                )

                # Merge con validated_data si no viene en save_kwargs
                for field_name in ["image", "image_2", "image_3"]:
                    if field_name not in save_kwargs:
                        val = serializer.validated_data.get(field_name)
                        if val:
                            save_kwargs[field_name] = val

                obj = serializer.save(**save_kwargs)
                headers = self.get_success_headers(serializer.data)
                return Response(
                    FormAnswersSerializer(obj, context={"request": request}).data,
                    status=201,
                    headers=headers
                )
        except Exception as exc:
            logger.exception(
                "Error en /api/form-answers/ payload_keys=%s files=%s",
                list(getattr(request.data, "keys", lambda: [])()),
                list(request.FILES.keys()),
            )
            return Response({"detail": str(exc)}, status=500)

    # Aceptar kwargs (ej. image) cuando se fuerza el guardado
    def perform_create(self, serializer, **kwargs):
        serializer.save(**kwargs)

    def perform_update(self, serializer, **kwargs):
        serializer.save(**kwargs)

    def _download_attachment(self, image_field, logger):
        """
        Descarga un adjunto desde GCS.

        Args:
            image_field: Campo ImageField con la imagen
            logger: Logger para registrar eventos

        Returns:
            tuple: (payload, content_type, filename) o (None, None, None) si hay error
        """
        if not image_field or not image_field.name:
            return None, None, None

        try:
            client = storage.Client(credentials=settings.GS_CREDENTIALS)
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            blob = bucket.blob(image_field.name)
            payload = blob.download_as_bytes()
            content_type = blob.content_type or "application/octet-stream"
            filename = os.path.basename(image_field.name)
            return payload, content_type, filename
        except Exception as exc:
            logger.error(
                "[FormAnswersViewSet] No se pudo descargar %s: %s",
                image_field.name,
                exc,
                exc_info=True,
            )
            return None, None, None

    @action(detail=True, methods=["get"], url_path="attachment")
    def attachment(self, request, pk=None):
        """Descarga la imagen principal (image) de una respuesta."""
        answer = self.get_object()
        if not answer.image:
            return Response(
                {"detail": "Esta respuesta no tiene adjunto."},
                status=status.HTTP_404_NOT_FOUND,
            )

        logger = logging.getLogger("django")
        payload, content_type, filename = self._download_attachment(answer.image, logger)

        if payload is None:
            return Response(
                {"detail": "No se pudo descargar el adjunto desde el almacenamiento."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = HttpResponse(payload, content_type=content_type)
        response["Content-Length"] = str(len(payload))
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response

    @action(detail=True, methods=["get"], url_path="attachment-2")
    def attachment_2(self, request, pk=None):
        """Descarga la segunda imagen (image_2) de una respuesta."""
        answer = self.get_object()
        if not answer.image_2:
            return Response(
                {"detail": "Esta respuesta no tiene segundo adjunto."},
                status=status.HTTP_404_NOT_FOUND,
            )

        logger = logging.getLogger("django")
        payload, content_type, filename = self._download_attachment(answer.image_2, logger)

        if payload is None:
            return Response(
                {"detail": "No se pudo descargar el adjunto desde el almacenamiento."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = HttpResponse(payload, content_type=content_type)
        response["Content-Length"] = str(len(payload))
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response

    @action(detail=True, methods=["get"], url_path="attachment-3")
    def attachment_3(self, request, pk=None):
        """Descarga la tercera imagen (image_3) de una respuesta."""
        answer = self.get_object()
        if not answer.image_3:
            return Response(
                {"detail": "Esta respuesta no tiene tercer adjunto."},
                status=status.HTTP_404_NOT_FOUND,
            )

        logger = logging.getLogger("django")
        payload, content_type, filename = self._download_attachment(answer.image_3, logger)

        if payload is None:
            return Response(
                {"detail": "No se pudo descargar el adjunto desde el almacenamiento."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = HttpResponse(payload, content_type=content_type)
        response["Content-Length"] = str(len(payload))
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


@api_view(["DELETE"])
def clear_form_templates(request):
    """
    Endpoint directo para borrar todas las plantillas, preguntas, work orders y respuestas.
    Útil si el router no expone correctamente la acción del ViewSet.
    """
    with transaction.atomic():
        answers_deleted, _ = FormAnswers.objects.all().delete()
        work_orders_deleted, _ = WorkOrder.objects.all().delete()
        questions_deleted, _ = FormQuestions.objects.all().delete()
        templates_deleted, _ = FormTemplate.objects.all().delete()

    return Response(
        {
            "success": True,
            "message": "Plantillas, preguntas, ordenes de trabajo y respuestas eliminadas.",
            "deleted": {
                "templates": templates_deleted,
                "questions": questions_deleted,
                "work_orders": work_orders_deleted,
                "answers": answers_deleted,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
def clear_work_orders(request):
    """
    Endpoint directo para borrar todas las work orders y sus respuestas.
    """
    with transaction.atomic():
        answers_deleted, _ = FormAnswers.objects.all().delete()
        work_orders_deleted, _ = WorkOrder.objects.all().delete()

    return Response(
        {
            "success": True,
            "message": "Ordenes de trabajo y respuestas eliminadas.",
            "deleted": {
                "work_orders": work_orders_deleted,
                "answers": answers_deleted,
            },
        },
        status=status.HTTP_200_OK,
    )


class RolesViewSet(viewsets.ModelViewSet):
    """API para gestionar roles.

    Sin paginación: normalmente hay pocos roles.
    """

    queryset = Roles.objects.all()
    serializer_class = RolesSerializer
    pagination_class = None  # Deshabilitar paginación para roles

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                role = serializer.save()
                return Response(
                    {
                        "success": True,
                        "message": f'Rol "{role.name}" creado exitosamente',
                        "role": RolesSerializer(role).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": "Datos de rol inválidos",
                        "details": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"success": False, "error": "Error al crear rol", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PermissionsViewSet(viewsets.ModelViewSet):
    """API para gestionar permisos.

    Sin paginación: normalmente hay pocos permisos.
    """

    queryset = Permissions.objects.all()
    serializer_class = PermissionsSerializer
    pagination_class = None  # Deshabilitar paginación para permisos

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                permission = serializer.save()
                return Response(
                    {
                        "success": True,
                        "message": f'Permiso "{permission.name}" creado exitosamente',
                        "permission": PermissionsSerializer(permission).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "error": "Datos de permiso inválidos",
                        "details": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": "Error al crear permiso",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Dashboard KPI endpoint
@api_view(["GET"])
def dashboard_kpis(request):
    """
    Endpoint para obtener los KPIs del dashboard de cumplimiento.

    Query params:
    - zone: Filtrar por zona/plaza (opcional)
    - eds: Filtrar por clave_eds (opcional)
    - form: Filtrar por form_template_id (opcional)
    - start_date: Fecha inicio YYYY-MM-DD (opcional)
    - end_date: Fecha fin YYYY-MM-DD (opcional)
    """
    logger = logging.getLogger("django")

    try:
        # Obtener parámetros de filtro
        zone_filter = request.query_params.get("zone")
        eds_filter = request.query_params.get("eds")
        form_filter = request.query_params.get("form")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Base queryset de work orders
        work_orders_qs = WorkOrder.objects.select_related("form_template").all()

        # Aplicar filtros
        if start_date:
            work_orders_qs = work_orders_qs.filter(date__gte=start_date)
        if end_date:
            work_orders_qs = work_orders_qs.filter(date__lte=end_date)
        if form_filter:
            work_orders_qs = work_orders_qs.filter(form_template_id=form_filter)

        # Obtener todas las EDS
        eds_list = EDS.objects.all()
        if zone_filter:
            eds_list = eds_list.filter(plaza=zone_filter)
        if eds_filter:
            eds_list = eds_list.filter(id_eds_pk=eds_filter)

        eds_map = {eds.id_eds_pk: eds for eds in eds_list}
        eds_claves = set(eds_map.keys())

        # Filtrar work orders por EDS
        if zone_filter or eds_filter:
            work_orders_qs = work_orders_qs.filter(clave_eds__in=eds_claves)

        # Obtener todos los form templates activos
        form_templates = FormTemplate.objects.filter(is_active=True)
        form_templates_map = {ft.id: ft for ft in form_templates}

        # Calcular compliance grade para cada work order
        def calculate_completion_grade(work_order):
            """Calcula el grade de cumplimiento para una work order"""
            if not work_order.form_template:
                return None

            questions = list(work_order.form_template.questions.all())
            total_questions = len(questions)
            if total_questions == 0:
                return None

            answers = FormAnswers.objects.filter(work_order=work_order)
            answers_by_question = {a.question_id: a for a in answers}

            correct_answers = 0
            for question in questions:
                answer_obj = answers_by_question.get(question.id)
                if _is_answer_correct(question, answer_obj):
                    correct_answers += 1

            return (correct_answers / total_questions) * 100

        # Estructuras para agregar datos
        eds_compliance_data = defaultdict(lambda: {
            "work_orders": [],
            "forms": defaultdict(lambda: {"expected": 0, "obtained": 0, "grades": []})
        })

        form_compliance_data = defaultdict(lambda: {
            "expected": 0,
            "obtained": 0,
            "grades": [],
            "zones": set(),
            "eds_list": set()
        })

        zone_compliance_data = defaultdict(lambda: {
            "stations": set(),
            "grades": [],
            "eds_list": set(),
            "forms": set()
        })

        # Procesar cada work order
        for wo in work_orders_qs:
            clave_eds = wo.clave_eds
            if not clave_eds:
                # Intentar obtener del primer form answer
                first_answer = FormAnswers.objects.filter(
                    work_order=wo, clave_eds_fk__isnull=False
                ).exclude(clave_eds_fk='').first()
                if first_answer:
                    clave_eds = first_answer.clave_eds_fk

            if not clave_eds or clave_eds not in eds_claves:
                continue

            eds_info = eds_map.get(clave_eds)
            if not eds_info:
                continue

            zone = eds_info.plaza or "SIN ZONA"
            form_template = wo.form_template
            if not form_template:
                continue

            grade = calculate_completion_grade(wo)
            if grade is None:
                continue

            # Contar preguntas y respuestas
            total_questions = form_template.questions.count()
            total_answers = FormAnswers.objects.filter(
                work_order=wo
            ).exclude(answer__isnull=True).exclude(answer__exact="").count()

            # Agregar a datos de EDS
            eds_compliance_data[clave_eds]["work_orders"].append({
                "id": wo.id,
                "grade": grade,
                "form_template_id": form_template.id,
                "form_template_name": form_template.name,
                "date": wo.date.isoformat() if wo.date else None
            })
            eds_compliance_data[clave_eds]["forms"][form_template.id]["expected"] += total_questions
            eds_compliance_data[clave_eds]["forms"][form_template.id]["obtained"] += total_answers
            eds_compliance_data[clave_eds]["forms"][form_template.id]["grades"].append(grade)

            # Agregar a datos de formulario
            form_compliance_data[form_template.id]["expected"] += total_questions
            form_compliance_data[form_template.id]["obtained"] += total_answers
            form_compliance_data[form_template.id]["grades"].append(grade)
            form_compliance_data[form_template.id]["zones"].add(zone)
            form_compliance_data[form_template.id]["eds_list"].add(clave_eds)

            # Agregar a datos de zona
            zone_compliance_data[zone]["stations"].add(clave_eds)
            zone_compliance_data[zone]["grades"].append(grade)
            zone_compliance_data[zone]["eds_list"].add(clave_eds)
            zone_compliance_data[zone]["forms"].add(form_template.name)

        # Calcular métricas finales

        # 1. Compliance rows (por EDS)
        compliance_rows = []
        all_grades = []

        for clave_eds, data in eds_compliance_data.items():
            eds_info = eds_map.get(clave_eds)
            if not eds_info:
                continue

            eds_grades = [wo["grade"] for wo in data["work_orders"] if wo["grade"] is not None]
            if not eds_grades:
                continue

            avg_grade = sum(eds_grades) / len(eds_grades)
            all_grades.append(avg_grade)

            # Métricas por formulario para esta EDS
            metrics = []
            for form_id, form_data in data["forms"].items():
                form_template = form_templates_map.get(form_id)
                if not form_template:
                    continue

                form_grades = form_data["grades"]
                form_percent = sum(form_grades) / len(form_grades) if form_grades else 0

                metrics.append({
                    "label": form_template.name,
                    "expected": form_data["expected"],
                    "obtained": form_data["obtained"],
                    "percent": round(form_percent, 0)
                })

            if metrics:
                compliance_rows.append({
                    "clave_eds": clave_eds,
                    "zone": eds_info.plaza or "SIN ZONA",
                    "eds": eds_info.name or clave_eds,
                    "avg_grade": round(avg_grade, 2),
                    "metrics": metrics
                })

        # Ordenar por grade descendente y asignar posición
        compliance_rows.sort(key=lambda x: x["avg_grade"], reverse=True)
        for i, row in enumerate(compliance_rows):
            row["position"] = i + 1

        # 2. Compliance highlights
        total_eds = len(compliance_rows)
        excellent_count = sum(1 for row in compliance_rows if row["avg_grade"] >= 90)
        attention_count = sum(1 for row in compliance_rows if 50 <= row["avg_grade"] < 75)
        critical_count = sum(1 for row in compliance_rows if row["avg_grade"] < 50)

        compliance_highlights = [
            {
                "label": "Estaciones de Servicio",
                "value": str(total_eds),
                "chip": "Total",
                "tone": "neutral"
            },
            {
                "label": "EDS ≥90% Cumplimiento",
                "value": str(excellent_count),
                "chip": "Excelente",
                "tone": "positive"
            },
            {
                "label": "EDS 50-75% Cumplimiento",
                "value": str(attention_count),
                "chip": "Atención",
                "tone": "warning"
            },
            {
                "label": "EDS <50% Cumplimiento",
                "value": str(critical_count),
                "chip": "Crítico",
                "tone": "danger"
            }
        ]

        # 3. Overall compliance rating
        compliance_rating = round(sum(all_grades) / len(all_grades), 0) if all_grades else 0

        # 4. Zone compliance
        zone_compliance = []
        for zone_name, data in zone_compliance_data.items():
            zone_grades = data["grades"]
            zone_percent = sum(zone_grades) / len(zone_grades) if zone_grades else 0

            zone_compliance.append({
                "zone": zone_name,
                "stations": len(data["stations"]),
                "percent": round(zone_percent, 0),
                "edsList": list(data["eds_list"]),
                "forms": list(data["forms"])
            })

        zone_compliance.sort(key=lambda x: x["percent"], reverse=True)

        # 5. Type compliance (por formulario)
        type_compliance = []
        for form_id, data in form_compliance_data.items():
            form_template = form_templates_map.get(form_id)
            if not form_template:
                continue

            form_grades = data["grades"]
            form_percent = sum(form_grades) / len(form_grades) if form_grades else 0

            type_compliance.append({
                "id": form_id,
                "name": form_template.name,
                "expected": data["expected"],
                "obtained": data["obtained"],
                "percent": round(form_percent, 0),
                "zones": list(data["zones"]),
                "edsList": list(data["eds_list"])
            })

        type_compliance.sort(key=lambda x: x["percent"], reverse=True)

        # 6. Opciones de filtro
        all_zones = sorted(set(eds.plaza for eds in eds_list if eds.plaza))
        all_eds_options = [{"clave_eds": eds.id_eds_pk, "name": eds.name} for eds in eds_list]
        all_form_options = [{"id": ft.id, "name": ft.name} for ft in form_templates]

        return Response({
            "success": True,
            "complianceRating": compliance_rating,
            "complianceHighlights": compliance_highlights,
            "complianceRows": compliance_rows,
            "zoneCompliance": zone_compliance,
            "typeCompliance": type_compliance,
            "filterOptions": {
                "zones": all_zones,
                "eds": all_eds_options,
                "forms": all_form_options
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("Error en dashboard_kpis")
        return Response({
            "success": False,
            "error": "Error al calcular KPIs del dashboard",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _is_answer_correct(question, answer_obj):
    """Determina si una respuesta es correcta según el tipo de pregunta"""
    if not answer_obj or answer_obj.answer in (None, ""):
        return False

    raw_value = answer_obj.answer
    expected = getattr(question, "expected_value", None)

    if expected not in (None, ""):
        return _compare_with_expected(question.type, expected, raw_value)

    if question.type == "boolean":
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

    return True


def _compare_with_expected(qtype, expected_value, raw_value):
    """Compara la respuesta contra el expected_value según el tipo de pregunta"""
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
        return exp_bool is not None and ans_bool is not None and exp_bool == ans_bool

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

    return str(raw_value).strip().lower() == str(expected_value).strip().lower()
