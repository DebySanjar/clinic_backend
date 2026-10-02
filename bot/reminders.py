"""
DentFlow Bot — Reminder & Delay Notification Service
APScheduler bilan ishlaydi — har daqiqa tekshiradi.
"""

import os
import asyncio
import logging
from datetime import timedelta

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.utils import timezone
from django.conf import settings
from asgiref.sync import sync_to_async

from aiogram import Bot

from clinic.models import Appointment, ReminderLog, ClinicSettings

logger = logging.getLogger(__name__)


async def send_reminder(bot: Bot, appointment_id: int, reminder_type: str):
    """Bir qabul uchun eslatma yuborish"""
    from clinic.models import Appointment, ReminderLog, ClinicSettings

    @sync_to_async
    def get_data():
        try:
            appt = Appointment.objects.select_related(
                'patient', 'doctor', 'service'
            ).get(pk=appointment_id)
            s = ClinicSettings.get_settings()
            return appt, s
        except Appointment.DoesNotExist:
            return None, None

    appt, clinic_settings = await get_data()
    if not appt or not appt.patient.telegram_id:
        return

    # Shablonni to'ldirish
    context = {
        'date': appt.date.strftime('%d.%m.%Y'),
        'time': appt.start_time.strftime('%H:%M'),
        'doctor': f"Dr. {appt.doctor.full_name}",
        'service': appt.service.name if appt.service else '',
        'clinic_name': clinic_settings.name,
        'address': clinic_settings.address,
        'phone': clinic_settings.phone,
    }

    if reminder_type == '24h':
        template = clinic_settings.reminder_24h_template
    else:
        template = clinic_settings.reminder_1h_template

    try:
        message_text = template.format(**context)
    except KeyError:
        message_text = (
            f"⏰ Eslatma!\n\n"
            f"📅 {context['date']} soat {context['time']}\n"
            f"👨‍⚕️ {context['doctor']}\n"
            f"🦷 {context['service']}\n\n"
            f"📍 {context['clinic_name']}, {context['address']}"
        )

    from bot.keyboards import reminder_keyboard
    webapp_url = getattr(settings, 'WEBAPP_URL', 'https://your-webapp.vercel.app')

    success = False
    try:
        await bot.send_message(
            chat_id=appt.patient.telegram_id,
            text=message_text,
            parse_mode='HTML',
            reply_markup=reminder_keyboard(appt.pk, webapp_url)
        )
        success = True
    except Exception as e:
        logger.error(f"Reminder yuborishda xato (appt={appointment_id}): {e}")

    @sync_to_async
    def save_log():
        ReminderLog.objects.create(
            appointment=appt,
            reminder_type=reminder_type,
            message=message_text,
            is_success=success
        )
        if reminder_type == '24h':
            appt.reminder_24h_sent = True
        else:
            appt.reminder_1h_sent = True
        appt.save(update_fields=[
            'reminder_24h_sent' if reminder_type == '24h' else 'reminder_1h_sent'
        ])

    await save_log()


async def send_delay_notification(
    bot: Bot,
    appointment_id: int,
    delay_minutes: int,
    new_time_str: str
):
    """Kechikish xabari yuborish"""

    @sync_to_async
    def get_appt():
        try:
            return Appointment.objects.select_related(
                'patient', 'doctor'
            ).get(pk=appointment_id)
        except Appointment.DoesNotExist:
            return None

    appt = await get_appt()
    if not appt or not appt.patient.telegram_id:
        return

    message_text = (
        f"⏳ <b>Diqqat!</b>\n\n"
        f"Avvalgi bemor qabuli <b>{delay_minutes} daqiqaga</b> cho'zildi.\n\n"
        f"👨‍⚕️ {appt.doctor.full_name}\n"
        f"📅 {appt.date.strftime('%d.%m.%Y')}\n"
        f"⏰ Yangi taxminiy vaqt: <b>{new_time_str}</b>\n\n"
        f"Kutasizmi?"
    )

    from bot.keyboards import delay_notification_keyboard

    success = False
    try:
        await bot.send_message(
            chat_id=appt.patient.telegram_id,
            text=message_text,
            parse_mode='HTML',
            reply_markup=delay_notification_keyboard(appt.pk)
        )
        success = True
    except Exception as e:
        logger.error(f"Delay notification xatosi (appt={appointment_id}): {e}")

    @sync_to_async
    def save_log():
        ReminderLog.objects.create(
            appointment=appt,
            reminder_type='delay',
            message=message_text,
            is_success=success
        )

    await save_log()


# ─── Scheduler Jobs ──────────────────────────────────────────────────────────

async def check_reminders(bot: Bot):
    """
    Har daqiqa ishga tushadi:
    - 24h oldin eslatma yuborish
    - 1h oldin eslatma yuborish
    """
    now = timezone.now()

    @sync_to_async
    def get_24h_appointments():
        target_start = now + timedelta(hours=24)
        target_end = now + timedelta(hours=24, minutes=5)
        from datetime import datetime
        from django.utils.timezone import make_aware

        appointments = []
        from clinic.models import Appointment
        for appt in Appointment.objects.filter(
            status__in=['pending', 'confirmed'],
            reminder_24h_sent=False
        ).select_related('patient'):
            appt_dt = make_aware(
                datetime.combine(appt.date, appt.start_time)
            ) if timezone.is_naive(
                datetime.combine(appt.date, appt.start_time)
            ) else datetime.combine(appt.date, appt.start_time)

            if not timezone.is_aware(appt_dt):
                appt_dt = timezone.make_aware(appt_dt)

            if target_start <= appt_dt < target_end:
                if appt.patient.telegram_id:
                    appointments.append(appt.id)
        return appointments

    @sync_to_async
    def get_1h_appointments():
        target_start = now + timedelta(hours=1)
        target_end = now + timedelta(hours=1, minutes=5)
        from datetime import datetime

        appointments = []
        from clinic.models import Appointment
        for appt in Appointment.objects.filter(
            status__in=['pending', 'confirmed'],
            reminder_1h_sent=False
        ).select_related('patient'):
            appt_dt = datetime.combine(appt.date, appt.start_time)
            if not timezone.is_aware(appt_dt):
                appt_dt = timezone.make_aware(appt_dt)

            if target_start <= appt_dt < target_end:
                if appt.patient.telegram_id:
                    appointments.append(appt.id)
        return appointments

    # 24h eslatmalar
    appt_ids_24h = await get_24h_appointments()
    for appt_id in appt_ids_24h:
        await send_reminder(bot, appt_id, '24h')
        logger.info(f"24h reminder yuborildi: appt_id={appt_id}")

    # 1h eslatmalar
    appt_ids_1h = await get_1h_appointments()
    for appt_id in appt_ids_1h:
        await send_reminder(bot, appt_id, '1h')
        logger.info(f"1h reminder yuborildi: appt_id={appt_id}")


def setup_scheduler(bot: Bot):
    """APScheduler ni sozlash va ishga tushirish"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = AsyncIOScheduler(timezone=str(settings.TIME_ZONE))

    # Har 5 daqiqada reminder tekshirish
    scheduler.add_job(
        check_reminders,
        trigger=IntervalTrigger(minutes=5),
        kwargs={'bot': bot},
        id='check_reminders',
        replace_existing=True,
        misfire_grace_time=60,
    )

    scheduler.start()
    logger.info("APScheduler ishga tushirildi ✅")
    return scheduler
