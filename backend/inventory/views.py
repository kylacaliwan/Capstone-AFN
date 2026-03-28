
from django.db import models
from django.db.models import Sum, Count, Q
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .automation import (
    cancel_pending_reservation,
    create_pending_reservation,
    fulfill_pending_reservation,
)
from .models import (
    InventoryCategory,
    InventoryItem,
    InventoryTransaction,
    InventoryReservation,
    ServiceTypeInventoryRequirement,
)
from .serializers import (
    InventoryCategorySerializer, InventoryItemSerializer,
    InventoryTransactionSerializer, InventoryReservationSerializer,
    ServiceTypeInventoryRequirementSerializer,
)
from users.permissions import (
    IsAdmin, IsSupervisor, IsTechnician, IsClient,
    IsAdminOrSupervisor, IsAdminOrSupervisorOrTechnician,
    CanManageInventory
)


class InventoryCategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [CanManageInventory]


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'sku', 'description']

    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageInventory()]
        elif self.action in ['list', 'retrieve']:
            return [IsAdminOrSupervisorOrTechnician()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        queryset = InventoryItem.objects.all()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by status
        item_status = self.request.query_params.get('status')
        if item_status:
            queryset = queryset.filter(status=item_status)
        
        # Filter low stock items
        low_stock = self.request.query_params.get('low_stock')
        if low_stock == 'true':
            queryset = queryset.filter(quantity__lte=models.F('minimum_stock'))
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get items with low stock"""
        items = InventoryItem.objects.filter(
            quantity__lte=models.F('minimum_stock')
        )
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get inventory statistics"""
        from django.db.models import ExpressionWrapper, DecimalField

        total_items = InventoryItem.objects.count()
        total_value = InventoryItem.objects.aggregate(
            total=Sum('total_value')
        )['total'] or 0

        # Database-level aggregation — no Python loop needed
        low_stock_count = InventoryItem.objects.filter(
            quantity__lte=models.F('minimum_stock')
        ).count()

        out_of_stock = InventoryItem.objects.filter(quantity=0).count()

        # By status — single query using values/annotate
        status_counts = {}
        for row in InventoryItem.objects.values('status').annotate(count=Count('id')):
            status_counts[row['status']] = row['count']

        # By category
        category_counts = InventoryItem.objects.values(
            'category__name'
        ).annotate(count=Count('id'))

        return Response({
            'total_items': total_items,
            'total_value': float(total_value),
            'low_stock_count': low_stock_count,
            'out_of_stock': out_of_stock,
            'status_counts': status_counts,
            'category_counts': list(category_counts)
        })


class InventoryTransactionViewSet(viewsets.ModelViewSet):
    queryset = InventoryTransaction.objects.all()
    serializer_class = InventoryTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageInventory()]
        return [IsAdminOrSupervisorOrTechnician()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'technician':
            return InventoryTransaction.objects.filter(technician=user)
        return InventoryTransaction.objects.all()

    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent transactions"""
        limit = int(request.query_params.get('limit', 20))
        transactions = self.get_queryset().order_by('-id')[:limit]
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_item(self, request):
        """Get transactions for a specific item — respects role-based filtering"""
        item_id = request.query_params.get('item_id')
        if not item_id:
            return Response({'error': 'item_id required'}, status=400)

        # Reuse get_queryset so technicians only see their own transactions
        transactions = self.get_queryset().filter(item_id=item_id)
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)


class InventoryReservationViewSet(viewsets.ModelViewSet):
    queryset = InventoryReservation.objects.all()
    serializer_class = InventoryReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'fulfill', 'cancel']:
            return [CanManageInventory()]
        return [IsAdminOrSupervisorOrTechnician()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'technician':
            return InventoryReservation.objects.filter(technician=user)
        return InventoryReservation.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = create_pending_reservation(
            item=serializer.validated_data['item'],
            quantity=serializer.validated_data['quantity'],
            technician=serializer.validated_data['technician'],
            required_date=serializer.validated_data['required_date'],
            service_ticket=serializer.validated_data.get('service_ticket'),
            performed_by=request.user,
            notes=serializer.validated_data.get('notes') or 'Manual reservation',
        )
        output_serializer = self.get_serializer(reservation)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'])
    def fulfill(self, request, pk=None):
        """Mark reservation as fulfilled and issue items"""
        reservation = self.get_object()

        if reservation.status != 'pending':
            return Response({'error': 'Only pending reservations can be fulfilled.'}, status=400)

        fulfill_pending_reservation(
            reservation,
            performed_by=request.user,
            notes=f"Fulfilling reservation #{reservation.id}",
        )
        return Response({'status': 'Reservation fulfilled'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel reservation"""
        reservation = self.get_object()

        if reservation.status != 'pending':
            return Response({'error': 'Only pending reservations can be cancelled.'}, status=400)

        cancel_pending_reservation(
            reservation,
            performed_by=request.user,
            notes=f"Cancelled reservation #{reservation.id}",
        )
        return Response({'status': 'Reservation cancelled'})
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending reservations"""
        reservations = InventoryReservation.objects.filter(status='pending')
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)


class ServiceTypeInventoryRequirementViewSet(viewsets.ModelViewSet):
    queryset = ServiceTypeInventoryRequirement.objects.select_related('service_type', 'item')
    serializer_class = ServiceTypeInventoryRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageInventory()]
        return [IsAdminOrSupervisorOrTechnician()]

