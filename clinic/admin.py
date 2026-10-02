"""
DentFlow — Django Admin konfiguratsiyasi
"""

from django.contrib import admin
from .models import (
    Doctor, DoctorLeave, ServiceCategory, Service,
    Patient, Appointment, ReminderLog, ClinicSettings
)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'speciality', 'phone', 'slot_duration', 'is_active']
    list_filter = ['is_active', 'speciality']
    search_fields = ['first_name', 'last_name', 'phone']


@admin.register(DoctorLeave)
class DoctorLeaveAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'date', 'reason']
    list_filter = ['doctor', 'date']


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'order']
    ordering = ['order']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'duration', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name']
    filter_horizontal = ['doctors']


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'telegram_id', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'service', 'date', 'start_time', 'status']
    list_filter = ['status', 'date', 'doctor']
    search_fields = ['patient__first_name', 'patient__last_name']
    date_hierarchy = 'date'


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'reminder_type', 'sent_at', 'is_success']
    list_filter = ['reminder_type', 'is_success']


@admin.register(ClinicSettings)
class ClinicSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ClinicSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
