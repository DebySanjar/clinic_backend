"""
DentFlow — Clinic URL Configuration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'doctors', views.DoctorViewSet, basename='doctor')
router.register(r'service-categories', views.ServiceCategoryViewSet, basename='service-category')
router.register(r'services', views.ServiceViewSet, basename='service')
router.register(r'patients', views.PatientViewSet, basename='patient')
router.register(r'appointments', views.AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('', include(router.urls)),

    # Stats
    path('stats/dashboard/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('stats/revenue/', views.RevenueStatsView.as_view(), name='revenue-stats'),

    # Clinic settings
    path('settings/', views.ClinicSettingsView.as_view(), name='clinic-settings'),

    # Telegram webhook
    path('bot/webhook/', views.telegram_webhook, name='telegram-webhook'),
]
