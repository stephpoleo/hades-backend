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
from django.db.models import Count, Max
from .serializers import (
    UsersSerializer,
    EDSSerializer,
    FormTemplateSerializer,
    WorkOrderSerializer,
    FormQuestionsSerializer,
    FormAnswersSerializer,
    PermissionsSerializer,
    RolesSerializer,
)


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
    pagination_class = None

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
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                eds_data = []
                for eds_item in serializer.data:
                    eds = EDS.objects.get(id_eds_pk=eds_item["id_eds_pk"])
                    eds_data.append(
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
                    )
                return self.get_paginated_response(
                    {
                        "success": True,
                        "message": f"{len(eds_data)} EDS encontradas",
                        "eds_list": eds_data,
                    }
                )
            serializer = self.get_serializer(queryset, many=True)
            eds_data = []
            for eds_item in serializer.data:
                eds = EDS.objects.get(id_eds_pk=eds_item["id_eds_pk"])
                eds_data.append(
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
                )
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
    pagination_class = None

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
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {
                        "success": True,
                        "message": f"{len(serializer.data)} usuarios encontrados",
                        "users": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
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
    """API para gestionar plantillas de formularios"""

    queryset = FormTemplate.objects.all()
    serializer_class = FormTemplateSerializer

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

    def list(self, request, *args, **kwargs):
        logger = logging.getLogger("django")
        try:
            return super().list(request, *args, **kwargs)
        except Exception as exc:
            logger.exception("Error GET /api/work-orders/")
            return Response({"detail": str(exc)}, status=500)

    # Aseguramos que kwargs (ej. image) lleguen al .save()
    def perform_create(self, serializer, **kwargs):
        serializer.save(**kwargs)

    def perform_update(self, serializer, **kwargs):
        serializer.save(**kwargs)

    def get_queryset(self):
        queryset = WorkOrder.objects.all()
        user_id = self.request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        return queryset

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
    """API para gestionar preguntas de formularios"""

    queryset = FormQuestions.objects.all()
    serializer_class = FormQuestionsSerializer


# FormAnswers ViewSet
class FormAnswersViewSet(viewsets.ModelViewSet):
    # Asegura que DRF procese multipart/form-data y lea request.FILES
    parser_classes = (MultiPartParser, FormParser)

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

    def create(self, request, *args, **kwargs):
        logger = logging.getLogger("django")
        try:
            data = request.data
            # 1) Intenta obtener archivo desde request.FILES (image/attachment/file)
            image_file = None
            for key in ["image", "attachment", "file"]:
                if key in request.FILES:
                    image_file = request.FILES[key]
                    break
            if not image_file and request.FILES:
                # Si vino con otro nombre, toma el primero
                image_file = next(iter(request.FILES.values()))

            # 2) Si hay archivo y no está en data, injértalo
            if image_file and not data.get("image"):
                try:
                    data = data.copy()
                except Exception:
                    pass
                data["image"] = image_file

            # 3) Si no hay archivo pero viene un string/base64 en data["image"], decodificarlo
            if (
                not image_file
                and data.get("image")
                and isinstance(data.get("image"), str)
            ):
                img_str = data.get("image")
                file_name = f"{uuid.uuid4().hex}.jpg"
                try:
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
                    image_file = ContentFile(decoded_file, name=file_name)
                    try:
                        data = data.copy()
                    except Exception:
                        pass
                    data["image"] = image_file
                except Exception as decode_exc:
                    logger.error(
                        "No se pudo decodificar image base64: %s",
                        decode_exc,
                        exc_info=True,
                    )
            # Si no hay archivo pero viene un string base64 en data["image"], decodificarlo
            if (
                not image_file
                and data.get("image")
                and isinstance(data.get("image"), str)
            ):
                img_str = data.get("image")
                file_name = f"{uuid.uuid4().hex}.jpg"
                try:
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
                    image_file = ContentFile(decoded_file, name=file_name)
                    try:
                        data = data.copy()
                    except Exception:
                        pass
                    data["image"] = image_file
                except Exception as decode_exc:
                    logger.error(
                        "No se pudo decodificar image base64: %s",
                        decode_exc,
                        exc_info=True,
                    )
            logger.error(
                "POST /api/form-answers/ files=%s data_keys=%s image_type=%s storage=%s bucket=%s media_url=%s",
                list(request.FILES.keys()),
                list(getattr(data, "keys", lambda: [])()),
                type(data.get("image")),
                getattr(settings, "DEFAULT_FILE_STORAGE", None),
                getattr(settings, "GS_BUCKET_NAME", None),
                getattr(settings, "MEDIA_URL", None),
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
            # Si es un solo objeto, procesar como antes
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
            if instance:
                serializer = self.get_serializer(instance, data=data, partial=True)
                serializer.is_valid(raise_exception=True)
                logger.error(
                    "FormAnswers update validated keys=%s image=%s type=%s name=%s size=%s storage=%s bucket=%s media_url=%s",
                    list(serializer.validated_data.keys()),
                    bool(serializer.validated_data.get("image")),
                    type(serializer.validated_data.get("image")),
                    getattr(serializer.validated_data.get("image"), "name", None),
                    getattr(serializer.validated_data.get("image"), "size", None),
                    getattr(settings, "DEFAULT_FILE_STORAGE", None),
                    getattr(settings, "GS_BUCKET_NAME", None),
                    getattr(settings, "MEDIA_URL", None),
                )
                obj = serializer.save(image=image_file or serializer.validated_data.get("image"))
                if image_file and not obj.image:
                    ext = (image_file.name or "upload").split(".")[-1]
                    filename = f"form_answers/{uuid.uuid4().hex}.{ext}"
                    saved_path = default_storage.save(filename, image_file)
                    obj.image.name = saved_path
                    obj.save(update_fields=["image"])
                return Response(FormAnswersSerializer(obj).data, status=200)
            else:
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                logger.error(
                    "FormAnswers create validated keys=%s image=%s type=%s name=%s size=%s storage=%s bucket=%s media_url=%s",
                    list(serializer.validated_data.keys()),
                    bool(serializer.validated_data.get("image")),
                    type(serializer.validated_data.get("image")),
                    getattr(serializer.validated_data.get("image"), "name", None),
                    getattr(serializer.validated_data.get("image"), "size", None),
                    getattr(settings, "DEFAULT_FILE_STORAGE", None),
                    getattr(settings, "GS_BUCKET_NAME", None),
                    getattr(settings, "MEDIA_URL", None),
                )
                obj = serializer.save(image=image_file or serializer.validated_data.get("image"))
                if image_file and not obj.image:
                    ext = (image_file.name or "upload").split(".")[-1]
                    filename = f"form_answers/{uuid.uuid4().hex}.{ext}"
                    saved_path = default_storage.save(filename, image_file)
                    obj.image.name = saved_path
                    obj.save(update_fields=["image"])
                headers = self.get_success_headers(serializer.data)
                return Response(FormAnswersSerializer(obj).data, status=201, headers=headers)
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

    @action(detail=True, methods=["get"], url_path="attachment")
    def attachment(self, request, pk=None):
        answer = self.get_object()
        if not answer.image:
            return Response(
                {"detail": "Esta respuesta no tiene adjunto."},
                status=status.HTTP_404_NOT_FOUND,
            )

        logger = logging.getLogger("django")
        try:
            client = storage.Client(credentials=settings.GS_CREDENTIALS)
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            blob = bucket.blob(answer.image.name)
            payload = blob.download_as_bytes()
            content_type = blob.content_type or "application/octet-stream"
        except Exception as exc:
            logger.error(
                "[FormAnswersViewSet.attachment] No se pudo descargar %s: %s",
                answer.image.name,
                exc,
                exc_info=True,
            )
            return Response(
                {
                    "detail": "No se pudo descargar el adjunto desde el almacenamiento.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response = HttpResponse(payload, content_type=content_type)
        response["Content-Length"] = str(len(payload))
        response["Content-Disposition"] = (
            f'inline; filename="{os.path.basename(answer.image.name)}"'
        )
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
    """API para gestionar roles"""

    queryset = Roles.objects.all()
    serializer_class = RolesSerializer

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
    """API para gestionar permisos"""

    queryset = Permissions.objects.all()
    serializer_class = PermissionsSerializer

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
