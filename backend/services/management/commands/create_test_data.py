import os
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import (
    InventoryCategory,
    InventoryItem,
    ServiceTypeInventoryRequirement,
)
from notifications.models import Notification
from services.models import (
    ServiceLocation,
    ServiceRequest,
    ServiceTicket,
    ServiceType,
)


User = get_user_model()


class Command(BaseCommand):
    help = "Create polished capstone demo data for AFN Service Management."
    PASSWORD_ENV_PREFIX = "AFN_DEMO_PASSWORD_"

    USER_FIXTURES = [
        {
            "username": "admin",
            "email": "admin@afn.com",
            "role": "admin",
            "first_name": "Ariana",
            "last_name": "Navarro",
            "phone": "+63 917 555 0100",
            "address": "AFN Operations Hub, Ortigas Center, Pasig City",
        },
        {
            "username": "supervisor1",
            "email": "supervisor@afn.com",
            "role": "supervisor",
            "first_name": "Carlos",
            "last_name": "Mendoza",
            "phone": "+63 917 555 0101",
            "address": "Dispatch Office, Pasig City",
        },
        {
            "username": "tech1",
            "email": "tech1@afn.com",
            "role": "technician",
            "first_name": "Marco",
            "last_name": "Reyes",
            "phone": "+63 917 555 0102",
            "address": "Mandaluyong City",
            "current_latitude": 14.5794,
            "current_longitude": 121.0359,
            "is_available": False,
        },
        {
            "username": "tech2",
            "email": "tech2@afn.com",
            "role": "technician",
            "first_name": "Lea",
            "last_name": "Santos",
            "phone": "+63 917 555 0103",
            "address": "Quezon City",
            "current_latitude": 14.6760,
            "current_longitude": 121.0437,
            "is_available": True,
        },
        {
            "username": "client1",
            "email": "client1@afn.com",
            "role": "client",
            "first_name": "Mia",
            "last_name": "Dela Cruz",
            "phone": "+63 917 555 0104",
            "address": "Greenview Residences, Makati City",
        },
        {
            "username": "client2",
            "email": "client2@afn.com",
            "role": "client",
            "first_name": "Julian",
            "last_name": "Ramos",
            "phone": "+63 917 555 0105",
            "address": "Riverside Suites, Quezon City",
        },
    ]

    SERVICE_FIXTURES = [
        {
            "name": "Solar Panel Installation",
            "description": "Rooftop solar installation and commissioning.",
            "estimated_duration": 480,
        },
        {
            "name": "Solar Panel Maintenance",
            "description": "Preventive maintenance, cleaning, and performance checks.",
            "estimated_duration": 180,
        },
        {
            "name": "Solar Inverter Repair",
            "description": "Inverter diagnostics, repair, and replacement support.",
            "estimated_duration": 240,
        },
        {
            "name": "CCTV Preventive Maintenance",
            "description": "Camera inspection, recorder cleanup, and health checks.",
            "estimated_duration": 120,
        },
        {
            "name": "Fire Alarm Inspection",
            "description": "Inspection and testing of control panels, detectors, and sirens.",
            "estimated_duration": 150,
        },
        {
            "name": "AC Service & Installation",
            "description": "Split-type air conditioning service and installation.",
            "estimated_duration": 240,
        },
    ]

    CATEGORY_FIXTURES = [
        ("Solar Components", "Solar modules, inverters, and accessories."),
        ("Security Systems", "CCTV cameras, recorders, and accessories."),
        ("Fire Safety", "Fire alarm detectors, modules, and control equipment."),
        ("HVAC", "Air conditioning equipment and installation accessories."),
        ("Electrical Consumables", "Common cabling and connectors for field work."),
    ]

    ITEM_FIXTURES = [
        {
            "name": "Solar Panel 550W",
            "sku": "SOL-550W",
            "category": "Solar Components",
            "quantity": 36,
            "minimum_stock": 12,
            "unit_price": 12850.00,
            "item_type": "equipment",
            "warehouse_location": "Rack A1",
            "supplier": "HelioTech Supply",
        },
        {
            "name": "Hybrid Inverter 5kW",
            "sku": "INV-5KW-HYB",
            "category": "Solar Components",
            "quantity": 9,
            "minimum_stock": 3,
            "unit_price": 48500.00,
            "item_type": "equipment",
            "warehouse_location": "Rack A3",
            "supplier": "HelioTech Supply",
        },
        {
            "name": "MC4 Connector Set",
            "sku": "MC4-SET",
            "category": "Electrical Consumables",
            "quantity": 80,
            "minimum_stock": 20,
            "unit_price": 180.00,
            "item_type": "consumable",
            "warehouse_location": "Bin E2",
            "supplier": "GridLine Trading",
        },
        {
            "name": "CCTV Dome Camera 4MP",
            "sku": "CCTV-4MP-DOME",
            "category": "Security Systems",
            "quantity": 24,
            "minimum_stock": 8,
            "unit_price": 3250.00,
            "item_type": "equipment",
            "warehouse_location": "Rack B2",
            "supplier": "SecureVision",
        },
        {
            "name": "NVR 8-Channel",
            "sku": "NVR-8CH",
            "category": "Security Systems",
            "quantity": 10,
            "minimum_stock": 4,
            "unit_price": 7800.00,
            "item_type": "equipment",
            "warehouse_location": "Rack B5",
            "supplier": "SecureVision",
        },
        {
            "name": "Smoke Detector Addressable",
            "sku": "FIRE-SD-ADDR",
            "category": "Fire Safety",
            "quantity": 40,
            "minimum_stock": 10,
            "unit_price": 950.00,
            "item_type": "equipment",
            "warehouse_location": "Rack C1",
            "supplier": "FireSafe Systems",
        },
        {
            "name": "Fire Alarm Control Module",
            "sku": "FIRE-MOD-CTRL",
            "category": "Fire Safety",
            "quantity": 12,
            "minimum_stock": 4,
            "unit_price": 4200.00,
            "item_type": "equipment",
            "warehouse_location": "Rack C3",
            "supplier": "FireSafe Systems",
        },
        {
            "name": "Split Type AC 1.5HP",
            "sku": "AC-1.5HP",
            "category": "HVAC",
            "quantity": 7,
            "minimum_stock": 2,
            "unit_price": 28600.00,
            "item_type": "equipment",
            "warehouse_location": "Rack D1",
            "supplier": "CoolFlow Distributors",
        },
        {
            "name": "Copper Tubing Set 1/4-3/8",
            "sku": "HVAC-COPPER-SET",
            "category": "HVAC",
            "quantity": 18,
            "minimum_stock": 6,
            "unit_price": 1450.00,
            "item_type": "part",
            "warehouse_location": "Rack D4",
            "supplier": "CoolFlow Distributors",
        },
    ]

    def handle(self, *args, **options):
        today = timezone.localdate()
        self.generated_passwords = {}
        self.env_passwords = {}

        self.stdout.write("Seeding polished capstone demo data...")

        users = self._seed_users()
        service_types = self._seed_service_types()
        items = self._seed_inventory()
        self._seed_service_templates(service_types, items)
        seeded_requests = self._seed_requests_and_tickets(users, service_types, today)
        self._seed_notifications(users, seeded_requests)

        self.stdout.write(self.style.SUCCESS("Capstone demo data is ready."))
        self.stdout.write("")
        self.stdout.write("Password summary:")
        for username in users:
            if username in self.env_passwords:
                self.stdout.write(f"{username}: sourced from {self.env_passwords[username]}")
            elif username in self.generated_passwords:
                self.stdout.write(f"{username}: generated one-time password {self.generated_passwords[username]}")
            else:
                self.stdout.write(f"{username}: existing password preserved")

    def _resolve_password(self, username, created):
        env_key = f"{self.PASSWORD_ENV_PREFIX}{username.upper()}"
        env_password = os.environ.get(env_key, "").strip()
        if env_password:
            self.env_passwords[username] = env_key
            return env_password

        if not created:
            return None

        generated_password = secrets.token_urlsafe(16)
        self.generated_passwords[username] = generated_password
        return generated_password

    def _seed_users(self):
        users = {}
        for fixture in self.USER_FIXTURES:
            defaults = fixture.copy()
            username = defaults.pop("username")

            user, created = User.objects.update_or_create(
                username=username,
                defaults=defaults,
            )
            password = self._resolve_password(username, created)
            if password and (created or not user.check_password(password)):
                user.set_password(password)
                user.save(update_fields=["password"])

            users[username] = user
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} user profile: {user.get_full_name() or user.username}")
        return users

    def _seed_service_types(self):
        service_types = {}
        for fixture in self.SERVICE_FIXTURES:
            service_type, _ = ServiceType.objects.update_or_create(
                name=fixture["name"],
                defaults={
                    "description": fixture["description"],
                    "estimated_duration": fixture["estimated_duration"],
                },
            )
            service_types[service_type.name] = service_type
        return service_types

    def _seed_inventory(self):
        categories = {}
        for name, description in self.CATEGORY_FIXTURES:
            category, _ = InventoryCategory.objects.update_or_create(
                name=name,
                defaults={"description": description},
            )
            categories[name] = category

        items = {}
        for fixture in self.ITEM_FIXTURES:
            item, _ = InventoryItem.objects.update_or_create(
                sku=fixture["sku"],
                defaults={
                    "name": fixture["name"],
                    "category": categories[fixture["category"]],
                    "quantity": fixture["quantity"],
                    "minimum_stock": fixture["minimum_stock"],
                    "unit_price": fixture["unit_price"],
                    "item_type": fixture["item_type"],
                    "warehouse_location": fixture["warehouse_location"],
                    "supplier": fixture["supplier"],
                    "status": "available",
                },
            )
            items[item.sku] = item
        return items

    def _seed_service_templates(self, service_types, items):
        template_rows = [
            ("Solar Panel Installation", "SOL-550W", 8, "Default module allocation for a standard residential install."),
            ("Solar Panel Installation", "INV-5KW-HYB", 1, "Reserve one inverter for each residential rooftop install."),
            ("Solar Panel Installation", "MC4-SET", 8, "Connector set allocation for standard panel stringing."),
            ("Solar Inverter Repair", "INV-5KW-HYB", 1, "Reserve one inverter when replacement is likely."),
            ("CCTV Preventive Maintenance", "CCTV-4MP-DOME", 1, "Spare camera available in case on-site replacement is required."),
            ("Fire Alarm Inspection", "FIRE-SD-ADDR", 2, "Replacement detectors for failed inspection findings."),
            ("AC Service & Installation", "HVAC-COPPER-SET", 1, "Copper tubing allowance for AC installations."),
        ]

        for service_name, sku, quantity, notes in template_rows:
            ServiceTypeInventoryRequirement.objects.update_or_create(
                service_type=service_types[service_name],
                item=items[sku],
                defaults={
                    "quantity": quantity,
                    "auto_reserve": True,
                    "notes": notes,
                },
            )

    def _seed_requests_and_tickets(self, users, service_types, today):
        supervisor = users["supervisor1"]
        tech1 = users["tech1"]
        tech2 = users["tech2"]
        client1 = users["client1"]
        client2 = users["client2"]

        scenarios = [
            {
                "key": "solar_active",
                "client": client1,
                "service_type": service_types["Solar Panel Installation"],
                "description": "Rooftop solar installation for Greenview Residences Tower B.",
                "request_defaults": {
                    "priority": "High",
                    "status": "Approved",
                    "preferred_date": today,
                    "preferred_time_slot": "morning",
                    "scheduling_notes": "Coordinate rooftop access with the building engineer.",
                    "request_date": timezone.now() - timedelta(days=4),
                },
                "location_defaults": {
                    "address": "123 Solar Street, Greenview Residences Tower B",
                    "city": "Makati City",
                    "province": "Metro Manila",
                    "latitude": 14.5547,
                    "longitude": 121.0244,
                },
                "ticket_defaults": {
                    "technician": tech1,
                    "supervisor": supervisor,
                    "scheduled_date": today,
                    "scheduled_time_slot": "morning",
                    "status": "In Progress",
                    "priority": "High",
                    "notes": "Installation team is on-site with full mounting kit.",
                    "start_time": timezone.now() - timedelta(hours=2),
                    "assigned_at": timezone.now() - timedelta(days=1),
                },
            },
            {
                "key": "maintenance_upcoming",
                "client": client2,
                "service_type": service_types["Solar Panel Maintenance"],
                "description": "Quarterly preventive maintenance for the Riverside Suites solar array.",
                "request_defaults": {
                    "priority": "Normal",
                    "status": "Approved",
                    "preferred_date": today + timedelta(days=1),
                    "preferred_time_slot": "afternoon",
                    "scheduling_notes": "Coordinate shutdown window with the property admin.",
                    "request_date": timezone.now() - timedelta(days=2),
                },
                "location_defaults": {
                    "address": "88 Riverside Drive, Riverside Suites",
                    "city": "Quezon City",
                    "province": "Metro Manila",
                    "latitude": 14.6760,
                    "longitude": 121.0437,
                },
                "ticket_defaults": {
                    "technician": tech2,
                    "supervisor": supervisor,
                    "scheduled_date": today + timedelta(days=1),
                    "scheduled_time_slot": "afternoon",
                    "status": "Not Started",
                    "priority": "Normal",
                    "notes": "Technician will perform cleaning, torque checks, and output validation.",
                    "assigned_at": timezone.now(),
                },
            },
            {
                "key": "repair_completed",
                "client": client2,
                "service_type": service_types["Solar Inverter Repair"],
                "description": "Inverter diagnostics and output recovery for the west wing system.",
                "request_defaults": {
                    "priority": "Urgent",
                    "status": "Completed",
                    "preferred_date": today - timedelta(days=5),
                    "preferred_time_slot": "midday",
                    "scheduling_notes": "Restore backup inverter before clinic opening hours.",
                    "request_date": timezone.now() - timedelta(days=8),
                },
                "location_defaults": {
                    "address": "45 West Avenue, St. Helena Clinic",
                    "city": "Quezon City",
                    "province": "Metro Manila",
                    "latitude": 14.6507,
                    "longitude": 121.0300,
                },
                "ticket_defaults": {
                    "technician": tech1,
                    "supervisor": supervisor,
                    "scheduled_date": today - timedelta(days=5),
                    "scheduled_time_slot": "midday",
                    "status": "Completed",
                    "priority": "Urgent",
                    "notes": "Faulty inverter board replaced and output stabilized.",
                    "start_time": timezone.now() - timedelta(days=5, hours=4),
                    "end_time": timezone.now() - timedelta(days=5, hours=1),
                    "completed_date": timezone.now() - timedelta(days=5, hours=1),
                    "client_rating": 5,
                    "client_feedback": "Technician resolved the issue quickly and explained the fix clearly.",
                    "assigned_at": timezone.now() - timedelta(days=6),
                    "warranty_status": "active",
                    "warranty_period_days": 180,
                    "warranty_start_date": today - timedelta(days=5),
                    "warranty_end_date": today + timedelta(days=175),
                    "warranty_notes": "Replacement inverter board covered for six months.",
                },
            },
            {
                "key": "inspection_pending",
                "client": client1,
                "service_type": service_types["Fire Alarm Inspection"],
                "description": "Annual fire alarm inspection for the residential amenity floor.",
                "request_defaults": {
                    "priority": "Normal",
                    "status": "Pending",
                    "preferred_date": today + timedelta(days=3),
                    "preferred_time_slot": "morning",
                    "scheduling_notes": "Coordinate access with the building safety marshal.",
                    "request_date": timezone.now() - timedelta(hours=18),
                },
                "location_defaults": {
                    "address": "17 Pioneer Street, Greenview Residences Amenity Floor",
                    "city": "Mandaluyong City",
                    "province": "Metro Manila",
                    "latitude": 14.5727,
                    "longitude": 121.0469,
                },
            },
        ]

        seeded_requests = {}
        for scenario in scenarios:
            request_obj, _ = ServiceRequest.objects.update_or_create(
                client=scenario["client"],
                service_type=scenario["service_type"],
                description=scenario["description"],
                defaults=scenario["request_defaults"],
            )
            ServiceLocation.objects.update_or_create(
                request=request_obj,
                defaults=scenario["location_defaults"],
            )
            if "ticket_defaults" in scenario:
                ServiceTicket.objects.update_or_create(
                    request=request_obj,
                    defaults=scenario["ticket_defaults"],
                )
            seeded_requests[scenario["key"]] = request_obj
        return seeded_requests

    def _seed_notifications(self, users, seeded_requests):
        notification_rows = [
            {
                "user": users["client1"],
                "request": seeded_requests["solar_active"],
                "title": "Installation Crew Dispatched",
                "message": "Your solar installation team is already on-site and work is in progress.",
                "type": "status_update",
            },
            {
                "user": users["client2"],
                "request": seeded_requests["maintenance_upcoming"],
                "title": "Maintenance Schedule Confirmed",
                "message": "Your preventive maintenance visit is booked for tomorrow afternoon.",
                "type": "reminder",
            },
            {
                "user": users["tech1"],
                "request": seeded_requests["solar_active"],
                "title": "Priority Job Active",
                "message": "Continue installation updates so the admin dashboard reflects live progress.",
                "type": "ticket_assigned",
            },
        ]

        for row in notification_rows:
            Notification.objects.get_or_create(
                user=row["user"],
                request=row["request"],
                title=row["title"],
                defaults={
                    "message": row["message"],
                    "type": row["type"],
                    "status": "unread",
                },
            )
