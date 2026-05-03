from django.db import models
from django.conf import settings
from django.utils import timezone

TIME_SLOT_CHOICES = [
    ('morning', 'Morning (8 AM - 11 AM)'),
    ('midday', 'Midday (11 AM - 2 PM)'),
    ('afternoon', 'Afternoon (2 PM - 5 PM)'),
    ('evening', 'Evening (5 PM - 8 PM)'),
]


class ServiceType(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    estimated_duration = models.IntegerField(default=60)  # in minutes

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Normal', 'Normal'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]
    
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'client'}
    )
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    description = models.TextField()
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default="Normal")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Pending")
    preferred_date = models.DateField(blank=True, null=True)
    preferred_time_slot = models.CharField(
        max_length=20,
        choices=TIME_SLOT_CHOICES,
        blank=True,
        null=True,
    )
    scheduling_notes = models.TextField(blank=True, null=True)
    request_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Auto-ticket will be created when request is approved
    auto_ticket_created = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['client_id', 'status']),
            models.Index(fields=['status', 'request_date']),
        ]
        ordering = ['-request_date']

    def __str__(self):
        return f"{self.service_type.name} request by {self.client.username}"


class ServiceLocation(models.Model):
    request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='location')
    address = models.TextField()
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    def __str__(self):
        return f"{self.address}, {self.city}"


class ServiceTicket(models.Model):
    STATUS_CHOICES = [
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('On Hold', 'On Hold'),
        ('Cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Normal', 'Normal'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]

    WARRANTY_STATUS_CHOICES = [
        ('not_applicable', 'Not Applicable'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('void', 'Void'),
    ]
    
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE)
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_tickets',
        limit_choices_to={'role': 'technician'}
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='supervised_tickets',
        limit_choices_to={'role': 'supervisor'}
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    scheduled_time_slot = models.CharField(
        max_length=20,
        choices=TIME_SLOT_CHOICES,
        blank=True,
        null=True,
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Not Started")
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default="Normal")
    notes = models.TextField(blank=True, null=True)
    
    # Client feedback
    client_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    client_feedback = models.TextField(blank=True, null=True)
    
    # For auto-assignment
    auto_assigned = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(null=True, blank=True)
    smart_assignment_score = models.FloatField(blank=True, null=True)
    smart_assignment_summary = models.CharField(max_length=255, blank=True, null=True)

    # Scheduling updates
    reschedule_requested = models.BooleanField(default=False)
    reschedule_reason = models.TextField(blank=True, null=True)
    reschedule_requested_at = models.DateTimeField(blank=True, null=True)

    # Warranty coverage
    warranty_status = models.CharField(
        max_length=20,
        choices=WARRANTY_STATUS_CHOICES,
        default='not_applicable',
    )
    warranty_period_days = models.PositiveIntegerField(blank=True, null=True)
    warranty_start_date = models.DateField(blank=True, null=True)
    warranty_end_date = models.DateField(blank=True, null=True)
    warranty_notes = models.TextField(blank=True, null=True)

    # Route information (optional, populated when technician assigned)
    route_geometry = models.JSONField(null=True, blank=True)
    route_distance = models.FloatField(null=True, blank=True)  # meters
    route_duration = models.FloatField(null=True, blank=True)  # seconds

    # Job completion proof (images)
    completion_proof_images = models.JSONField(
        default=list,
        blank=True,
        help_text="List of image URLs uploaded as proof of job completion"
    )
    completion_notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['technician_id', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['auto_assigned', 'assigned_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Ticket {self.id} for {self.request}"


class TicketCrewAssignment(models.Model):
    ticket = models.ForeignKey(
        ServiceTicket,
        on_delete=models.CASCADE,
        related_name='crew_assignments',
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='crew_ticket_assignments',
        limit_choices_to={'role': 'technician'},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['ticket', 'technician'],
                name='unique_ticket_crew_assignment',
            )
        ]

    def __str__(self):
        return f"Ticket #{self.ticket_id} crew: {self.technician.username}"


class AfterSalesCase(models.Model):
    CASE_TYPE_CHOICES = [
        ('follow_up', 'Follow Up'),
        ('maintenance', 'Maintenance'),
        ('complaint', 'Complaint'),
        ('warranty', 'Warranty'),
        ('revisit', 'Revisit'),
        ('feedback', 'Feedback'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    CREATION_SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('completion_flow', 'Completion Flow'),
        ('maintenance_alert', 'Maintenance Alert'),
    ]

    service_ticket = models.ForeignKey(ServiceTicket, on_delete=models.CASCADE, related_name='after_sales_cases')
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='after_sales_cases',
        limit_choices_to={'role': 'client'}
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_after_sales_cases',
        limit_choices_to={'role': 'follow_up'}
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_after_sales_cases'
    )
    case_type = models.CharField(max_length=20, choices=CASE_TYPE_CHOICES, default='follow_up')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    creation_source = models.CharField(
        max_length=30,
        choices=CREATION_SOURCE_CHOICES,
        default='manual',
    )
    summary = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    requires_revisit = models.BooleanField(default=False)
    customer_satisfaction = models.PositiveSmallIntegerField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_case_type_display()} for ticket #{self.service_ticket_id}"

    class Meta:
        ordering = ['-created_at']


class MaintenanceSchedule(models.Model):
    PROFILE_CHOICES = [
        ('commercial_area', 'Commercial Area'),
        ('dust_free_area', 'Dust-Free Area'),
        ('standard_area', 'Standard Area'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('due_soon', 'Due Soon'),
        ('due', 'Due'),
        ('completed', 'Completed'),
        ('dismissed', 'Dismissed'),
    ]

    service_ticket = models.OneToOneField(
        ServiceTicket,
        on_delete=models.CASCADE,
        related_name='maintenance_schedule'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='maintenance_schedules',
        limit_choices_to={'role': 'client'}
    )
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name='maintenance_schedules')
    maintenance_profile = models.CharField(max_length=30, choices=PROFILE_CHOICES)
    interval_days = models.PositiveIntegerField()
    follow_up_window_days = models.PositiveIntegerField(default=14)
    last_service_date = models.DateField()
    next_due_date = models.DateField()
    notify_on_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    maintenance_notes = models.TextField(blank=True, null=True)
    due_soon_notified_at = models.DateTimeField(blank=True, null=True)
    due_notified_at = models.DateTimeField(blank=True, null=True)
    risk_level = models.CharField(max_length=20, default='normal')
    risk_score = models.FloatField(default=0)
    prediction_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Maintenance for ticket #{self.service_ticket_id} due {self.next_due_date}"

    class Meta:
        ordering = ['next_due_date', 'id']


class TechnicianSkill(models.Model):
    SKILL_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('expert', 'Expert'),
    ]
    
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'technician'}
    )
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    skill_level = models.CharField(max_length=50, choices=SKILL_LEVELS)

    class Meta:
        unique_together = ('technician', 'service_type')

    def __str__(self):
        return f"{self.technician.username} - {self.service_type.name} ({self.skill_level})"


