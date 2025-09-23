from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .models import NGO
from .serializers import NGOSerializer, NGOApplicationSerializer, NGOPublicSerializer


class NGOViewSet(viewsets.ModelViewSet):
    queryset = NGO.objects.all()
    serializer_class = NGOSerializer
    
    def get_permissions(self):
        if self.action == 'apply':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        if self.action == 'list':
            # Only return approved NGOs for public list
            return NGO.objects.filter(approved=True)
        return super().get_queryset()
    
    def get_serializer_class(self):
        if self.action == 'apply':
            return NGOApplicationSerializer
        elif self.action == 'list':
            return NGOPublicSerializer
        return super().get_serializer_class()
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def apply(self, request):
        """NGO application endpoint"""
        serializer = NGOApplicationSerializer(data=request.data)
        if serializer.is_valid():
            # Create NGO record (not approved by default)
            ngo = serializer.save()
            
            # Optionally create a User account for NGO login
            if 'password' in request.data:
                user = User.objects.create_user(
                    username=ngo.email,
                    email=ngo.email,
                    password=request.data['password']
                )
                ngo.user = user
                ngo.save()
            
            return Response({
                'message': 'Application submitted successfully. Awaiting admin approval.',
                'ngo_id': ngo.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
