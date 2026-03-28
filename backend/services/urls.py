from django.urls import path, include
from rest_framework import routers
from .views import (
    ServiceTypeViewSet, ServiceRequestViewSet, ServiceLocationViewSet,
    ServiceTicketViewSet, TechnicianSkillViewSet, ServiceStatusHistoryViewSet,
    InspectionChecklistViewSet, TechnicianLocationHistoryViewSet, GISDashboardView,
    ServiceAnalyticsViewSet, TechnicianPerformanceViewSet, DemandForecastViewSet, ServiceTrendViewSet,
    TechnicianClientsView, StatusReportsViewSet, ORSViewSet, CoverageHeatmapViewSet,
    TechnicianDashboardView, TechnicianJobsView, TechnicianScheduleView
)
from .views_follow_up import FollowUpCaseViewSet
from .views_dashboard import DashboardView

router = routers.DefaultRouter()
router.register(r'service-types', ServiceTypeViewSet)
router.register(r'service-requests', ServiceRequestViewSet)
router.register(r'service-locations', ServiceLocationViewSet)
router.register(r'service-tickets', ServiceTicketViewSet)
router.register(r'technician-skills', TechnicianSkillViewSet)
router.register(r'status-history', ServiceStatusHistoryViewSet)
router.register(r'inspections', InspectionChecklistViewSet)
router.register(r'technician-locations', TechnicianLocationHistoryViewSet)
router.register(r'gis-dashboard', GISDashboardView, basename='gis-dashboard')
router.register(r'analytics', ServiceAnalyticsViewSet)
router.register(r'technician-performance', TechnicianPerformanceViewSet)
router.register(r'demand-forecasts', DemandForecastViewSet)
router.register(r'service-trends', ServiceTrendViewSet)
router.register(r'technician-dashboard', TechnicianDashboardView, basename='technician-dashboard')
router.register(r'technician-jobs', TechnicianJobsView, basename='technician-jobs')
router.register(r'technician-schedule', TechnicianScheduleView, basename='technician-schedule')
router.register(r'follow-up-cases', FollowUpCaseViewSet, basename='follow-up-cases')
router.register(r'coverage-heatmap', CoverageHeatmapViewSet, basename='coverage-heatmap')
router.register(r'ors', ORSViewSet, basename='ors')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardView.as_view(), name='role-dashboard'),
    path('technician/location/', TechnicianLocationHistoryViewSet.as_view({'post': 'update_location'}), name='technician-location'),
    path('technician-clients/', TechnicianClientsView.as_view({'get': 'list'}), name='technician-clients'),
]
