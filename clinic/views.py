"""
DentFlow — DRF Views
"""

import asyncio
from datetime import datetime, timedelta, date, time
from decimal import Decimal

from django.utils import timezone
from django.db.models import Sum, Count, Q

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import (
    extend_schema, extend_schema_view,
    OpenApiParameter, OpenApiExample,
)
from drf_spectacular.types import OpenApiTypes

from .models import (
    Doctor, DoctorLeave, ServiceCategory, Service,
    Patient, Appointment, ReminderLog, ClinicSettings
)
from .serializers import (
    DoctorListSerializer, DoctorDetailSerializer, DoctorLeaveSerializer,
    ServiceCategorySerializer, ServiceListSerializer, ServiceDetailSerializer,
    PatientSerializer, AppointmentListSerializer, AppointmentCreateSerializer,
    AppointmentDetailSerializer, ReminderLogSerializer,
    ClinicSettingsSerializer, DashboardStatsSerializer,
    SlotSerializer, SlotResponseSerializer,
    RevenueStatsSerializer, CancelRequestSerializer,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def generate_slots(doctor: Doctor, target_date: date) -> list:
    """Shifokor uchun bo'sh vaqt slotlarini yaratish"""
    slots = []
    duration = doctor.slot_duration

    # Mavjud qabullarni olish
    existing = Appointment.objects.filter(
        doctor=doctor,
        date=target_date,
        status__in=['pending', 'confirmed', 'in_progress']
    ).values_list('start_time', 'end_time', 'id')

    booked_slots = {(s, e): appt_id for s, e, appt_id in existing}

    current = datetime.combine(target_date, doctor.work_start)
    work_end = datetime.combine(target_date, doctor.work_end)

    while current + timedelta(minutes=duration) <= work_end:
        slot_time = current.time()
        slot_end = (current + timedelta(minutes=duration)).time()

        # Tanaffus tekshiruvi
        in_break = False
        if doctor.break_start and doctor.break_end:
            if doctor.break_start <= slot_time < doctor.break_end:
                in_break = True

        # Band tekshiruvi
        is_booked = False
        appt_id = None
        for (s, e), aid in booked_slots.items():
            if slot_time < e and slot_end > s:
                is_booked = True
                appt_id = aid
                break

        if not in_break:
            slots.append({
                'time': slot_time,
                'is_available': not is_booked,
                'appointment_id': appt_id if is_booked else None,
            })

        current += timedelta(minutes=duration)

    return slots


# ─── Doctor ViewSet ───────────────────────────────────────────────────────────

# ─── Doctor ViewSet ───────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="Shifokorlar ro'yxati",
        parameters=[
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY,
                             description='Faqat faol shifokorlar', required=False)
        ],
        tags=['Doctors'],
    ),
    retrieve=extend_schema(summary="Shifokor tafsilotlari", tags=['Doctors']),
    create=extend_schema(summary="Yangi shifokor qo'shish", tags=['Doctors']),
    update=extend_schema(summary="Shifokorni yangilash", tags=['Doctors']),
    partial_update=extend_schema(summary="Shifokorni qisman yangilash", tags=['Doctors']),
    destroy=extend_schema(summary="Shifokorni o'chirish", tags=['Doctors']),
)
class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.filter(is_active=True).prefetch_related('services')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['list']:
            return DoctorListSerializer
        return DoctorDetailSerializer

    def get_queryset(self):
        qs = Doctor.objects.prefetch_related('services')
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        return qs

    @extend_schema(
        summary="Bo'sh vaqt slotlari",
        description="Shifokorning ko'rsatilgan sanasidagi bo'sh vaqt slotlarini qaytaradi.",
        parameters=[
            OpenApiParameter(
                name='date', location=OpenApiParameter.QUERY,
                description='Sana (YYYY-MM-DD)', required=True, type=OpenApiTypes.DATE,
            )
        ],
        responses={200: SlotResponseSerializer},
        tags=['Doctors'],
    )
    @action(detail=True, methods=['get'], url_path='slots')
    def slots(self, request, pk=None):
        """Shifokor uchun bo'sh vaqt slotlari"""
        doctor = self.get_object()
        date_str = request.query_params.get('date')

        if not date_str:
            return Response(
                {'error': 'date parametri kerak (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Noto\'g\'ri sana formati. YYYY-MM-DD ishlating.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ish kunini tekshirish
        weekday = target_date.weekday()
        if doctor.work_days and weekday not in doctor.work_days:
            return Response({'slots': [], 'message': 'Shifokor bu kuni ishlamaydi.'})

        # Dam olish tekshiruvi
        if DoctorLeave.objects.filter(doctor=doctor, date=target_date).exists():
            return Response({'slots': [], 'message': 'Shifokor bu kuni dam oladi.'})

        slots = generate_slots(doctor, target_date)
        serializer = SlotSerializer(slots, many=True)
        return Response({'slots': serializer.data})

    @extend_schema(
        summary="Tatil kunlarini ko'rish/qo'shish",
        tags=['Doctors'],
    )
    @action(detail=True, methods=['get', 'post'], url_path='leaves')
    def leaves(self, request, pk=None):
        doctor = self.get_object()
        if request.method == 'GET':
            leaves = DoctorLeave.objects.filter(doctor=doctor)
            serializer = DoctorLeaveSerializer(leaves, many=True)
            return Response(serializer.data)
        else:
            data = request.data.copy()
            data['doctor'] = doctor.pk
            serializer = DoctorLeaveSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Tatil kunini o'chirish",
        parameters=[
            OpenApiParameter('leave_id', OpenApiTypes.INT, OpenApiParameter.PATH,
                             description="Tatil kuni ID-si"),
        ],
        tags=['Doctors'],
    )
    @action(detail=True, methods=['delete'], url_path='leaves/(?P<leave_id>[^/.]+)')
    def delete_leave(self, request, pk=None, leave_id=None):
        doctor = self.get_object()
        try:
            leave = DoctorLeave.objects.get(pk=leave_id, doctor=doctor)
            leave.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DoctorLeave.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=status.HTTP_404_NOT_FOUND)


