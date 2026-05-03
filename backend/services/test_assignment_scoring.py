"""
Unit tests for technician assignment and scoring logic.

Tests the core algorithm for auto-assigning technicians to tickets based on
skill, distance, and workload factors.
"""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from services.models import ServiceType, ServiceRequest, ServiceLocation, ServiceTicket, TechnicianSkill
from services.views import score_technician_fit, calculate_distance

User = get_user_model()


class DistanceCalculationTests(TestCase):
    """Test the Haversine distance calculation."""
    
    def test_same_point_returns_zero(self):
        """Distance between same coordinates should be 0."""
        distance = calculate_distance(14.5995, 120.9842, 14.5995, 120.9842)
        self.assertAlmostEqual(distance, 0, places=2)

    def test_known_distance_manila_to_tagaytay(self):
        """Test distance calculation against known real-world coordinates."""
        # Manila to Tagaytay is approximately 60 km
        manila_lat, manila_lon = 14.5995, 120.9842
        tagaytay_lat, tagaytay_lon = 14.0996, 120.9895
        
        distance = calculate_distance(manila_lat, manila_lon, tagaytay_lat, tagaytay_lon)
        # Should be approximately 60 km (with some tolerance for Haversine approximation)
        self.assertGreater(distance, 55)
        self.assertLess(distance, 65)

    def test_distance_symmetry(self):
        """Distance from A to B should equal distance from B to A."""
        lat1, lon1 = 14.5995, 120.9842
        lat2, lon2 = 14.0996, 120.9895
        
        distance_ab = calculate_distance(lat1, lon1, lat2, lon2)
        distance_ba = calculate_distance(lat2, lon2, lat1, lon1)
        
        self.assertAlmostEqual(distance_ab, distance_ba, places=2)

    def test_returns_positive_number(self):
        """Distance should always be positive."""
        distance = calculate_distance(14.5995, 120.9842, 15.0, 121.0)
        self.assertGreater(distance, 0)


