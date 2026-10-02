"""
DentFlow — DRF Serializers
"""

from datetime import datetime, timedelta, date
from django.utils import timezone
from rest_framework import serializers
from .models import (
    Doctor, DoctorLeave, ServiceCategory, Service,
    Patient, Appointment, ReminderLog, ClinicSettings
)


# ─── Service Category ────────────────────────────────────────────────────────

class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'icon', 'order']


# ─── Service ─────────────────────────────────────────────────────────────────

class ServiceListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    price_formatted = serializers.ReadOnlyField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'name_ru', 'description',
            'price', 'price_formatted', 'duration',
            'category', 'category_name', 'is_active'
        ]


class ServiceDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    price_formatted = serializers.ReadOnlyField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'name_ru', 'description',
            'price', 'price_formatted', 'duration',
            'category', 'category_name', 'doctors', 'is_active'
        ]


# ─── Doctor ──────────────────────────────────────────────────────────────────

class DoctorListSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    services = ServiceListSerializer(many=True, read_only=True)
    today_appointments = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'speciality', 'phone', 'telegram_id', 'photo',
            'slot_duration', 'work_start', 'work_end',
            'break_start', 'break_end', 'work_days',
            'is_active', 'services', 'today_appointments', 'created_at'
        ]

    def get_today_appointments(self, obj):
        today = timezone.localdate()
        return obj.appointments.filter(
            date=today,
            status__in=['pending', 'confirmed', 'in_progress']
        ).count()


class DoctorDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    services = ServiceListSerializer(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), many=True, write_only=True,
        source='services', required=False
    )

    class Meta:
        model = Doctor
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'speciality', 'phone', 'telegram_id', 'photo',
            'slot_duration', 'work_start', 'work_end',
            'break_start', 'break_end', 'work_days',
            'is_active', 'services', 'service_ids', 'created_at', 'updated_at'
        ]


class DoctorLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorLeave
        fields = ['id', 'doctor', 'date', 'reason', 'created_at']


# ─── Patient ─────────────────────────────────────────────────────────────────

class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    visit_count = serializers.ReadOnlyField()

    class Meta:
        model = Patient
        fields = [
            'id', 'telegram_id', 'first_name', 'last_name',
            'full_name', 'phone', 'notes', 'visit_count', 'created_at'
        ]


# ─── Appointment ─────────────────────────────────────────────────────────────

class AppointmentListSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone', read_only=True)
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delay_minutes = serializers.ReadOnlyField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_phone',
            'doctor', 'doctor_name', 'service', 'service_name',
            'date', 'start_time', 'end_time',
            'actual_start', 'actual_end',
            'status', 'status_display', 'notes', 'price',
            'delay_minutes', 'created_at', 'updated_at'
        ]


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'patient', 'doctor', 'service',
            'date', 'start_time', 'notes'
        ]

    def validate(self, data):
        doctor = data['doctor']
        appt_date = data['date']
        start_time = data['start_time']
        service = data.get('service')

        # Ish kunini tekshirish
        weekday = appt_date.weekday()
        if doctor.work_days and weekday not in doctor.work_days:
            raise serializers.ValidationError(
                f"Shifokor {appt_date} kuni ishlamaydi."
            )

        # Dam olish kunini tekshirish
        if DoctorLeave.objects.filter(doctor=doctor, date=appt_date).exists():
            raise serializers.ValidationError(
                "Shifokor bu kuni dam olish kuniga ro'yxatdan o'tgan."
            )

        # O'tgan vaqtni tekshirish
        appt_datetime = datetime.combine(appt_date, start_time)
        if timezone.is_naive(appt_datetime):
            appt_datetime = timezone.make_aware(appt_datetime)
        if appt_datetime < timezone.now():
            raise serializers.ValidationError("O'tgan vaqtga qabul yaratib bo'lmaydi.")

        # Ish vaqtini tekshirish
        if start_time < doctor.work_start or start_time >= doctor.work_end:
            raise serializers.ValidationError(
                f"Shifokor ish vaqti: {doctor.work_start} - {doctor.work_end}"
            )

        # Tanaffus vaqtini tekshirish
        if doctor.break_start and doctor.break_end:
            if doctor.break_start <= start_time < doctor.break_end:
                raise serializers.ValidationError(
                    f"Bu vaqt tanaffus vaqtiga to'g'ri keladi: "
                    f"{doctor.break_start} - {doctor.break_end}"
                )

        # Slot mavjudligini tekshirish
        duration = service.duration if service else doctor.slot_duration
        end_time_dt = (
            datetime.combine(appt_date, start_time) + timedelta(minutes=duration)
        ).time()

        conflicting = Appointment.objects.filter(
            doctor=doctor,
            date=appt_date,
            status__in=['pending', 'confirmed', 'in_progress']
        ).exclude(pk=self.instance.pk if self.instance else None)

        for appt in conflicting:
            if start_time < appt.end_time and end_time_dt > appt.start_time:
                raise serializers.ValidationError(
                    f"Bu vaqtda boshqa qabul mavjud ({appt.start_time} - {appt.end_time})."
                )

        data['end_time'] = end_time_dt
        return data


class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    doctor = DoctorListSerializer(read_only=True)
    service = ServiceListSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delay_minutes = serializers.ReadOnlyField()

    class Meta:
        model = Appointment
        fields = '__all__'


# ─── Reminder Log ─────────────────────────────────────────────────────────────

class ReminderLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderLog
        fields = ['id', 'appointment', 'reminder_type', 'message', 'sent_at', 'is_success']


# ─── Clinic Settings ─────────────────────────────────────────────────────────

class ClinicSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicSettings
        fields = [
            'id', 'name', 'address', 'phone',
            'telegram_bot_token', 'work_start', 'work_end',
            'reminder_24h', 'reminder_1h',
            'reminder_24h_template', 'reminder_1h_template',
            'updated_at'
        ]


# ─── Slot Generator ──────────────────────────────────────────────────────────

class SlotSerializer(serializers.Serializer):
    """Bo'sh vaqt slotlari"""
    time = serializers.TimeField()
    is_available = serializers.BooleanField()
    appointment_id = serializers.IntegerField(allow_null=True)


# ─── Dashboard Stats ─────────────────────────────────────────────────────────

class DashboardStatsSerializer(serializers.Serializer):
    today_appointments = serializers.IntegerField()
    today_completed = serializers.IntegerField()
    today_cancelled = serializers.IntegerField()
    today_revenue = serializers.DecimalField(max_digits=15, decimal_places=0)
    week_appointments = serializers.IntegerField()
    week_revenue = serializers.DecimalField(max_digits=15, decimal_places=0)
    month_appointments = serializers.IntegerField()
    month_revenue = serializers.DecimalField(max_digits=15, decimal_places=0)
    total_patients = serializers.IntegerField()
    active_doctors = serializers.IntegerField()
    recent_appointments = AppointmentListSerializer(many=True)
