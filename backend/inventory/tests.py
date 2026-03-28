from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import (
    InventoryCategory,
    InventoryItem,
    InventoryReservation,
    InventoryTransaction,
    ServiceTypeInventoryRequirement,
)
from services.models import ServiceLocation, ServiceRequest, ServiceTicket, ServiceType
from users.models import User


class AutoInventoryWorkflowTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='inventory-admin',
            password='pass',
            role='admin',
        )
        self.client_user = User.objects.create_user(
            username='inventory-client',
            password='pass',
            role='client',
        )
        self.technician_user = User.objects.create_user(
            username='inventory-tech',
            password='pass',
            role='technician',
            status='active',
            is_available=True,
            current_latitude='14.560000',
            current_longitude='121.020000',
        )
        self.category = InventoryCategory.objects.create(
            name='Service Parts',
            description='Default service parts',
        )
        self.inventory_item = InventoryItem.objects.create(
            name='Replacement Sensor',
            sku='SENSOR-01',
            category=self.category,
            item_type='part',
            quantity=10,
            minimum_stock=2,
            status='available',
        )
        self.service_type = ServiceType.objects.create(
            name='Sensor Maintenance',
            description='Maintenance service needing sensors',
            estimated_duration=90,
        )
        ServiceTypeInventoryRequirement.objects.create(
            service_type=self.service_type,
            item=self.inventory_item,
            quantity=2,
            auto_reserve=True,
            notes='Standard replacement stock',
        )
        self.request_obj = ServiceRequest.objects.create(
            client=self.client_user,
            service_type=self.service_type,
            description='Maintenance request',
            priority='Normal',
            status='Approved',
            auto_ticket_created=True,
        )
        ServiceLocation.objects.create(
            request=self.request_obj,
            address='400 Inventory Street',
            city='Pasig',
            province='Metro Manila',
            latitude='14.572000',
            longitude='121.049000',
        )
        self.ticket = ServiceTicket.objects.create(
            request=self.request_obj,
            scheduled_date=timezone.localdate(),
            status='Not Started',
            priority='Normal',
        )

    def assign_ticket(self):
        self.client.force_authenticate(user=self.admin_user)
        return self.client.post(
            f'/api/services/service-tickets/{self.ticket.id}/assign/',
            {'technician_id': self.technician_user.id},
            format='json',
        )

    def test_assigning_ticket_auto_reserves_inventory(self):
        response = self.assign_ticket()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation = InventoryReservation.objects.get(service_ticket=self.ticket)
        self.inventory_item.refresh_from_db()

        self.assertEqual(reservation.technician, self.technician_user)
        self.assertEqual(reservation.quantity, 2)
        self.assertEqual(reservation.status, 'pending')
        self.assertEqual(self.inventory_item.reserved_quantity, 2)
        self.assertEqual(len(response.data['inventory_summary']['reservations']), 1)
        self.assertEqual(
            InventoryTransaction.objects.filter(
                service_ticket=self.ticket,
                transaction_type='reservation',
            ).count(),
            1,
        )

    def test_cancelling_request_releases_reserved_inventory(self):
        assign_response = self.assign_ticket()
        self.assertEqual(assign_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.admin_user)
        cancel_response = self.client.post(
            f'/api/services/service-requests/{self.request_obj.id}/cancel/',
            {},
            format='json',
        )

        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        reservation = InventoryReservation.objects.get(service_ticket=self.ticket)
        self.inventory_item.refresh_from_db()

        self.assertEqual(reservation.status, 'cancelled')
        self.assertEqual(self.inventory_item.reserved_quantity, 0)
        self.assertTrue(
            InventoryTransaction.objects.filter(
                service_ticket=self.ticket,
                transaction_type='cancellation',
            ).exists()
        )

    def test_completing_ticket_issues_reserved_inventory(self):
        assign_response = self.assign_ticket()
        self.assertEqual(assign_response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.technician_user)
        start_response = self.client.post(
            f'/api/services/service-tickets/{self.ticket.id}/start_work/',
            {},
            format='json',
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)

        complete_response = self.client.post(
            f'/api/services/service-tickets/{self.ticket.id}/complete_work/',
            {},
            format='json',
        )

        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        reservation = InventoryReservation.objects.get(service_ticket=self.ticket)
        self.inventory_item.refresh_from_db()

        self.assertEqual(reservation.status, 'fulfilled')
        self.assertEqual(self.inventory_item.quantity, 8)
        self.assertEqual(self.inventory_item.reserved_quantity, 0)
        self.assertTrue(
            InventoryTransaction.objects.filter(
                service_ticket=self.ticket,
                transaction_type='issue',
            ).exists()
        )
