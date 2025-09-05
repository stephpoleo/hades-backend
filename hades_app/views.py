from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Users, EDS, FormTemplate, WorkOrder, FormQuestions, FormAnswers, Roles, Permissions
from .serializers import (UsersSerializer, EDSSerializer, FormTemplateSerializer, 
                         WorkOrderSerializer, FormQuestionsSerializer, FormAnswersSerializer,
                         RolesSerializer, PermissionsSerializer)

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
        """Listar EDS con mensaje"""
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
                        'status': eds.plaza_status
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
                    'status': eds.plaza_status
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
    queryset = Users.objects.filter(usr_status=True)  # Solo usuarios activos
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
                    'status': instance.usr_status
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
        """Listar usuarios con mensaje"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                users_data = []
                for user_data in serializer.data:
                    user = Users.objects.get(id_usr_pk=user_data['id_usr_pk'])
                    users_data.append({
                        'id': user.id_usr_pk,
                        'name': user.name,
                        'email': user.email,
                        'role': user.role_name,
                        'status': user.usr_status
                    })
                
                return self.get_paginated_response({
                    'success': True,
                    'message': f'{len(users_data)} usuarios encontrados',
                    'users': users_data
                })
            
            serializer = self.get_serializer(queryset, many=True)
            users_data = []
            for user_data in serializer.data:
                user = Users.objects.get(id_usr_pk=user_data['id_usr_pk'])
                users_data.append({
                    'id': user.id_usr_pk,
                    'name': user.name,
                    'email': user.email,
                    'role': user.role_name,
                    'status': user.usr_status
                })
            
            return Response({
                'success': True,
                'message': f'{len(users_data)} usuarios encontrados',
                'users': users_data
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


# API endpoints específicos
@api_view(['GET'])
def users_list(request):
    """API endpoint para listar usuarios"""
    users = Users.objects.all()
    data = []
    for user in users:
        data.append({
            'id': user.id_usr_pk,
            'name': user.name,
            'email': user.email,
            'status': user.usr_status,
            'role': user.role_name,
        })
    return JsonResponse(data, safe=False)


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
    """API para gestionar respuestas de formularios"""
    queryset = FormAnswers.objects.all()
    serializer_class = FormAnswersSerializer


# Roles ViewSet
class RolesViewSet(viewsets.ModelViewSet):
    """API para gestionar roles"""
    queryset = Roles.objects.all()
    serializer_class = RolesSerializer

    def create(self, request, *args, **kwargs):
        """Crear nuevo rol con mensaje de confirmación"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                role = serializer.save()
                return Response({
                    'success': True,
                    'message': f'Rol "{role.name}" creado exitosamente',
                    'role': {
                        'id': role.id_rol_pk,
                        'name': role.name,
                        'status': role.role_status
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'error': 'Datos de rol inválidos',
                    'message': 'Por favor verifica los campos requeridos',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al crear rol',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        """Obtener un rol específico con mensaje"""
        try:
            instance = self.get_object()
            return Response({
                'success': True,
                'message': f'Rol "{instance.name}" encontrado',
                'role': {
                    'id': instance.id_rol_pk,
                    'name': instance.name,
                    'status': instance.role_status
                }
            }, status=status.HTTP_200_OK)
        except Roles.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Rol no encontrado',
                'message': 'El rol solicitado no existe'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al obtener rol',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Actualizar rol con mensaje de confirmación"""
        try:
            instance = self.get_object()
            old_name = instance.name
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                role = serializer.save()
                return Response({
                    'success': True,
                    'message': f'Rol "{old_name}" actualizado exitosamente',
                    'role': {
                        'id': role.id_rol_pk,
                        'name': role.name,
                        'status': role.role_status
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Datos de actualización inválidos',
                    'message': 'Por favor verifica los campos a actualizar',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Roles.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Rol no encontrado',
                'message': 'El rol que intentas actualizar no existe'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al actualizar rol',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, *args, **kwargs):
        """Listar roles con mensaje"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                roles_data = []
                for role_item in serializer.data:
                    role = Roles.objects.get(id_rol_pk=role_item['id_rol_pk'])
                    roles_data.append({
                        'id': role.id_rol_pk,
                        'name': role.name,
                        'status': role.role_status
                    })
                return self.get_paginated_response({
                    'success': True,
                    'message': f'{len(roles_data)} roles encontrados',
                    'roles': roles_data
                })
            serializer = self.get_serializer(queryset, many=True)
            roles_data = []
            for role_item in serializer.data:
                role = Roles.objects.get(id_rol_pk=role_item['id_rol_pk'])
                roles_data.append({
                    'id': role.id_rol_pk,
                    'name': role.name,
                    'status': role.role_status
                })
            return Response({
                'success': True,
                'message': f'{len(roles_data)} roles encontrados',
                'roles': roles_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al listar roles',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Eliminar rol con mensaje de confirmación"""
        try:
            instance = self.get_object()
            role_name = instance.name
            role_id = instance.id_rol_pk
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': f'Rol "{role_name}" (ID: {role_id}) eliminado exitosamente',
                'deleted_role': {
                    'id': role_id,
                    'name': role_name
                }
            }, status=status.HTTP_200_OK)
        except Roles.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Rol no encontrado',
                'message': 'El rol que intentas eliminar no existe'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al eliminar rol',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Permissions ViewSet
class PermissionsViewSet(viewsets.ModelViewSet):
    """API para gestionar permisos"""
    queryset = Permissions.objects.all()
    serializer_class = PermissionsSerializer

    def create(self, request, *args, **kwargs):
        """Crear nuevo permiso con mensaje de confirmación"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                permission = serializer.save()
                return Response({
                    'success': True,
                    'message': f'Permiso "{permission.name}" creado exitosamente',
                    'permission': {
                        'id': permission.id_permissions_pk,
                        'name': permission.name,
                        'status': permission.permission_status
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'success': False,
                    'error': 'Datos de permiso inválidos',
                    'message': 'Por favor verifica los campos requeridos',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al crear permiso',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        """Obtener un permiso específico con mensaje"""
        try:
            instance = self.get_object()
            return Response({
                'success': True,
                'message': f'Permiso "{instance.name}" encontrado',
                'permission': {
                    'id': instance.id_permissions_pk,
                    'name': instance.name,
                    'status': instance.permission_status
                }
            }, status=status.HTTP_200_OK)
        except Permissions.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Permiso no encontrado',
                'message': 'El permiso solicitado no existe'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al obtener permiso',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Actualizar permiso con mensaje de confirmación"""
        try:
            instance = self.get_object()
            old_name = instance.name
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if serializer.is_valid():
                permission = serializer.save()
                return Response({
                    'success': True,
                    'message': f'Permiso "{old_name}" actualizado exitosamente',
                    'permission': {
                        'id': permission.id_permissions_pk,
                        'name': permission.name,
                        'status': permission.permission_status
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': 'Datos de actualización inválidos',
                    'message': 'Por favor verifica los campos a actualizar',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Permissions.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Permiso no encontrado',
                'message': 'El permiso que intentas actualizar no existe'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al actualizar permiso',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, *args, **kwargs):
        """Listar permisos con mensaje"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                permissions_data = []
                for perm_item in serializer.data:
                    permission = Permissions.objects.get(id_permissions_pk=perm_item['id_permissions_pk'])
                    permissions_data.append({
                        'id': permission.id_permissions_pk,
                        'name': permission.name,
                        'status': permission.permission_status
                    })
                return self.get_paginated_response({
                    'success': True,
                    'message': f'{len(permissions_data)} permisos encontrados',
                    'permissions': permissions_data
                })
            serializer = self.get_serializer(queryset, many=True)
            permissions_data = []
            for perm_item in serializer.data:
                permission = Permissions.objects.get(id_permissions_pk=perm_item['id_permissions_pk'])
                permissions_data.append({
                    'id': permission.id_permissions_pk,
                    'name': permission.name,
                    'status': permission.permission_status
                })
            return Response({
                'success': True,
                'message': f'{len(permissions_data)} permisos encontrados',
                'permissions': permissions_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al listar permisos',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Eliminar permiso con mensaje de confirmación"""
        try:
            instance = self.get_object()
            permission_name = instance.name
            permission_id = instance.id_permissions_pk
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': f'Permiso "{permission_name}" (ID: {permission_id}) eliminado exitosamente',
                'deleted_permission': {
                    'id': permission_id,
                    'name': permission_name
                }
            }, status=status.HTTP_200_OK)
        except Permissions.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Permiso no encontrado',
                'message': 'El permiso que intentas eliminar no existe'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Error al eliminar permiso',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
