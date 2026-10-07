"""
DentFlow — DRF Serializers
"""

from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
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
    price_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'name_ru', 'description',
            'price', 'price_formatted', 'duration',
            'category', 'category_name', 'is_active',
        ]

    @extend_schema_field(serializers.CharField())
    def get_price_formatted(self, obj) -> str:
        return obj.price_formatted


class ServiceDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    price_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'name_ru', 'description',
            'price', 'price_formatted', 'duration',
            'category', 'category_name', 'doctors', 'is_active',
        ]

    @extend_schema_field(serializers.CharField())
    def get_price_formatted(self, obj) -> str:
        return obj.price_formatted


# ─── Doctor ──────────────────────────────────────────────────────────────────

class DoctorListSerializer(serializers.ModelSerializer):
    full_name      = serializers.SerializerMethodField()
    services       = ServiceListSerializer(many=True, read_only=True)
    today_appointments = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'speciality', 'phone', 'telegram_id', 'photo',
            'slot_duration', 'work_start', 'work_end',
            'break_start', 'break_end', 'work_days',
            'is_active', 'services', 'today_appointments', 'created_at',
        ]

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj) -> str:
        return obj.full_name

    @extend_schema_field(serializers.IntegerField())
    def get_today_appointments(self, obj) -> int:
        today = timezone.localdate()
        return obj.appointments.filter(
            date=today,
            status__in=['pending', 'confirmed', 'in_progress'],
        ).count()


class DoctorDetailSerializer(serializers.ModelSerializer):
    full_name   = serializers.SerializerMethodField()
    services    = ServiceListSerializer(many=True, read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), many=True,
        write_only=True, source='services', required=False,
    )

    class Meta:
        model = Doctor
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'speciality', 'phone', 'telegram_id', 'photo',
            'slot_duration', 'work_start', 'work_end',
            'break_start', 'break_end', 'work_days',
            'is_active', 'services', 'service_ids', 'created_at', 'updated_at',
        ]

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj) -> str:
        return obj.full_name


class DoctorLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorLeave
        fields = ['id', 'doctor', 'date', 'reason', 'created_at']


# ─── Patient ─────────────────────────────────────────────────────────────────

class PatientSerializer(serializers.ModelSerializer):
    full_name   = serializers.SerializerMethodField()
    visit_count = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'telegram_id', 'first_name', 'last_name',
            'full_name', 'phone', 'notes', 'visit_count', 'created_at',
        ]

    @extend_schema_field(serializers.CharField())
    def get_full_name(self, obj) -> str:
        return obj.full_name

    @extend_schema_field(serializers.IntegerField())
    def get_visit_count(self, obj) -> int:
        return obj.visit_count


# ─── Appointment ─────────────────────────────────────────────────────────────

class AppointmentListSerializer(serializers.ModelSerializer):
    patient_name   = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone  = serializers.CharField(source='patient.phone',     read_only=True)
    doctor_name    = serializers.CharField(source='doctor.full_name',  read_only=True)
    service_name   = serializers.CharField(source='service.name',      read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delay_minutes  = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_phone',
            'doctor', 'doctor_name', 'service', 'service_name',
            'date', 'start_time', 'end_time',
            'actual_start', 'actual_end',
            'status', 'status_display', 'notes', 'price',
            'delay_minutes', 'created_at', 'updated_at',
        ]

    @extend_schema_field(serializers.IntegerField())
    def get_delay_minutes(self, obj) -> int:
        return obj.delay_minutes


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'service', 'date', 'start_time', 'notes']

    def validate(self, data):
        doctor     = data['doctor']
        appt_date  = data['date']
        start_time = data['start_time']
        service    = data.get('service')

        if doctor.work_days and appt_date.weekday() not in doctor.work_days:
            raise serializers.ValidationError(f"Shifokor {appt_date} kuni ishlamaydi.")

        if DoctorLeave.objects.filter(doctor=doctor, date=appt_date).exists():
            raise serializers.ValidationError("Shifokor bu kuni dam oladi.")

        appt_dt = datetime.combine(appt_date, start_time)
        if timezone.is_naive(appt_dt):
            appt_dt = timezone.make_aware(appt_dt)
        if appt_dt < timezone.now():
            raise serializers.ValidationError("O'tgan vaqtga qabul yaratib bo'lmaydi.")

        if start_time < doctor.work_start or start_time >= doctor.work_end:
            raise serializers.ValidationError(
                f"Shifokor ish vaqti: {doctor.work_start} – {doctor.work_end}"
            )

        if doctor.break_start and doctor.break_end:
            if doctor.break_start <= start_time < doctor.break_end:
                raise serializers.ValidationError(
                    f"Bu vaqt tanaffusga to'g'ri keladi: "
                    f"{doctor.break_start} – {doctor.break_end}"
                )

        duration    = service.duration if service else doctor.slot_duration
        end_time_dt = (
            datetime.combine(appt_date, start_time) + timedelta(minutes=duration)
        ).time()

        conflicting = Appointment.objects.filter(
            doctor=doctor, date=appt_date,
            status__in=['pending', 'confirmed', 'in_progress'],
        ).exclude(pk=self.instance.pk if self.instance else None)

        for appt in conflicting:
            if start_time < appt.end_time and end_time_dt > appt.start_time:
                raise serializers.ValidationError(
                    f"Bu vaqtda qabul band ({appt.start_time}–{appt.end_time})."
                )

        data['end_time'] = end_time_dt
        return data


