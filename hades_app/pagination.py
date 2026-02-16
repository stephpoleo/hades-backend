"""
Clases de paginación para la API de Hades.

Proporciona paginación estándar y personalizada para diferentes casos de uso.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Paginación estándar para listados.

    - page_size: 20 registros por defecto
    - page_size_query_param: permite al frontend especificar el tamaño
    - max_page_size: límite máximo de 100 registros por página

    Uso en frontend:
        GET /api/work-orders/?page=1&page_size=20
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        Respuesta paginada con metadata adicional.
        """
        return Response({
            'success': True,
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })


class LargePagination(PageNumberPagination):
    """
    Paginación para listados grandes (EDS, usuarios).

    - page_size: 20 registros por defecto
    - Útil para listados con muchos registros
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })


class SmallPagination(PageNumberPagination):
    """
    Paginación para listados pequeños o móviles.

    - page_size: 20 registros por defecto
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })
