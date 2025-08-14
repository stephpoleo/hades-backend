from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Users
from .serializers import UsersSerializer

# Create your views here.

# API ViewSets for REST endpoints
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