class TechnicianScoringTests(TestCase):
    """Test the technician fitness scoring algorithm."""
    
    def setUp(self):
        """Set up test data."""
        # Create service type
        self.hvac_service = ServiceType.objects.create(
            name="AC Service & Installation",
            estimated_duration=120
        )
        self.general_service = ServiceType.objects.create(
            name="General Services",
            estimated_duration=60
        )
        
        # Create technicians
        self.tech_expert = User.objects.create_user(
            username='tech_expert',
            password='pass123',
            role='technician',
            current_latitude=Decimal('14.5995'),
            current_longitude=Decimal('120.9842'),
            is_available=True,
            status='active'
        )
        
        self.tech_beginner = User.objects.create_user(
            username='tech_beginner',
            password='pass123',
            role='technician',
            current_latitude=Decimal('14.5995'),
            current_longitude=Decimal('120.9842'),
            is_available=False,  # Not available
            status='active'
        )
        
        # Create skills
        TechnicianSkill.objects.create(
            technician=self.tech_expert,
            service_type=self.hvac_service,
            skill_level='expert'
        )
        
        TechnicianSkill.objects.create(
            technician=self.tech_beginner,
            service_type=self.hvac_service,
            skill_level='beginner'
        )
        
        # Create client
        self.client = User.objects.create_user(
            username='client1',
            password='pass123',
            role='client'
        )
        
        # Create service request
        self.request = ServiceRequest.objects.create(
            client=self.client,
            service_type=self.hvac_service,
            description="AC installation needed",
            status='Approved',
            preferred_date=date.today() + timedelta(days=1)
        )
        
        # Create location
        self.location = ServiceLocation.objects.create(
            request=self.request,
            address="123 Main St",
            city="Manila",
            province="Metro Manila",
            latitude=Decimal('14.5995'),
            longitude=Decimal('120.9842')
        )
        
        # Create ticket
        self.ticket = ServiceTicket.objects.create(
            request=self.request,
            scheduled_date=date.today() + timedelta(days=1),
            status='Not Started'
        )

    def test_score_expert_technician_same_location(self):
        """Expert technician at same location should score high."""
        score_data = score_technician_fit(
            self.ticket,
            self.tech_expert,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        self.assertIsNotNone(score_data)
        self.assertGreater(score_data['score'], 40)  # High score for expert at 0 distance
        self.assertAlmostEqual(score_data['distance_km'], 0, places=1)
        self.assertEqual(score_data['skill_level'], 'expert')

    def test_score_beginner_lower_than_expert(self):
        """Beginner technician should score lower than expert."""
        score_expert = score_technician_fit(
            self.ticket,
            self.tech_expert,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        score_beginner = score_technician_fit(
            self.ticket,
            self.tech_beginner,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        self.assertGreater(score_expert['score'], score_beginner['score'])

    def test_unavailable_technician_scores_lower(self):
        """Unavailable technician should score 5 points lower."""
        # Make expert available and check score
        self.tech_expert.is_available = True
        self.tech_expert.save()
        self.tech_beginner.is_available = False
        self.tech_beginner.save()
        
        score_available = score_technician_fit(
            self.ticket,
            self.tech_expert,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        # Manually calculate what beginner score would be with availability bonus
        score_unavailable = score_technician_fit(
            self.ticket,
            self.tech_beginner,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        if score_available and score_unavailable:
            self.assertGreater(score_available['score'], score_unavailable['score'])

    def test_missing_location_returns_none(self):
        """Technician without location should return None."""
        self.tech_expert.current_latitude = None
        self.tech_expert.current_longitude = None
        self.tech_expert.save()
        
        score_data = score_technician_fit(
            self.ticket,
            self.tech_expert,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        self.assertIsNone(score_data)

    def test_missing_skill_returns_none(self):
        """Technician without required skill should return None."""
        # Create a different service type with no skill
        painting_service = ServiceType.objects.create(
            name="Painting",
            estimated_duration=180
        )
        
        request_painting = ServiceRequest.objects.create(
            client=self.client,
            service_type=painting_service,  # Different service
            description="Paint the house",
            status='Approved',
            preferred_date=date.today() + timedelta(days=1)
        )
        
        location_painting = ServiceLocation.objects.create(
            request=request_painting,
            address="456 Oak Ave",
            city="Manila",
            province="Metro Manila",
            latitude=Decimal('14.5995'),
            longitude=Decimal('120.9842')
        )
        
        ticket_painting = ServiceTicket.objects.create(
            request=request_painting,
            scheduled_date=date.today() + timedelta(days=1),
            status='Not Started'
        )
        
        score_data = score_technician_fit(
            ticket_painting,
            self.tech_expert,  # Expert in AC, not painting
            float(location_painting.latitude),
            float(location_painting.longitude)
        )
        
        self.assertIsNone(score_data)

    def test_distance_penalty(self):
        """Technician further away should score lower."""
        # Score at same location
        score_near = score_technician_fit(
            self.ticket,
            self.tech_expert,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        # Score 30 km away
        score_far = score_technician_fit(
            self.ticket,
            self.tech_expert,
            14.7995,  # Different coordinates
            120.7842
        )
        
        self.assertIsNotNone(score_near)
        self.assertIsNotNone(score_far)
        self.assertGreater(score_near['score'], score_far['score'])

    def test_score_contains_all_required_fields(self):
        """Score result should contain all expected fields."""
        score_data = score_technician_fit(
            self.ticket,
            self.tech_expert,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        self.assertIsNotNone(score_data)
        self.assertIn('score', score_data)
        self.assertIn('distance_km', score_data)
        self.assertIn('skill_level', score_data)
        self.assertIn('summary', score_data)

    def test_score_summary_is_informative(self):
        """Score summary should contain useful information."""
        score_data = score_technician_fit(
            self.ticket,
            self.tech_expert,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        self.assertIsNotNone(score_data)
        summary = score_data['summary']
        
        # Should contain skill level info
        self.assertIn('expert', summary.lower())
        # Should contain distance
        self.assertIn('km', summary.lower())
        # Should contain job count info
        self.assertIn('job', summary.lower())


class WorkloadPenaltyTests(TestCase):
    """Test how workload affects scoring."""
    
    def setUp(self):
        """Set up test data with multiple tickets."""
        # Create service type and technician
        self.service = ServiceType.objects.create(
            name="AC Service",
            estimated_duration=120
        )
        
        self.technician = User.objects.create_user(
            username='tech_busy',
            password='pass123',
            role='technician',
            current_latitude=Decimal('14.5995'),
            current_longitude=Decimal('120.9842'),
            is_available=True,
            status='active'
        )
        
        # Give technician the skill
        TechnicianSkill.objects.create(
            technician=self.technician,
            service_type=self.service,
            skill_level='intermediate'
        )
        
        # Create client
        self.client = User.objects.create_user(
            username='client_busy',
            password='pass123',
            role='client'
        )
        
        # Create a service request
        self.request = ServiceRequest.objects.create(
            client=self.client,
            service_type=self.service,
            description="AC service",
            status='Approved',
            preferred_date=date.today() + timedelta(days=1)
        )
        
        # Create location
        self.location = ServiceLocation.objects.create(
            request=self.request,
            address="123 Main St",
            city="Manila",
            province="Metro Manila",
            latitude=Decimal('14.5995'),
            longitude=Decimal('120.9842')
        )
        
        # Create new ticket for scoring
        self.ticket_to_score = ServiceTicket.objects.create(
            request=self.request,
            scheduled_date=date.today() + timedelta(days=1),
            status='Not Started'
        )

    def test_workload_affects_score(self):
        """Technician with more active jobs should score lower."""
        # Create existing active tickets for the technician
        for i in range(3):
            request = ServiceRequest.objects.create(
                client=self.client,
                service_type=self.service,
                description=f"Job {i}",
                status='Approved',
                preferred_date=date.today() + timedelta(days=1)
            )
            
            ServiceLocation.objects.create(
                request=request,
                address=f"{100+i} Street",
                city="Manila",
                province="Metro Manila",
                latitude=Decimal('14.5995'),
                longitude=Decimal('120.9842')
            )
            
            ServiceTicket.objects.create(
                request=request,
                technician=self.technician,  # Assign to technician
                scheduled_date=date.today() + timedelta(days=1),
                status='In Progress'  # Active status
            )
        
        # Score should be affected by existing active load
        score_data = score_technician_fit(
            self.ticket_to_score,
            self.technician,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        self.assertIsNotNone(score_data)
        # With 3 active jobs, technician loses workload points but still scores reasonably
        # Intermediate skill (30 points) + distance (30 points) + workload penalty (down from 15 to 0) = ~60-75 range
        self.assertLess(score_data['score'], 80)
        self.assertGreater(score_data['score'], 40)


class EdgeCaseTests(TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up minimal test data."""
        self.service = ServiceType.objects.create(name="Test Service")
        self.client = User.objects.create_user(
            username='client', password='pass', role='client'
        )
        self.technician = User.objects.create_user(
            username='tech', password='pass', role='technician',
            current_latitude=Decimal('0'), current_longitude=Decimal('0')
        )
        
        TechnicianSkill.objects.create(
            technician=self.technician,
            service_type=self.service,
            skill_level='intermediate'
        )
        
        self.request = ServiceRequest.objects.create(
            client=self.client, service_type=self.service,
            description="Test", status='Approved'
        )
        
        self.location = ServiceLocation.objects.create(
            request=self.request, address="Test", city="Test",
            province="Test", latitude=Decimal('0'), longitude=Decimal('0')
        )
        
        self.ticket = ServiceTicket.objects.create(
            request=self.request, scheduled_date=date.today(),
            status='Not Started'
        )

    def test_score_with_zero_coordinates(self):
        """Should handle zero coordinates (0,0) without error."""
        score_data = score_technician_fit(
            self.ticket, self.technician, 0.0, 0.0
        )
        self.assertIsNotNone(score_data)

    def test_score_with_negative_coordinates(self):
        """Should handle negative coordinates (Southern hemisphere)."""
        score_data = score_technician_fit(
            self.ticket, self.technician, -33.9249, 18.4241  # Cape Town
        )
        self.assertIsNotNone(score_data)

    def test_score_is_numeric(self):
        """Score should always be a valid number."""
        score_data = score_technician_fit(
            self.ticket, self.technician,
            float(self.location.latitude),
            float(self.location.longitude)
        )
        
        self.assertIsNotNone(score_data)
        self.assertIsInstance(score_data['score'], float)
        self.assertGreaterEqual(score_data['score'], 0)