# ─── Service Category ViewSet ─────────────────────────────────────────────────

# ─── Service Category ViewSet ─────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(summary="Kategoriyalar ro'yxati", tags=['Services']),
    retrieve=extend_schema(summary="Kategoriya tafsilotlari", tags=['Services']),
    create=extend_schema(summary="Kategoriya qo'shish", tags=['Services']),
    update=extend_schema(summary="Kategoriyani yangilash", tags=['Services']),
    partial_update=extend_schema(summary="Kategoriyani qisman yangilash", tags=['Services']),
    destroy=extend_schema(summary="Kategoriyani o'chirish", tags=['Services']),
)
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAuthenticated]


# ─── Service ViewSet ──────────────────────────────────────────────────────────

# ─── Service ViewSet ──────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="Xizmatlar ro'yxati",
        parameters=[
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('doctor_id', OpenApiTypes.INT,  OpenApiParameter.QUERY, required=False),
            OpenApiParameter('category',  OpenApiTypes.INT,  OpenApiParameter.QUERY, required=False),
        ],
        tags=['Services'],
    ),
    retrieve=extend_schema(summary="Xizmat tafsilotlari", tags=['Services']),
    create=extend_schema(summary="Yangi xizmat qo'shish", tags=['Services']),
    update=extend_schema(summary="Xizmatni yangilash", tags=['Services']),
    partial_update=extend_schema(summary="Xizmatni qisman yangilash", tags=['Services']),
    destroy=extend_schema(summary="Xizmatni o'chirish", tags=['Services']),
)
class ServiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ServiceDetailSerializer
        return ServiceListSerializer

    def get_queryset(self):
        qs = Service.objects.select_related('category').prefetch_related('doctors')
        is_active = self.request.query_params.get('is_active')
        doctor_id = self.request.query_params.get('doctor_id')
        category = self.request.query_params.get('category')

        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        if doctor_id:
            qs = qs.filter(doctors__id=doctor_id)
        if category:
            qs = qs.filter(category__id=category)
        return qs


# ─── Patient ViewSet ──────────────────────────────────────────────────────────

# ─── Patient ViewSet ──────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="Bemorlar ro'yxati",
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description='Ism, familiya yoki telefon', required=False),
        ],
        tags=['Patients'],
    ),
    retrieve=extend_schema(summary="Bemor tafsilotlari", tags=['Patients']),
    create=extend_schema(summary="Yangi bemor qo'shish", tags=['Patients']),
    update=extend_schema(summary="Bemorni yangilash", tags=['Patients']),
    partial_update=extend_schema(summary="Bemorni qisman yangilash", tags=['Patients']),
    destroy=extend_schema(summary="Bemorni o'chirish", tags=['Patients']),
)
class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Patient.objects.all()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search)
            )
        return qs

    @extend_schema(
        summary="Bemor qabullari tarixi",
        responses={200: AppointmentListSerializer(many=True)},
        tags=['Patients'],
    )
    @action(detail=True, methods=['get'])
    def appointments(self, request, pk=None):
        """Bemor qabullari tarixi"""
        patient = self.get_object()
        appointments = Appointment.objects.filter(
            patient=patient
        ).select_related('doctor', 'service').order_by('-date', '-start_time')
        serializer = AppointmentListSerializer(appointments, many=True)
        return Response(serializer.data)