class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient        = PatientSerializer(read_only=True)
    doctor         = DoctorListSerializer(read_only=True)
    service        = ServiceListSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delay_minutes  = serializers.SerializerMethodField()

    class Meta:
        model  = Appointment
        fields = '__all__'

    @extend_schema_field(serializers.IntegerField())
    def get_delay_minutes(self, obj) -> int:
        return obj.delay_minutes


# ─── Reminder Log ────────────────────────────────────────────────────────────

class ReminderLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ReminderLog
        fields = ['id', 'appointment', 'reminder_type', 'message', 'sent_at', 'is_success']


# ─── Clinic Settings ─────────────────────────────────────────────────────────

class ClinicSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ClinicSettings
        fields = [
            'id', 'name', 'address', 'phone',
            'telegram_bot_token', 'work_start', 'work_end',
            'reminder_24h', 'reminder_1h',
            'reminder_24h_template', 'reminder_1h_template',
            'updated_at',
        ]


# ─── Slot ────────────────────────────────────────────────────────────────────

class SlotSerializer(serializers.Serializer):
    """Bo'sh vaqt sloti"""
    time           = serializers.TimeField()
    is_available   = serializers.BooleanField()
    appointment_id = serializers.IntegerField(allow_null=True)


class SlotResponseSerializer(serializers.Serializer):
    """GET /doctors/{id}/slots/ javobi"""
    slots   = SlotSerializer(many=True)
    message = serializers.CharField(required=False, allow_blank=True)


# ─── Dashboard Stats ─────────────────────────────────────────────────────────

class DashboardStatsSerializer(serializers.Serializer):
    today_appointments  = serializers.IntegerField()
    today_completed     = serializers.IntegerField()
    today_cancelled     = serializers.IntegerField()
    today_revenue       = serializers.DecimalField(max_digits=15, decimal_places=0)
    week_appointments   = serializers.IntegerField()
    week_revenue        = serializers.DecimalField(max_digits=15, decimal_places=0)
    month_appointments  = serializers.IntegerField()
    month_revenue       = serializers.DecimalField(max_digits=15, decimal_places=0)
    total_patients      = serializers.IntegerField()
    active_doctors      = serializers.IntegerField()
    recent_appointments = AppointmentListSerializer(many=True)


# ─── Revenue Stats ────────────────────────────────────────────────────────────

class DailyRevenueSerializer(serializers.Serializer):
    date         = serializers.DateField()
    revenue      = serializers.FloatField()
    appointments = serializers.IntegerField()


class TopDoctorSerializer(serializers.Serializer):
    doctor__id         = serializers.IntegerField()
    doctor__first_name = serializers.CharField()
    doctor__last_name  = serializers.CharField()
    revenue            = serializers.FloatField()
    count              = serializers.IntegerField()


class TopServiceSerializer(serializers.Serializer):
    service__id   = serializers.IntegerField()
    service__name = serializers.CharField()
    revenue       = serializers.FloatField()
    count         = serializers.IntegerField()


class RevenueStatsSerializer(serializers.Serializer):
    period      = serializers.CharField()
    daily       = DailyRevenueSerializer(many=True)
    top_doctors = TopDoctorSerializer(many=True)
    top_services = TopServiceSerializer(many=True)


# ─── Simple message serializer (action responses uchun) ─────────────────────

class CancelRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