# Real-time tracking: Service Status Timeline
class ServiceStatusHistory(models.Model):
    """Tracks all status changes for audit trail"""
    ticket = models.ForeignKey(ServiceTicket, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Ticket {self.ticket.id} - {self.status} at {self.timestamp}"


# Pre-installation Inspection Checklist
class InspectionChecklist(models.Model):
    """Digital pre-installation inspection checklist"""
    MAINTENANCE_PROFILE_CHOICES = MaintenanceSchedule.PROFILE_CHOICES
    FOLLOW_UP_CASE_TYPE_CHOICES = [
        choice for choice in AfterSalesCase.CASE_TYPE_CHOICES
        if choice[0] != 'maintenance'
    ]

    ticket = models.OneToOneField(ServiceTicket, on_delete=models.CASCADE, related_name='inspection')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_inspections'
    )
    is_completed = models.BooleanField(default=False)
    
    # Site Assessment
    site_accessible = models.BooleanField(default=False)
    site_accessible_notes = models.TextField(blank=True, null=True)
    
    # Electrical Check
    electrical_available = models.BooleanField(default=False)
    electrical_adequate = models.BooleanField(default=False)
    electrical_notes = models.TextField(blank=True, null=True)
    
    # Structural Check
    roof_condition = models.CharField(max_length=100, blank=True, null=True)
    structural_assessment = models.TextField(blank=True, null=True)
    
    # Safety Check
    safety_equipment_present = models.BooleanField(default=False)
    safety_hazards = models.TextField(blank=True, null=True)
    
    # Overall
    recommendation = models.CharField(max_length=100, blank=True, null=True)  # Approved, Conditional, Rejected
    additional_notes = models.TextField(blank=True, null=True)

    # Planned maintenance
    maintenance_required = models.BooleanField(default=False)
    maintenance_profile = models.CharField(
        max_length=30,
        choices=MAINTENANCE_PROFILE_CHOICES,
        blank=True,
        null=True
    )
    maintenance_interval_days = models.PositiveIntegerField(blank=True, null=True)
    maintenance_notes = models.TextField(blank=True, null=True)
    proof_media = models.JSONField(default=list, blank=True)
    warranty_provided = models.BooleanField(default=False)
    warranty_period_days = models.PositiveIntegerField(blank=True, null=True)
    warranty_notes = models.TextField(blank=True, null=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_case_type = models.CharField(
        max_length=20,
        choices=FOLLOW_UP_CASE_TYPE_CHOICES,
        blank=True,
        null=True,
    )
    follow_up_due_date = models.DateField(blank=True, null=True)
    follow_up_summary = models.CharField(max_length=255, blank=True, null=True)
    follow_up_details = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Inspection for Ticket {self.ticket.id}"


# Technician Location History for tracking
class TechnicianLocationHistory(models.Model):
    """Track technician movements for history"""
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'technician'}
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)
    accuracy = models.FloatField(default=0)  # GPS accuracy in meters
    
    def __str__(self):
        return f"{self.technician.username} at {self.timestamp}"