# ─── Appointment ViewSet ──────────────────────────────────────────────────────

# ─── Appointment ViewSet ──────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="Qabullar ro'yxati",
        parameters=[
            OpenApiParameter('date',       OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('doctor_id',  OpenApiTypes.INT,  OpenApiParameter.QUERY, required=False),
            OpenApiParameter('patient_id', OpenApiTypes.INT,  OpenApiParameter.QUERY, required=False),
            OpenApiParameter('status',     OpenApiTypes.STR,  OpenApiParameter.QUERY, required=False,
                             enum=['pending','confirmed','in_progress','completed','cancelled','no_show']),
            OpenApiParameter('date_from',  OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
            OpenApiParameter('date_to',    OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False),
        ],
        tags=['Appointments'],
    ),
    retrieve=extend_schema(summary="Qabul tafsilotlari", tags=['Appointments']),
    create=extend_schema(summary="Yangi qabul yaratish", tags=['Appointments']),
    update=extend_schema(summary="Qabulni yangilash", tags=['Appointments']),
    partial_update=extend_schema(summary="Qabulni qisman yangilash", tags=['Appointments']),
    destroy=extend_schema(summary="Qabulni o'chirish", tags=['Appointments']),
)
class AppointmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return AppointmentCreateSerializer
        if self.action == 'retrieve':
            return AppointmentDetailSerializer
        return AppointmentListSerializer

    def get_queryset(self):
        qs = Appointment.objects.select_related(
            'patient', 'doctor', 'service'
        ).order_by('date', 'start_time')

        # Filterlar
        appt_date = self.request.query_params.get('date')
        doctor_id = self.request.query_params.get('doctor_id')
        patient_id = self.request.query_params.get('patient_id')
        appt_status = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')

        if appt_date:
            qs = qs.filter(date=appt_date)
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if appt_status:
            qs = qs.filter(status=appt_status)
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()
        output = AppointmentListSerializer(appointment)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Qabulni boshlash",
        description="Shifokor qabulni boshlaydi — status `in_progress` ga o'tadi.",
        request=None,
        responses={200: AppointmentListSerializer},
        tags=['Appointments'],
    )
    @action(detail=True, methods=['post'], url_path='start')
    def start_appointment(self, request, pk=None):
        """Qabulni boshlash (shifokor)"""
        appointment = self.get_object()
        if appointment.status not in ['pending', 'confirmed']:
            return Response(
                {'error': 'Faqat kutilayotgan yoki tasdiqlangan qabulni boshlash mumkin.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        appointment.status = 'in_progress'
        appointment.actual_start = timezone.now()
        appointment.save()
        return Response(AppointmentListSerializer(appointment).data)

    @extend_schema(
        summary="Qabulni tugatish",
        description="Qabulni tugatadi. Agar kechikish bo'lsa, keyingi bemorlarga avtomatik xabar yuboriladi.",
        request=None,
        responses={200: AppointmentListSerializer},
        tags=['Appointments'],
    )
    @action(detail=True, methods=['post'], url_path='complete')
    def complete_appointment(self, request, pk=None):
        """Qabulni tugatish — keyingi bemorlarga delay xabar yuborish"""
        appointment = self.get_object()
        if appointment.status != 'in_progress':
            return Response(
                {'error': 'Faqat jarayondagi qabulni tugatish mumkin.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        appointment.status = 'completed'
        appointment.actual_end = timezone.now()
        appointment.save()

        # Delay hisoblash va keyingi bemorlarga xabar yuborish
        delay = appointment.delay_minutes
        if delay > 0:
            _notify_upcoming_appointments_delay(appointment, delay)

        return Response({
            **AppointmentListSerializer(appointment).data,
            'delay_minutes': delay
        })

    @extend_schema(
        summary="Qabulni bekor qilish",
        request=CancelRequestSerializer,
        responses={200: AppointmentListSerializer},
        tags=['Appointments'],
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_appointment(self, request, pk=None):
        """Qabulni bekor qilish"""
        appointment = self.get_object()
        if appointment.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Bu qabulni bekor qilib bo\'lmaydi.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        reason = request.data.get('reason', '')
        appointment.status = 'cancelled'
        if reason:
            appointment.notes = f"{appointment.notes}\n[Bekor sababi]: {reason}".strip()
        appointment.save()
        return Response(AppointmentListSerializer(appointment).data)

    @extend_schema(
        summary="Qabulni tasdiqlash",
        request=None,
        responses={200: AppointmentListSerializer},
        tags=['Appointments'],
    )
    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm_appointment(self, request, pk=None):
        """Qabulni tasdiqlash"""
        appointment = self.get_object()
        if appointment.status != 'pending':
            return Response(
                {'error': 'Faqat kutilayotgan qabulni tasdiqlash mumkin.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        appointment.status = 'confirmed'
        appointment.save()
        return Response(AppointmentListSerializer(appointment).data)

    @extend_schema(
        summary="Bemor kelmadi deb belgilash",
        request=None,
        responses={200: AppointmentListSerializer},
        tags=['Appointments'],
    )
    @action(detail=True, methods=['post'], url_path='no-show')
    def no_show(self, request, pk=None):
        """Bemor kelmadi"""
        appointment = self.get_object()
        appointment.status = 'no_show'
        appointment.save()
        return Response(AppointmentListSerializer(appointment).data)


def _notify_upcoming_appointments_delay(completed_appointment: Appointment, delay_minutes: int):
    """
    Tugagan qabuldan so'ng bir xil kunda, shifokorning keyingi qabullariga
    delay xabari yuborish (bot orqali async).
    """
    from django.conf import settings

    upcoming = Appointment.objects.filter(
        doctor=completed_appointment.doctor,
        date=completed_appointment.date,
        start_time__gt=completed_appointment.start_time,
        status__in=['pending', 'confirmed']
    ).select_related('patient', 'service').order_by('start_time')

    cumulative_delay = delay_minutes
    for appt in upcoming:
        if appt.patient.telegram_id:
            # Yangi taxminiy vaqt
            new_time_dt = (
                datetime.combine(appt.date, appt.start_time) +
                timedelta(minutes=cumulative_delay)
            )
            new_time_str = new_time_dt.strftime('%H:%M')

            message = (
                f"⏳ <b>Diqqat!</b>\n\n"
                f"Avvalgi bemor qabuli {cumulative_delay} daqiqaga cho'zildi.\n"
                f"Sizning taxminiy vaqtingiz: <b>{new_time_str}</b>\n\n"
                f"Kutasizmi? Agar bekor qilmoqchi bo'lsangiz /cancel buyrug'ini bosing."
            )

            # Async xabar yuborish (fire-and-forget)
            try:
                import aiogram
                from aiogram import Bot
                bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

                async def send():
                    try:
                        await bot.send_message(
                            chat_id=appt.patient.telegram_id,
                            text=message,
                            parse_mode='HTML'
                        )
                    finally:
                        await bot.session.close()

                loop = asyncio.new_event_loop()
                loop.run_until_complete(send())
                loop.close()

                # Log saqlash
                ReminderLog.objects.create(
                    appointment=appt,
                    reminder_type='delay',
                    message=message,
                    is_success=True
                )
            except Exception as e:
                ReminderLog.objects.create(
                    appointment=appt,
                    reminder_type='delay',
                    message=message,
                    is_success=False
                )

        # Har keyingi bemor uchun ham delay to'planadi
        duration = appt.service.duration if appt.service else appt.doctor.slot_duration
        # cumulative_delay shu qoladi (oddiy holat)


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Dashboard statistikasi",
        description="Bugungi, haftalik va oylik qabullar soni, daromad, so'nggi qabullar.",
        responses={200: DashboardStatsSerializer},
        tags=['Stats'],
    )
    def get(self, request):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Bugungi
        today_qs = Appointment.objects.filter(date=today)
        today_appointments = today_qs.count()
        today_completed = today_qs.filter(status='completed').count()
        today_cancelled = today_qs.filter(status='cancelled').count()
        today_revenue = today_qs.filter(status='completed').aggregate(
            total=Sum('price')
        )['total'] or Decimal('0')

        # Haftalik
        week_qs = Appointment.objects.filter(date__gte=week_start, date__lte=today)
        week_appointments = week_qs.count()
        week_revenue = week_qs.filter(status='completed').aggregate(
            total=Sum('price')
        )['total'] or Decimal('0')

        # Oylik
        month_qs = Appointment.objects.filter(date__gte=month_start, date__lte=today)
        month_appointments = month_qs.count()
        month_revenue = month_qs.filter(status='completed').aggregate(
            total=Sum('price')
        )['total'] or Decimal('0')

        # Umumiy
        total_patients = Patient.objects.count()
        active_doctors = Doctor.objects.filter(is_active=True).count()

        # So'nggi qabullar
        recent_appointments = Appointment.objects.select_related(
            'patient', 'doctor', 'service'
        ).order_by('-created_at')[:10]

        data = {
            'today_appointments': today_appointments,
            'today_completed': today_completed,
            'today_cancelled': today_cancelled,
            'today_revenue': today_revenue,
            'week_appointments': week_appointments,
            'week_revenue': week_revenue,
            'month_appointments': month_appointments,
            'month_revenue': month_revenue,
            'total_patients': total_patients,
            'active_doctors': active_doctors,
            'recent_appointments': recent_appointments,
        }

        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)


# ─── Revenue Stats ────────────────────────────────────────────────────────────

class RevenueStatsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Daromad statistikasi",
        description="Kunlik daromad, top shifokorlar va top xizmatlar.",
        parameters=[
            OpenApiParameter(
                name='period', location=OpenApiParameter.QUERY,
                description='Davr: week | month | year',
                required=False, type=OpenApiTypes.STR,
                enum=['week', 'month', 'year'],
            )
        ],
        responses={200: RevenueStatsSerializer},
        tags=['Stats'],
    )
    def get(self, request):
        period = request.query_params.get('period', 'week')  # week | month | year
        today = timezone.localdate()

        if period == 'week':
            days = 7
        elif period == 'month':
            days = 30
        else:
            days = 365

        start_date = today - timedelta(days=days - 1)

        # Kunlik daromad
        daily_data = []
        current = start_date
        while current <= today:
            revenue = Appointment.objects.filter(
                date=current, status='completed'
            ).aggregate(total=Sum('price'))['total'] or 0

            count = Appointment.objects.filter(date=current).count()

            daily_data.append({
                'date': current.strftime('%Y-%m-%d'),
                'revenue': float(revenue),
                'appointments': count,
            })
            current += timedelta(days=1)

        # Top shifokorlar
        top_doctors = Appointment.objects.filter(
            date__gte=start_date, status='completed'
        ).values(
            'doctor__id', 'doctor__first_name', 'doctor__last_name'
        ).annotate(
            revenue=Sum('price'), count=Count('id')
        ).order_by('-revenue')[:5]

        # Top xizmatlar
        top_services = Appointment.objects.filter(
            date__gte=start_date, status='completed'
        ).values(
            'service__id', 'service__name'
        ).annotate(
            revenue=Sum('price'), count=Count('id')
        ).order_by('-count')[:5]

        return Response({
            'period': period,
            'daily': daily_data,
            'top_doctors': list(top_doctors),
            'top_services': list(top_services),
        })


# ─── Clinic Settings ─────────────────────────────────────────────────────────

class ClinicSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Klinika sozlamalarini ko'rish",
        responses={200: ClinicSettingsSerializer},
        tags=['Settings'],
    )
    def get(self, request):
        settings_obj = ClinicSettings.get_settings()
        serializer = ClinicSettingsSerializer(settings_obj)
        return Response(serializer.data)

    @extend_schema(
        summary="Klinika sozlamalarini yangilash",
        request=ClinicSettingsSerializer,
        responses={200: ClinicSettingsSerializer},
        tags=['Settings'],
    )
    def put(self, request):
        settings_obj = ClinicSettings.get_settings()
        serializer = ClinicSettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Klinika sozlamalarini qisman yangilash",
        request=ClinicSettingsSerializer,
        responses={200: ClinicSettingsSerializer},
        tags=['Settings'],
    )
    def patch(self, request):
        return self.put(request)


# ─── Telegram Webhook ────────────────────────────────────────────────────────

@extend_schema(exclude=True)
@api_view(['POST'])
@permission_classes([AllowAny])
def telegram_webhook(request):
    """Telegram webhook endpoint"""
    try:
        from bot.main import dp, bot
        import asyncio

        update_data = request.data

        async def process():
            from aiogram.types import Update
            update = Update.model_validate(update_data)
            await dp.feed_update(bot, update)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(process())
        loop.close()

        return Response({'ok': True})
    except Exception as e:
        return Response({'ok': False, 'error': str(e)}, status=500)
