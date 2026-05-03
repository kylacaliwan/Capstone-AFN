from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from django.utils import timezone
from .models import Notification, FirebaseToken
from .serializers import NotificationSerializer, FirebaseTokenSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    
    def get_queryset(self):
        # Return only notifications for the current user
        return Notification.objects.filter(user=self.request.user).select_related(
            'user', 'ticket', 'request'
        ).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed('POST')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({
            'status': 'Notification marked as read',
            'notification_id': notification.id,
            'read_at': notification.read_at,
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        read_at = timezone.now()
        updated_count = self.get_queryset().filter(status='unread').update(
            status='read',
            read_at=read_at,
        )
        return Response({
            'status': 'All notifications marked as read',
            'updated_count': updated_count,
            'read_at': read_at,
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = self.get_queryset().filter(status='unread').count()
        return Response({'unread_count': count})


class FirebaseTokenViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Firebase Cloud Messaging tokens"""
    serializer_class = FirebaseTokenSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return only tokens for the current user"""
        return FirebaseToken.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register or update a Firebase token"""
        fcm_token = request.data.get('fcm_token')
        device_name = request.data.get('device_name', '')
        device_type = request.data.get('device_type', 'web')
        
        if not fcm_token:
            return Response(
                {'error': 'fcm_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Browser/device tokens are unique across users, so reuse the record if
        # the same device signs into a different account.
        token, created = FirebaseToken.objects.update_or_create(
            fcm_token=fcm_token,
            defaults={
                'user': request.user,
                'device_name': device_name,
                'device_type': device_type,
                'is_active': True
            }
        )
        
        serializer = self.get_serializer(token)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def deregister(self, request):
        """Deregister a Firebase token"""
        fcm_token = request.data.get('fcm_token')
        
        if not fcm_token:
            return Response(
                {'error': 'fcm_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            token = FirebaseToken.objects.get(user=request.user, fcm_token=fcm_token)
            token.is_active = False
            token.save()
            return Response({'status': 'Token deregistered successfully'})
        except FirebaseToken.DoesNotExist:
            return Response(
                {'error': 'Token not found'},
                status=status.HTTP_404_NOT_FOUND
            )