# Analytics Models for Descriptive and Predictive Analysis
class ServiceAnalytics(models.Model):
    """Aggregated analytics data for services"""
    date = models.DateField()
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, null=True, blank=True)
    
    # Descriptive metrics
    total_requests = models.IntegerField(default=0)
    completed_requests = models.IntegerField(default=0)
    pending_requests = models.IntegerField(default=0)
    cancelled_requests = models.IntegerField(default=0)
    
    # Performance metrics
    avg_response_time_hours = models.FloatField(default=0)  # Average time to assign technician
    avg_completion_time_hours = models.FloatField(default=0)  # Average time to complete
    technician_utilization_rate = models.FloatField(default=0)  # Percentage of time technicians are busy
    
    # Geographic metrics
    service_area_coverage = models.FloatField(default=0)  # Square km covered
    popular_locations = models.JSONField(default=list)  # Top service locations
    
    # Customer satisfaction (placeholder for future ratings)
    satisfaction_score = models.FloatField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['date', 'service_type']
        ordering = ['-date']
    
    def __str__(self):
        service_name = self.service_type.name if self.service_type else "All Services"
        return f"{service_name} Analytics - {self.date}"


class TechnicianPerformance(models.Model):
    """Individual technician performance metrics"""
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'technician'})
    date = models.DateField()
    
    # Work metrics
    tickets_assigned = models.IntegerField(default=0)
    tickets_completed = models.IntegerField(default=0)
    tickets_pending = models.IntegerField(default=0)
    
    # Time metrics
    total_work_hours = models.FloatField(default=0)
    avg_response_time_hours = models.FloatField(default=0)
    avg_completion_time_hours = models.FloatField(default=0)
    
    # Quality metrics
    customer_satisfaction = models.FloatField(default=0)
    rework_rate = models.FloatField(default=0)  # Percentage requiring rework
    
    # Efficiency metrics
    distance_traveled_km = models.FloatField(default=0)
    fuel_efficiency = models.FloatField(default=0)  # km per liter
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['technician', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.technician.username} Performance - {self.date}"


class DemandForecast(models.Model):
    """Predictive demand forecasting"""
    FORECAST_PERIODS = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name='service_demands')
    forecast_date = models.DateField()  # Date this forecast is for
    forecast_period = models.CharField(max_length=20, choices=FORECAST_PERIODS, default='daily')
    
    # Forecasted demand
    predicted_requests = models.IntegerField()
    confidence_level = models.FloatField(default=0.8)  # 0-1 confidence score
    
    # Factors influencing forecast
    weather_impact = models.FloatField(default=0)  # -1 to 1 (negative/positive impact)
    seasonal_trend = models.FloatField(default=0)  # Seasonal adjustment factor
    historical_average = models.IntegerField(default=0)  # Base historical average
    
    # Forecast accuracy tracking
    actual_requests = models.IntegerField(null=True, blank=True)  # Filled in after the date
    forecast_accuracy = models.FloatField(null=True, blank=True)  # Calculated accuracy
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-forecast_date']
    
    def __str__(self):
        return f"{self.service_type.name} forecast for {self.forecast_date} ({self.predicted_requests} requests)"


class ServiceTrend(models.Model):
    """Trend analysis for service patterns"""
    TREND_TYPES = [
        ('seasonal', 'Seasonal'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    trend_type = models.CharField(max_length=20, choices=TREND_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Trend metrics
    average_requests = models.FloatField()
    peak_day = models.CharField(max_length=20, blank=True)  # e.g., "Monday", "Winter"
    peak_hour = models.IntegerField(null=True, blank=True)  # 0-23
    
    # Growth indicators
    growth_rate = models.FloatField(default=0)  # Percentage change
    trend_direction = models.CharField(max_length=20, default='stable')  # increasing, decreasing, stable
    
    # Statistical measures
    standard_deviation = models.FloatField(default=0)
    confidence_interval = models.JSONField(default=dict)  # min/max confidence bounds
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.service_type.name} {self.trend_type} trend ({self.period_start} to {self.period_end})"
