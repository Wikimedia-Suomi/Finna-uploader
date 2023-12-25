from rest_framework import viewsets
from images.models import FinnaImage
from images.serializers import FinnaImageSerializer
from rest_framework.views import APIView
from rest_framework.response import Response


class FinnaImageViewSet(viewsets.ModelViewSet):
    queryset = FinnaImage.objects.order_by('?')[:100]
    serializer_class = FinnaImageSerializer


class HelloWorldAPI(APIView):
    def get(self, request):
        return Response({"message": "Hello from Django REST API!"})
