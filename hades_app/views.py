from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .migrations.models import EDS
from rest_framework import serializers

class EDSSerializer(serializers.ModelSerializer):
    class Meta:
        model = EDS
        fields = '__all__'

class EDSView(APIView):
    """CRUD para EDS"""

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            id = request.query_params.get("id")
            if id is not None:
                eds = EDS.objects.get(pk=id)
                serializer = EDSSerializer(eds)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            if e.args and "matching query does not exist" in str(e):
                return Response(
                    {"message": "Wrong EDS id or does not exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                eds = EDS.objects.all()
                serializer = EDSSerializer(eds, many=True)
                if eds.exists():
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"message": "EDS not found"},
                        status=status.HTTP_200_OK,
                    )

    def post(self, request):
        serializer = EDSSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "New EDS created", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        id = request.query_params.get("id")
        try:
            eds_instance = EDS.objects.get(pk=id)
        except Exception:
            return Response(
                {"message": "Wrong EDS id or does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EDSSerializer(eds_instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "EDS updated", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        id = request.query_params.get("id")
        try:
            eds_instance = EDS.objects.get(pk=id)
        except Exception:
            return Response(
                {"message": "Wrong EDS id or does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        eds_instance.delete()
        return Response(
            {"message": f"EDS {id} was deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )