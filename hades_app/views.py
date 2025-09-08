from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import Users, EDS, FormTemplate, WorkOrder, FormQuestions, FormAnswers
from django.db.models import Count, Max
from .serializers import (UsersSerializer, EDSSerializer, FormTemplateSerializer, 
                         WorkOrderSerializer, FormQuestionsSerializer, FormAnswersSerializer)

# EDS ViewSet - Standardized CRUD
class EDSViewSet(viewsets.ModelViewSet):
    """API para gestionar EDS (Estaciones de Servicio)"""
    queryset = EDS.objects.all()
    serializer_class = EDSSerializer
    
    def create(self, request, *args, **kwargs):
        """Crear nueva EDS con mensaje de confirmación"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                eds = serializer.save()
                
                return Response({
                    'success': True,
                    'message': f'EDS "{eds.name}" creada exitosamente',
                    'eds': {
                        'id': eds.id_eds_pk,
                        'name': eds.name,
                        'plaza': eds.plaza,
                        'state': eds.state,
                        'municipality': eds.municipality
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'error': 'Datos de EDS inválidos',
                    'message': 'Por favor verifica los campos requeridos',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al crear EDS',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        """Obtener una EDS específica con mensaje"""
        try:
            instance = self.get_object()
            
            return Response({
                'success': True,
                'message': f'EDS "{instance.name}" encontrada',
                'eds': {
                    'id': instance.id_eds_pk,
                    'name': instance.name,
                    'plaza': instance.plaza,
                    'state': instance.state,
                    'municipality': instance.municipality,
                    'zip_code': instance.zip_code,
                    'plaza_status': instance.plaza_status,
                    'longitude': str(instance.long_eds) if instance.long_eds else None,
                    'latitude': str(instance.latit_eds) if instance.latit_eds else None
                }
            }, status=status.HTTP_200_OK)
            
        except EDS.DoesNotExist:
            return Response({
                'success': False,
                'error': 'EDS no encontrada',
                'message': 'La EDS solicitada no existe'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al obtener EDS',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Actualizar EDS con mensaje de confirmación"""
        try:
            instance = self.get_object()
            old_name = instance.name
            
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                eds = serializer.save()
                
                return Response({
                    'success': True,
                    'message': f'EDS "{old_name}" actualizada exitosamente',
                    'eds': {
                        'id': eds.id_eds_pk,
                        'name': eds.name,
                        'plaza': eds.plaza,
                        'state': eds.state,
                        'municipality': eds.municipality
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Datos de actualización inválidos',
                    'message': 'Por favor verifica los campos a actualizar',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except EDS.DoesNotExist:
            return Response({
                'success': False,
                'error': 'EDS no encontrada',
                'message': 'La EDS que intentas actualizar no existe'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al actualizar EDS',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def list(self, request, *args, **kwargs):
        """Listar EDS con mensaje (incluyendo longitud y latitud)"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                eds_data = []
                for eds_item in serializer.data:
                    eds = EDS.objects.get(id_eds_pk=eds_item['id_eds_pk'])
                    eds_data.append({
                        'id': eds.id_eds_pk,
                        'name': eds.name,
                        'plaza': eds.plaza,
                        'state': eds.state,
                        'municipality': eds.municipality,
                        'status': eds.plaza_status,
                        'longitude': str(eds.long_eds) if eds.long_eds else None,
                        'latitude': str(eds.latit_eds) if eds.latit_eds else None
                    })
                return self.get_paginated_response({
                    'success': True,
                    'message': f'{len(eds_data)} EDS encontradas',
                    'eds_list': eds_data
                })
            serializer = self.get_serializer(queryset, many=True)
            eds_data = []
            for eds_item in serializer.data:
                eds = EDS.objects.get(id_eds_pk=eds_item['id_eds_pk'])
                eds_data.append({
                    'id': eds.id_eds_pk,
                    'name': eds.name,
                    'plaza': eds.plaza,
                    'state': eds.state,
                    'municipality': eds.municipality,
                    'status': eds.plaza_status,
                    'longitude': str(eds.long_eds) if eds.long_eds else None,
                    'latitude': str(eds.latit_eds) if eds.latit_eds else None
                })
            return Response({
                'success': True,
                'message': f'{len(eds_data)} EDS encontradas',
                'eds_list': eds_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al listar EDS',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar EDS con mensaje de confirmación"""
        try:
            instance = self.get_object()
            eds_name = instance.name
            eds_id = instance.id_eds_pk
            
            # Realizar la eliminación
            self.perform_destroy(instance)
            
            return Response({
                'success': True,
                'message': f'EDS "{eds_name}" (ID: {eds_id}) eliminada exitosamente',
                'deleted_eds': {
                    'id': eds_id,
                    'name': eds_name
                }
            }, status=status.HTTP_200_OK)
            
        except EDS.DoesNotExist:
            return Response({
                'success': False,
                'error': 'EDS no encontrada',
                'message': 'La EDS que intentas eliminar no existe'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al eliminar EDS',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Users Views
class UsersViewSet(viewsets.ModelViewSet):
    """API para gestionar usuarios"""
    queryset = Users.objects.all()
    serializer_class = UsersSerializer
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo usuario con mensaje de confirmación"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                if 'password' in request.data:
                    user.set_password(request.data['password'])
                    user.save()
                
                return Response({
                    'success': True,
                    'message': f'Usuario "{user.name}" creado exitosamente',
                    'user': {
                        'id': user.id_usr_pk,
                        'name': user.name,
                        'email': user.email,
                        'role': user.role_name
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'error': 'Datos de usuario inválidos',
                    'message': 'Por favor verifica los campos requeridos',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al crear usuario',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        """Obtener un usuario específico con mensaje"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            
            return Response({
                'success': True,
                'message': f'Usuario "{instance.name}" encontrado',
                'user': {
                    'id': instance.id_usr_pk,
                    'name': instance.name,
                    'email': instance.email,
                    'role': instance.role_name,
                    'status': instance.usr_status,
                    'eds_info': serializer.data.get('eds_info')
                }
            }, status=status.HTTP_200_OK)
            
        except Users.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Usuario no encontrado',
                'message': 'El usuario solicitado no existe'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al obtener usuario',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, *args, **kwargs):
        """Actualizar usuario con mensaje de confirmación"""
        try:
            instance = self.get_object()
            old_name = instance.name
            
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                user = serializer.save()
                
                # Si se actualiza la contraseña
                if 'password' in request.data:
                    user.set_password(request.data['password'])
                    user.save()
                
                return Response({
                    'success': True,
                    'message': f'Usuario "{old_name}" actualizado exitosamente',
                    'user': {
                        'id': user.id_usr_pk,
                        'name': user.name,
                        'email': user.email,
                        'role': user.role_name
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Datos de actualización inválidos',
                    'message': 'Por favor verifica los campos a actualizar',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Users.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Usuario no encontrado',
                'message': 'El usuario que intentas actualizar no existe'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al actualizar usuario',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def list(self, request, *args, **kwargs):
        """Listar usuarios con mensaje y todos los campos del serializer (incluyendo eds_info)"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response({
                    'success': True,
                    'message': f'{len(serializer.data)} usuarios encontrados',
                    'users': serializer.data
                })

            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'message': f'{len(serializer.data)} usuarios encontrados',
                'users': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al listar usuarios',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar usuario con mensaje de confirmación"""
        try:
            instance = self.get_object()
            user_name = instance.name
            user_id = instance.id_usr_pk
            
            # Realizar la eliminación
            self.perform_destroy(instance)
            
            return Response({
                'success': True,
                'message': f'Usuario "{user_name}" (ID: {user_id}) eliminado exitosamente',
                'deleted_user': {
                    'id': user_id,
                    'name': user_name
                }
            }, status=status.HTTP_200_OK)
            
        except Users.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Usuario no encontrado',
                'message': 'El usuario que intentas eliminar no existe'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al eliminar usuario',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# FormTemplate ViewSet
class FormTemplateViewSet(viewsets.ModelViewSet):
    """API para gestionar plantillas de formularios"""
    queryset = FormTemplate.objects.all()
    serializer_class = FormTemplateSerializer


# WorkOrder ViewSet
class WorkOrderViewSet(viewsets.ModelViewSet):
    """API para gestionar órdenes de trabajo"""
    queryset = WorkOrder.objects.all()
    serializer_class = WorkOrderSerializer


# FormQuestions ViewSet
class FormQuestionsViewSet(viewsets.ModelViewSet):
    """API para gestionar preguntas de formularios"""
    queryset = FormQuestions.objects.all()
    serializer_class = FormQuestionsSerializer


# FormAnswers ViewSet
class FormAnswersViewSet(viewsets.ModelViewSet):
    @action(detail=False, methods=['get'], url_path='by-workorder')
    def by_workorder(self, request):
        """
        Devuelve todas las respuestas para un work_order_id dado.
        Uso: /api/form-answers/by-workorder/?work_order_id=1
        """
        work_order_id = request.query_params.get('work_order_id')
        if not work_order_id:
            return Response({'detail': 'work_order_id es requerido como parámetro.'}, status=400)
        queryset = self.get_queryset().filter(work_order_id=work_order_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    from rest_framework.decorators import action
    from django.db.models import Count, Max

    @action(detail=False, methods=['delete'], url_path='delete-duplicates')
    def delete_duplicates(self, request):
        """
        Elimina respuestas duplicadas por (question_id, work_order_id), dejando solo la más reciente (mayor id).
        """
        # Agrupa por question_id y work_order_id, cuenta y obtiene el id máximo (más reciente)
        duplicates = (
            FormAnswers.objects.values('question_id', 'work_order_id')
            .annotate(count=Count('id'), max_id=Max('id'))
            .filter(count__gt=1)
        )
        total_deleted = 0
        for dup in duplicates:
            # Obtiene todos los ids menos el más reciente
            to_delete = (
                FormAnswers.objects
                .filter(question_id=dup['question_id'], work_order_id=dup['work_order_id'])
                .exclude(id=dup['max_id'])
            )
            deleted, _ = to_delete.delete()
            total_deleted += deleted
        return Response({'deleted': total_deleted, 'message': 'Respuestas duplicadas eliminadas.'})
    """API para gestionar respuestas de formularios"""
    queryset = FormAnswers.objects.all()
    serializer_class = FormAnswersSerializer

    def create(self, request, *args, **kwargs):
        # Extrae los IDs de pregunta y work_order del request
        question_id = request.data.get('question_id')
        work_order_id = request.data.get('work_order_id')
        if not question_id or not work_order_id:
            return Response({'detail': 'question_id y work_order_id son requeridos.'}, status=400)

        # Busca si ya existe una respuesta para esa combinación
        instance = FormAnswers.objects.filter(question_id=question_id, work_order_id=work_order_id).first()
        if instance:
            # Si existe, actualiza el registro existente
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=200)
        else:
            # Si no existe, crea uno nuevo
            return super().create(request, *args, **kwargs)
