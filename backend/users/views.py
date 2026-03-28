from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Avg, Count, Q
from django.utils import timezone
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

from .models import User
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    UserUpdateSerializer, SelfUserUpdateSerializer,
    TechnicianLocationUpdateSerializer, PasswordChangeSerializer
)
from .permissions import (
    IsAdmin, IsSupervisor, IsTechnician, IsClient,
    IsAdminOrSupervisor, IsAdminOrSupervisorOrTechnician,
    IsOwnerOrAdmin, CanManageUsers
)
from services.models import ServiceRequest, ServiceTicket, ServiceType
from services.serializers import ServiceTypeSerializer
from services.models import TechnicianSkill


def authenticate_user_credentials(identifier, password):
    """
    Accept username or email and self-heal legacy plain-text passwords.
    """
    user = authenticate(username=identifier, password=password)
    if user:
        return user

    lookup_value = (identifier or '').strip()
    if not lookup_value:
        return None

    def authenticate_candidate(candidate):
        if not candidate or not candidate.is_active:
            return None

        # Some older records were saved with raw passwords. If we detect a raw
        # match, convert it to a proper Django hash and continue with normal auth.
        if '$' not in (candidate.password or '') and candidate.password == password:
            candidate.set_password(password)
            candidate.save(update_fields=['password'])

        return authenticate(username=candidate.username, password=password)

    for candidate in User.objects.filter(email__iexact=lookup_value).order_by('id'):
        authenticated_user = authenticate_candidate(candidate)
        if authenticated_user:
            return authenticated_user

    username_candidate = User.objects.filter(username__iexact=lookup_value).first()
    return authenticate_candidate(username_candidate)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.role in ['admin', 'supervisor']


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['login', 'register']:
            return [permissions.AllowAny()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageUsers()]
        elif self.action == 'list':
            return [IsAdminOrSupervisor()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        queryset = User.objects.none()

        # Support filtered users by query param from admin dashboard
        role_filter = self.request.query_params.get('role')

        if user.role == 'admin':
            queryset = User.objects.all()
        elif user.role == 'supervisor':
            # Supervisors can see all users except other supervisors/admins
            queryset = User.objects.exclude(role__in=['admin', 'supervisor'])
        elif user.role in ['technician', 'client']:
            queryset = User.objects.filter(id=user.id)

        if role_filter:
            queryset = queryset.filter(role=role_filter)

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'register':
            return UserRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """Get current user info"""
        if request.method.lower() == 'patch':
            serializer = SelfUserUpdateSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(UserSerializer(request.user).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """Register a new user"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """User login"""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate_user_credentials(
                serializer.validated_data['username'],
                serializer.validated_data['password']
            )
            if user:
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.key
                })
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """User logout"""
        try:
            request.user.auth_token.delete()
            return Response({'message': 'Logged out successfully'})
        except Token.DoesNotExist:
            # Token already deleted or never created — still a clean logout
            return Response({'message': 'Logged out successfully'})
        except Exception as e:
            logger.error(f"Logout error for user {request.user.id}: {e}", exc_info=True)
            return Response({'error': 'Error logging out'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change password for the authenticated user"""
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class AuthViewSet(viewsets.ViewSet):
    """ViewSet for authentication endpoints that don't require authentication"""
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['login', 'test_connection']:
            return [permissions.AllowAny()]
        if self.action in ['update_status', 'set_available']:
            return [IsAdmin()]
        if self.action in ['technicians', 'clients']:
            return [IsAdminOrSupervisor()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """User login"""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate_user_credentials(
                serializer.validated_data['username'],
                serializer.validated_data['password']
            )
            if user:
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'user': UserSerializer(user).data,
                    'token': token.key
                })
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def test_connection(self, request):
        """Test endpoint to verify frontend-backend connection"""
        return Response({'message': 'Backend is connected!', 'status': 'success'})

    @action(detail=False, methods=['post'])
    def verify_token(self, request):
        """Verify if token is valid"""
        return Response({'valid': True})
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update user status (admin only)"""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        if new_status in ['active', 'inactive']:
            user.status = new_status
            user.save()
            return Response({'status': 'Status updated'})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def set_available(self, request, pk=None):
        """Set technician availability"""
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user.role != 'technician':
            return Response({'error': 'Only technicians can set availability'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_available = request.data.get('is_available', True)
        user.is_available = is_available
        user.save()
        
        return Response({'is_available': user.is_available})
    
    @action(detail=False, methods=['get'])
    def technicians(self, request):
        """Get all technicians"""
        technicians = User.objects.filter(role='technician').values(
            'id', 'username', 'email', 'phone', 'current_latitude', 
            'current_longitude', 'is_available', 'status'
        )
        return Response(technicians)
    
    @action(detail=False, methods=['get'])
    def clients(self, request):
        """Get all clients"""
        clients = User.objects.filter(role='client').values(
            'id', 'username', 'email', 'phone', 'address', 'status'
        )
        return Response(clients)


class AdminTechniciansViewSet(viewsets.ViewSet):
    """ViewSet for admin technician management"""
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsAdminOrSupervisor()]
        return [permissions.IsAuthenticated(), IsAdmin()]

    def list(self, request):
        """Get all technicians"""
        technicians = User.objects.filter(role='technician')
        serializer = UserSerializer(technicians, many=True)
        skills_by_technician = {}
        for skill in TechnicianSkill.objects.filter(technician__in=technicians).select_related('service_type'):
            skills_by_technician.setdefault(skill.technician_id, []).append(skill.service_type.name)

        technician_data = []
        for technician_data_item in serializer.data:
            skill_names = skills_by_technician.get(technician_data_item['id'], [])
            technician_data.append({
                **technician_data_item,
                'skills': skill_names,
                'skill': skill_names[0] if skill_names else ''
            })
        return Response(technician_data)

    def create(self, request):
        """Create a new technician"""
        serializer = UserRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            user.role = 'technician'
            user.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Get a specific technician"""
        try:
            technician = User.objects.get(id=pk, role='technician')
            serializer = UserSerializer(technician)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'Technician not found'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        """Update a technician"""
        try:
            technician = User.objects.get(id=pk, role='technician')
            serializer = UserUpdateSerializer(technician, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(UserSerializer(technician).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'Technician not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        """Delete a technician"""
        try:
            technician = User.objects.get(id=pk, role='technician')
            technician.delete()
            return Response({'message': 'Technician deleted'}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({'error': 'Technician not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminClientsViewSet(viewsets.ViewSet):
    """ViewSet for admin client management"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def list(self, request):
        """Get all clients"""
        clients = User.objects.filter(role='client')
        serializer = UserSerializer(clients, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Create a new client"""
        serializer = UserRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            user.role = 'client'
            user.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Get a specific client"""
        try:
            client = User.objects.get(id=pk, role='client')
            serializer = UserSerializer(client)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        """Update a client"""
        try:
            client = User.objects.get(id=pk, role='client')
            serializer = UserUpdateSerializer(client, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(UserSerializer(client).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        """Delete a client"""
        try:
            client = User.objects.get(id=pk, role='client')
            client.delete()
            return Response({'message': 'Client deleted'}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminUsersViewSet(viewsets.ViewSet):
    """ViewSet for admin all users management"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def list(self, request):
        """Get all users"""
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Create a new user"""
        serializer = UserRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Get a specific user"""
        try:
            user = User.objects.get(id=pk)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        """Update a user"""
        try:
            user = User.objects.get(id=pk)
            serializer = UserUpdateSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(UserSerializer(user).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        """Deactivate a user without deleting their record"""
        try:
            user = User.objects.get(id=pk)
            user.status = 'inactive'
            user.is_active = False
            user.save(update_fields=['status', 'is_active'])
            return Response({'message': 'User deactivated'})
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminSettingsViewSet(viewsets.ViewSet):
    """ViewSet for admin settings"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def list(self, request):
        """Get admin settings"""
        settings_data = {
            'enableNotifications': True,
            'defaultTimeZone': 'Africa/Lagos',
            'systemName': 'AFN Service Management',
            'supportEmail': 'support@afn.com',
            'maxTechnicianAssignments': 5,
            'autoDispatchEnabled': True,
            'smsNotificationsEnabled': True,
        }
        return Response(settings_data)

    def update(self, request, pk=None):
        """Update admin settings via the router's standard PUT endpoint"""
        return Response({
            'success': True,
            'message': 'Settings updated successfully',
            'settings': request.data
        })

    @action(detail=False, methods=['put'])
    def update_settings(self, request):
        """Update admin settings"""
        return self.update(request)


class AdminServicesViewSet(viewsets.ViewSet):
    """ViewSet for admin service management"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def list(self, request):
        """Get all service types"""
        services = ServiceType.objects.all()
        serializer = ServiceTypeSerializer(services, many=True)
        return Response(serializer.data)

    def create(self, request):
        """Create a new service type"""
        serializer = ServiceTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Get a specific service type"""
        try:
            service = ServiceType.objects.get(id=pk)
            serializer = ServiceTypeSerializer(service)
            return Response(serializer.data)
        except ServiceType.DoesNotExist:
            return Response({'error': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        """Update a service type"""
        try:
            service = ServiceType.objects.get(id=pk)
            serializer = ServiceTypeSerializer(service, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ServiceType.DoesNotExist:
            return Response({'error': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        """Delete a service type"""
        try:
            service = ServiceType.objects.get(id=pk)
            service.delete()
            return Response({'message': 'Service deleted'}, status=status.HTTP_204_NO_CONTENT)
        except ServiceType.DoesNotExist:
            return Response({'error': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminAnalyticsViewSet(viewsets.ViewSet):
    """ViewSet for admin analytics"""
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    FORECAST_WINDOW_DAYS = 7
    HISTORY_WINDOW_DAYS = 42
    RECENT_WINDOW_DAYS = 14
    FORECAST_JOBS_PER_TECHNICIAN = 5
    BUSIEST_MONTHS_WINDOW = 12
    BUSIEST_WEEKS_WINDOW = 12
    LOCATION_TREND_WINDOW_DAYS = 30
    ANALYTICS_LIST_LIMIT = 6

    def list(self, request):
        """Get descriptive and predictive analytics based on live system data."""
        today = timezone.now().date()
        overview = self._build_overview()
        service_breakdown = self._build_service_breakdown(today)
        top_technician = self._build_top_technician(today)
        completion_trend = self._build_completion_trend(today)
        predictive_summary, service_forecasts, daily_forecast = self._build_predictive_analytics(today)
        busiest_months = self._build_busiest_months(today)
        busiest_weeks = self._build_busiest_weeks(today)
        top_requested_service_types = self._build_top_requested_service_types(service_breakdown)
        city_completion_trends, province_completion_trends = self._build_location_completion_trends(today)

        return Response({
            'generatedAt': timezone.now(),
            'overview': overview,
            'totalRequests': overview['totalRequests'],
            'completedRequests': overview['completedRequests'],
            'pendingRequests': overview['pendingRequests'],
            'activeUsers': overview['activeUsers'],
            'activeTechnicians': overview['activeTechnicians'],
            'avgResponseTime': overview['avgResponseTimeHours'],
            'avgCompletionTime': overview['avgCompletionTimeHours'],
            'totalRevenue': 0,
            'jobCountByService': service_breakdown,
            'topTech': top_technician,
            'completionTrend': completion_trend,
            'predictiveSummary': predictive_summary,
            'serviceForecasts': service_forecasts,
            'dailyForecast': daily_forecast,
            'busiestMonths': busiest_months,
            'busiestWeeks': busiest_weeks,
            'topRequestedServiceTypes': top_requested_service_types,
            'cityCompletionTrends': city_completion_trends,
            'provinceCompletionTrends': province_completion_trends,
        })

    def _build_overview(self):
        completed_tickets = ServiceTicket.objects.filter(status='Completed')
        active_tickets = ServiceTicket.objects.filter(status__in=['Not Started', 'In Progress', 'On Hold'])
        assigned_tickets = ServiceTicket.objects.filter(assigned_at__isnull=False).select_related('request')

        return {
            'totalRequests': ServiceRequest.objects.count(),
            'completedRequests': completed_tickets.count(),
            'pendingRequests': ServiceRequest.objects.filter(status__in=['Pending', 'Approved']).count(),
            'activeTickets': active_tickets.count(),
            'activeUsers': User.objects.filter(status='active', is_active=True).count(),
            'activeTechnicians': User.objects.filter(
                role='technician',
                status='active',
                is_active=True
            ).count(),
            'avgResponseTimeHours': self._average_response_time_hours(assigned_tickets),
            'avgCompletionTimeHours': self._average_completion_time_hours(
                completed_tickets.select_related('request')
            ),
        }

    def _average_response_time_hours(self, tickets):
        durations = []
        for ticket in tickets:
            if ticket.assigned_at and ticket.request and ticket.request.request_date:
                durations.append(
                    (ticket.assigned_at - ticket.request.request_date).total_seconds() / 3600
                )
        if not durations:
            return 0
        return round(sum(durations) / len(durations), 1)

    def _average_completion_time_hours(self, tickets):
        durations = []
        for ticket in tickets:
            if not ticket.completed_date:
                continue
            baseline = ticket.start_time or getattr(ticket.request, 'request_date', None)
            if baseline:
                durations.append((ticket.completed_date - baseline).total_seconds() / 3600)
        if not durations:
            return 0
        return round(sum(durations) / len(durations), 1)

    def _build_service_breakdown(self, today):
        recent_start = today - timezone.timedelta(days=29)
        breakdown = (
            ServiceRequest.objects.values('service_type_id', 'service_type__name')
            .annotate(
                count=Count('id'),
                recent_requests=Count('id', filter=Q(request_date__date__gte=recent_start)),
                completed_requests=Count('id', filter=Q(status='Completed'))
            )
            .order_by('-count', 'service_type__name')
        )

        return [
            {
                'id': row['service_type_id'],
                'name': row['service_type__name'] or 'Unknown Service',
                'count': row['count'],
                'recentRequests': row['recent_requests'],
                'completedRequests': row['completed_requests'],
            }
            for row in breakdown
        ]

    def _build_top_technician(self, today):
        recent_start = today - timezone.timedelta(days=29)
        leaderboard = (
            ServiceTicket.objects.filter(
                status='Completed',
                technician__isnull=False,
                completed_date__date__gte=recent_start
            )
            .values('technician__username')
            .annotate(
                total_completed=Count('id'),
                avg_rating=Avg('client_rating')
            )
            .order_by('-total_completed', 'technician__username')
            .first()
        )

        if not leaderboard:
            return None

        return {
            'techName': leaderboard['technician__username'],
            'totalCompleted': leaderboard['total_completed'],
            'avgRating': round(leaderboard['avg_rating'], 1)
            if leaderboard['avg_rating'] is not None else None,
        }

    def _build_completion_trend(self, today):
        trend = []
        for offset in range(6, -1, -1):
            date = today - timezone.timedelta(days=offset)
            trend.append({
                'date': date.isoformat(),
                'label': date.strftime('%a'),
                'completedCount': ServiceTicket.objects.filter(
                    status='Completed',
                    completed_date__date=date
                ).count(),
            })
        return trend

    def _build_busiest_months(self, today):
        window_start = (today.replace(day=1) - timezone.timedelta(days=370)).replace(day=1)
        buckets = defaultdict(lambda: {
            'monthStart': None,
            'label': '',
            'requestCount': 0,
            'completedCount': 0,
        })

        for request_obj in ServiceRequest.objects.filter(request_date__date__gte=window_start):
            request_dt = request_obj.request_date
            request_day = (
                timezone.localtime(request_dt).date()
                if timezone.is_aware(request_dt) else request_dt.date()
            )
            month_start = request_day.replace(day=1)
            bucket = buckets[month_start]
            bucket['monthStart'] = month_start.isoformat()
            bucket['label'] = month_start.strftime('%b %Y')
            bucket['requestCount'] += 1
            if request_obj.status == 'Completed':
                bucket['completedCount'] += 1

        busiest_months = []
        for month_start, bucket in buckets.items():
            completion_rate = (
                (bucket['completedCount'] / bucket['requestCount']) * 100
                if bucket['requestCount'] else 0
            )
            busiest_months.append({
                **bucket,
                'completionRate': round(completion_rate, 1),
                '_sort_month': month_start,
            })

        busiest_months.sort(
            key=lambda item: (-item['requestCount'], -item['_sort_month'].toordinal())
        )

        return [
            {key: value for key, value in item.items() if key != '_sort_month'}
            for item in busiest_months[:self.ANALYTICS_LIST_LIMIT]
        ]

    def _build_busiest_weeks(self, today):
        window_start = today - timezone.timedelta(days=(self.BUSIEST_WEEKS_WINDOW * 7) - 1)
        buckets = defaultdict(lambda: {
            'weekStart': None,
            'weekEnd': None,
            'label': '',
            'requestCount': 0,
            'completedCount': 0,
        })

        for request_obj in ServiceRequest.objects.filter(request_date__date__gte=window_start):
            request_dt = request_obj.request_date
            request_day = (
                timezone.localtime(request_dt).date()
                if timezone.is_aware(request_dt) else request_dt.date()
            )
            week_start = request_day - timezone.timedelta(days=request_day.weekday())
            week_end = week_start + timezone.timedelta(days=6)
            bucket = buckets[week_start]
            bucket['weekStart'] = week_start.isoformat()
            bucket['weekEnd'] = week_end.isoformat()
            bucket['label'] = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
            bucket['requestCount'] += 1
            if request_obj.status == 'Completed':
                bucket['completedCount'] += 1

        busiest_weeks = []
        for week_start, bucket in buckets.items():
            completion_rate = (
                (bucket['completedCount'] / bucket['requestCount']) * 100
                if bucket['requestCount'] else 0
            )
            busiest_weeks.append({
                **bucket,
                'completionRate': round(completion_rate, 1),
                '_sort_week': week_start,
            })

        busiest_weeks.sort(
            key=lambda item: (-item['requestCount'], -item['_sort_week'].toordinal())
        )

        return [
            {key: value for key, value in item.items() if key != '_sort_week'}
            for item in busiest_weeks[:self.ANALYTICS_LIST_LIMIT]
        ]

    def _build_top_requested_service_types(self, service_breakdown):
        top_services = []
        for service in service_breakdown[:self.ANALYTICS_LIST_LIMIT]:
            completion_rate = (
                (service['completedRequests'] / service['count']) * 100
                if service['count'] else 0
            )
            top_services.append({
                'serviceTypeId': service['id'],
                'serviceType': service['name'],
                'requestCount': service['count'],
                'recentRequests': service['recentRequests'],
                'completedCount': service['completedRequests'],
                'completionRate': round(completion_rate, 1),
            })
        return top_services

    def _build_location_completion_trends(self, today):
        recent_start = today - timezone.timedelta(days=self.LOCATION_TREND_WINDOW_DAYS - 1)
        previous_start = recent_start - timezone.timedelta(days=self.LOCATION_TREND_WINDOW_DAYS)

        tickets = ServiceTicket.objects.select_related('request__location').filter(
            request__location__isnull=False
        )

        city_buckets = defaultdict(lambda: {
            'city': '',
            'totalTickets': 0,
            'completedCount': 0,
            'recentCompleted': 0,
            'previousCompleted': 0,
            'latestCompletedDate': None,
        })
        province_buckets = defaultdict(lambda: {
            'province': '',
            'totalTickets': 0,
            'completedCount': 0,
            'recentCompleted': 0,
            'previousCompleted': 0,
            'latestCompletedDate': None,
        })

        for ticket in tickets:
            try:
                location = ticket.request.location
            except Exception:
                continue

            city = (location.city or '').strip()
            province = (location.province or '').strip()
            bucket_targets = []

            if city and city.lower() != 'unspecified':
                bucket_targets.append((city_buckets, city, 'city'))
            if province and province.lower() != 'unspecified':
                bucket_targets.append((province_buckets, province, 'province'))

            for bucket_map, label, field_name in bucket_targets:
                bucket = bucket_map[label]
                bucket[field_name] = label
                bucket['totalTickets'] += 1

                if ticket.status != 'Completed' or not ticket.completed_date:
                    continue

                bucket['completedCount'] += 1
                completed_day = (
                    timezone.localtime(ticket.completed_date).date()
                    if timezone.is_aware(ticket.completed_date) else ticket.completed_date.date()
                )
                if completed_day >= recent_start:
                    bucket['recentCompleted'] += 1
                elif previous_start <= completed_day < recent_start:
                    bucket['previousCompleted'] += 1

                latest_completed = bucket['latestCompletedDate']
                if latest_completed is None or completed_day > latest_completed:
                    bucket['latestCompletedDate'] = completed_day

        def serialize_location_buckets(bucket_map, field_name):
            serialized = []
            for bucket in bucket_map.values():
                trend_delta = bucket['recentCompleted'] - bucket['previousCompleted']
                if trend_delta > 0:
                    trend_direction = 'up'
                elif trend_delta < 0:
                    trend_direction = 'down'
                else:
                    trend_direction = 'flat'

                completion_rate = (
                    (bucket['completedCount'] / bucket['totalTickets']) * 100
                    if bucket['totalTickets'] else 0
                )

                serialized.append({
                    field_name: bucket[field_name],
                    'totalTickets': bucket['totalTickets'],
                    'completedCount': bucket['completedCount'],
                    'completionRate': round(completion_rate, 1),
                    'recentCompleted': bucket['recentCompleted'],
                    'previousCompleted': bucket['previousCompleted'],
                    'trendDelta': trend_delta,
                    'trendDirection': trend_direction,
                    'latestCompletedDate': bucket['latestCompletedDate'].isoformat()
                    if bucket['latestCompletedDate'] else None,
                })

            serialized.sort(
                key=lambda item: (
                    -item['completedCount'],
                    -item['recentCompleted'],
                    item[field_name].lower(),
                )
            )
            return serialized[:self.ANALYTICS_LIST_LIMIT]

        return (
            serialize_location_buckets(city_buckets, 'city'),
            serialize_location_buckets(province_buckets, 'province'),
        )

    def _build_predictive_analytics(self, today):
        history_start = today - timezone.timedelta(days=self.HISTORY_WINDOW_DAYS - 1)
        recent_start = today - timezone.timedelta(days=self.RECENT_WINDOW_DAYS - 1)
        previous_start = recent_start - timezone.timedelta(days=self.RECENT_WINDOW_DAYS)

        active_technicians = User.objects.filter(
            role='technician',
            status='active',
            is_active=True
        ).count()

        weekday_slots = {index: 0 for index in range(7)}
        current_date = history_start
        while current_date <= today:
            weekday_slots[current_date.weekday()] += 1
            current_date += timezone.timedelta(days=1)

        daily_forecast_map = {}
        for offset in range(1, self.FORECAST_WINDOW_DAYS + 1):
            forecast_date = today + timezone.timedelta(days=offset)
            daily_forecast_map[forecast_date] = {
                'date': forecast_date.isoformat(),
                'label': forecast_date.strftime('%a %d %b'),
                'predictedRequests': 0,
            }

        service_forecasts = []
        weighted_growth_total = 0
        weighted_growth_volume = 0

        for service_type in ServiceType.objects.order_by('name'):
            request_days = []
            history_requests = ServiceRequest.objects.filter(
                service_type=service_type,
                request_date__date__gte=previous_start,
                request_date__date__lte=today
            ).values_list('request_date', flat=True)

            for request_date in history_requests:
                localized = timezone.localtime(request_date) if timezone.is_aware(request_date) else request_date
                request_days.append(localized.date())

            weekday_counts = {index: 0 for index in range(7)}
            history_count = 0
            recent_count = 0
            previous_count = 0

            for request_day in request_days:
                if request_day >= history_start:
                    history_count += 1
                    weekday_counts[request_day.weekday()] += 1
                if request_day >= recent_start:
                    recent_count += 1
                elif request_day >= previous_start:
                    previous_count += 1

            history_daily_average = (
                history_count / self.HISTORY_WINDOW_DAYS if history_count else 0
            )
            recent_daily_average = (
                recent_count / self.RECENT_WINDOW_DAYS if recent_count else history_daily_average
            )
            previous_daily_average = (
                previous_count / self.RECENT_WINDOW_DAYS if previous_count else 0
            )

            if previous_daily_average > 0:
                growth_rate = (recent_daily_average - previous_daily_average) / previous_daily_average
            elif recent_daily_average > 0 and history_daily_average > 0:
                growth_rate = (recent_daily_average - history_daily_average) / history_daily_average
            elif recent_daily_average > 0:
                growth_rate = 0.25
            else:
                growth_rate = 0

            trend_factor = max(0.8, min(1.5, 1 + (growth_rate * 0.35)))
            per_day_predictions = []

            for offset in range(1, self.FORECAST_WINDOW_DAYS + 1):
                forecast_date = today + timezone.timedelta(days=offset)
                weekday = forecast_date.weekday()
                weekday_average = weekday_counts[weekday] / max(1, weekday_slots[weekday])

                if history_daily_average > 0 and weekday_average > 0:
                    weekday_factor = weekday_average / history_daily_average
                else:
                    weekday_factor = 1.12 if weekday == 0 else 0.9 if weekday >= 5 else 1.0

                raw_prediction = recent_daily_average * weekday_factor * trend_factor
                if history_count == 0 and recent_count == 0:
                    predicted_requests = 0
                elif raw_prediction < 1:
                    predicted_requests = 1
                else:
                    predicted_requests = int(round(raw_prediction))

                per_day_predictions.append(predicted_requests)
                daily_forecast_map[forecast_date]['predictedRequests'] += predicted_requests

            predicted_next_7_days = sum(per_day_predictions)
            available_technicians = (
                TechnicianSkill.objects.filter(
                    service_type=service_type,
                    technician__role='technician',
                    technician__status='active',
                    technician__is_active=True
                )
                .values('technician_id')
                .distinct()
                .count()
            )
            if available_technicians == 0:
                available_technicians = active_technicians

            recommended_technicians = (
                (predicted_next_7_days + self.FORECAST_JOBS_PER_TECHNICIAN - 1)
                // self.FORECAST_JOBS_PER_TECHNICIAN
                if predicted_next_7_days > 0 else 0
            )
            capacity_gap = max(0, recommended_technicians - available_technicians)

            if capacity_gap > 0:
                risk_level = 'high'
            elif growth_rate > 0.2 or (
                available_technicians > 0 and
                predicted_next_7_days > available_technicians * self.FORECAST_JOBS_PER_TECHNICIAN
            ):
                risk_level = 'medium'
            else:
                risk_level = 'low'

            confidence = 45
            if history_count:
                confidence += min(35, history_count)
            if previous_count and recent_count:
                confidence += 10
            confidence = min(92, confidence)

            service_forecasts.append({
                'serviceTypeId': service_type.id,
                'serviceType': service_type.name,
                'recentRequests': recent_count,
                'previousRequests': previous_count,
                'historyRequests': history_count,
                'averageDailyDemand': round(recent_daily_average, 2),
                'projectedGrowthRate': round(growth_rate * 100, 1),
                'predictedNext7Days': predicted_next_7_days,
                'availableTechnicians': available_technicians,
                'recommendedTechnicians': recommended_technicians,
                'capacityGap': capacity_gap,
                'confidence': confidence,
                'riskLevel': risk_level,
            })

            weighted_growth_total += growth_rate * predicted_next_7_days
            weighted_growth_volume += predicted_next_7_days

        risk_priority = {'high': 0, 'medium': 1, 'low': 2}
        service_forecasts.sort(
            key=lambda item: (
                risk_priority.get(item['riskLevel'], 3),
                -item['predictedNext7Days'],
                item['serviceType']
            )
        )

        daily_forecast = []
        for forecast_date in sorted(daily_forecast_map.keys()):
            entry = daily_forecast_map[forecast_date]
            predicted_requests = entry['predictedRequests']
            capacity_gap = max(0, predicted_requests - active_technicians)

            if capacity_gap > 0:
                demand_level = 'high'
            elif predicted_requests >= max(3, active_technicians):
                demand_level = 'medium'
            else:
                demand_level = 'low'

            daily_forecast.append({
                **entry,
                'capacityGap': capacity_gap,
                'demandLevel': demand_level,
            })

        total_predicted_requests = sum(item['predictedRequests'] for item in daily_forecast)
        recommended_technicians = (
            (total_predicted_requests + self.FORECAST_JOBS_PER_TECHNICIAN - 1)
            // self.FORECAST_JOBS_PER_TECHNICIAN
            if total_predicted_requests > 0 else 0
        )
        projected_growth_rate = (
            round((weighted_growth_total / weighted_growth_volume) * 100, 1)
            if weighted_growth_volume else 0
        )

        if recommended_technicians > active_technicians:
            staffing_pressure = 'high'
        elif recommended_technicians == active_technicians and recommended_technicians > 0:
            staffing_pressure = 'medium'
        else:
            staffing_pressure = 'low'

        busiest_day = max(
            daily_forecast,
            key=lambda item: item['predictedRequests'],
            default=None
        )
        top_risk_service = next(
            (item for item in service_forecasts if item['riskLevel'] == 'high'),
            service_forecasts[0] if service_forecasts else None
        )

        predictive_summary = {
            'forecastWindowDays': self.FORECAST_WINDOW_DAYS,
            'historyWindowDays': self.HISTORY_WINDOW_DAYS,
            'totalPredictedRequests': total_predicted_requests,
            'projectedGrowthRate': projected_growth_rate,
            'activeTechnicians': active_technicians,
            'recommendedTechnicians': recommended_technicians,
            'staffingPressure': staffing_pressure,
            'busiestDay': busiest_day,
            'topRiskService': {
                'serviceType': top_risk_service['serviceType'],
                'predictedNext7Days': top_risk_service['predictedNext7Days'],
                'capacityGap': top_risk_service['capacityGap'],
                'riskLevel': top_risk_service['riskLevel'],
            } if top_risk_service else None,
        }

        return predictive_summary, service_forecasts, daily_forecast
