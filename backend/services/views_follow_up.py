from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from users.permissions import CanAccessAfterSales, CanManageAfterSalesCases, IsAdmin

from .maintenance import process_maintenance_alerts
from .models import AfterSalesCase as FollowUpCase, MaintenanceSchedule, ServiceTicket
from .serializers import FollowUpCaseSerializer


class FollowUpCaseViewSet(viewsets.ModelViewSet):
    serializer_class = FollowUpCaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'summary',
        'details',
        'service_ticket__request__client__username',
        'service_ticket__request__service_type__name',
    ]
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'status', 'priority']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), CanManageAfterSalesCases()]
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated(), CanAccessAfterSales()]

    def get_queryset(self):
        queryset = FollowUpCase.objects.select_related(
            'service_ticket__request__client',
            'service_ticket__request__service_type',
            'assigned_to',
            'created_by',
            'client',
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        case_type = self.request.query_params.get('case_type')
        if case_type:
            queryset = queryset.filter(case_type=case_type)

        assigned_only = self.request.query_params.get('assigned_only')
        if assigned_only == 'true' and self.request.user.role == 'follow_up':
            queryset = queryset.filter(assigned_to=self.request.user)

        return queryset

    def perform_create(self, serializer):
        service_ticket = serializer.validated_data['service_ticket']
        assigned_to = serializer.validated_data.get('assigned_to')
        case_type = serializer.validated_data.get('case_type', 'follow_up')

        if service_ticket.status != 'Completed':
            raise ValidationError({'service_ticket': 'Follow-up cases can only be opened for completed tickets.'})

        if case_type == 'warranty':
            if service_ticket.warranty_status != 'active' or not service_ticket.warranty_end_date:
                raise ValidationError({
                    'service_ticket': 'Warranty cases can only be opened while the ticket warranty is active.',
                })

        if self.request.user.role == 'follow_up' and assigned_to and assigned_to != self.request.user:
            assigned_to = self.request.user

        serializer.save(
            client=service_ticket.request.client,
            created_by=self.request.user,
            creation_source='manual',
            assigned_to=assigned_to or (self.request.user if self.request.user.role == 'follow_up' else assigned_to),
            due_date=serializer.validated_data.get('due_date') or (
                service_ticket.warranty_end_date if case_type == 'warranty' else serializer.validated_data.get('due_date')
            ),
        )

    def perform_update(self, serializer):
        case = serializer.save()
        resolved_statuses = {'resolved', 'closed'}
        maintenance_schedule = MaintenanceSchedule.objects.filter(service_ticket=case.service_ticket).first()

        if case.status in resolved_statuses and case.resolved_at is None:
            case.resolved_at = timezone.now()
            case.save(update_fields=['resolved_at'])
        elif case.status not in resolved_statuses and case.resolved_at is not None:
            case.resolved_at = None
            case.save(update_fields=['resolved_at'])

        if maintenance_schedule and case.case_type == 'maintenance':
            if case.status in resolved_statuses:
                maintenance_schedule.status = 'completed'
            else:
                today = timezone.localdate()
                if today >= maintenance_schedule.next_due_date:
                    maintenance_schedule.status = 'due'
                elif today >= maintenance_schedule.notify_on_date:
                    maintenance_schedule.status = 'due_soon'
                else:
                    maintenance_schedule.status = 'scheduled'
            maintenance_schedule.save(update_fields=['status', 'updated_at'])

    @action(detail=False, methods=['get'])
    def summary(self, request):
        today = timezone.now().date()
        process_maintenance_alerts(reference_date=today)
        queryset = self.get_queryset()
        open_statuses = ['open', 'in_progress']

        summary = queryset.aggregate(
            total_cases=Count('id'),
            open_cases=Count('id', filter=Q(status__in=open_statuses)),
            overdue_cases=Count('id', filter=Q(status__in=open_statuses, due_date__lt=today)),
            revisit_cases=Count('id', filter=Q(requires_revisit=True)),
        )

        follow_up_candidates = ServiceTicket.objects.filter(status='Completed').exclude(
            after_sales_cases__isnull=False
        ).count()
        maintenance_summary = MaintenanceSchedule.objects.exclude(status__in=['completed', 'dismissed']).aggregate(
            scheduled_maintenance=Count('id'),
            maintenance_due_soon=Count('id', filter=Q(status='due_soon')),
            maintenance_due=Count('id', filter=Q(status='due')),
        )

        return Response({
            **summary,
            'follow_up_candidates': follow_up_candidates,
            **maintenance_summary,
        })
