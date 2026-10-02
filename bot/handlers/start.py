"""
DentFlow Bot — /start va asosiy handlerlar
"""

import os
import django

# Django setup (bot standalone ishlaganda)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Contact
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from django.conf import settings
from clinic.models import Patient, Appointment
from ..keyboards import (
    main_menu_keyboard, confirm_phone_keyboard,
    delay_notification_keyboard
)

router = Router()

WEBAPP_URL = getattr(settings, 'WEBAPP_URL', 'https://your-webapp.vercel.app')


# ─── /start ──────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    telegram_id = message.from_user.id

    # Bemorni topish yoki yaratish
    patient = await _get_or_none_patient(telegram_id)

    if patient is None:
        # Yangi foydalanuvchi — telefon so'rash
        await message.answer(
            "👋 <b>DentFlow</b> ga xush kelibsiz!\n\n"
            "Stomatologiya klinikamizda qabulga yozilish uchun "
            "telefon raqamingizni yuboring.",
            parse_mode='HTML',
            reply_markup=confirm_phone_keyboard()
        )
    else:
        await message.answer(
            f"👋 Xush kelibsiz, <b>{patient.first_name}</b>!\n\n"
            "Quyidagi tugmalardan foydalaning:",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard(WEBAPP_URL)
        )


@router.message(F.contact)
async def handle_contact(message: Message):
    """Telefon raqamini qabul qilish"""
    contact: Contact = message.contact
    telegram_id = message.from_user.id

    # Faqat o'z raqamini qabul qilish
    if contact.user_id != telegram_id:
        await message.answer("❗ Faqat o'z telefon raqamingizni yuboring.")
        return

    phone = contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone

    first_name = message.from_user.first_name or 'Bemor'
    last_name = message.from_user.last_name or ''

    # Bemorni yaratish yoki yangilash
    from asgiref.sync import sync_to_async

    @sync_to_async
    def save_patient():
        patient, created = Patient.objects.get_or_create(
            telegram_id=telegram_id,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
            }
        )
        if not created:
            patient.phone = phone
            patient.save()
        return patient, created

    patient, created = await save_patient()

    await message.answer(
        f"✅ Ro'yxatdan o'tdingiz!\n\n"
        f"Ism: <b>{patient.first_name}</b>\n"
        f"Tel: <b>{patient.phone}</b>\n\n"
        "Endi qabulga yozilishingiz mumkin 👇",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(WEBAPP_URL)
    )


# ─── /help ───────────────────────────────────────────────────────────────────

@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>DentFlow Bot — Yordam</b>\n\n"
        "🦷 <b>Qabulga yozilish</b> — Shifokorni tanlang, "
        "xizmat va qulay vaqtni belgilang\n\n"
        "📋 <b>Mening qabullarim</b> — Barcha qabullaringizni ko'ring, "
        "bekor qiling yoki ko'chiring\n\n"
        "⏰ Bot sizga qabul vaqtidan 24 soat va 1 soat oldin "
        "eslatma yuboradi.\n\n"
        "📞 Muammo bo'lsa: " + getattr(settings, 'CLINIC_PHONE', '+998 71 000 00 00'),
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(WEBAPP_URL)
    )


# ─── Delay callback (kechikish xabari) ───────────────────────────────────────

@router.callback_query(F.data.startswith('delay_wait:'))
async def delay_wait(callback: CallbackQuery):
    """Bemor kutishga rozi"""
    await callback.answer("✅ Tushunarli, sizni xabardor qilamiz!")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "✅ Rahmat! Qabul vaqti yaqinlashganda eslatib qo'yamiz."
    )


@router.callback_query(F.data.startswith('delay_cancel:'))
async def delay_cancel(callback: CallbackQuery):
    """Bemor kechikish sababli bekor qilmoqchi"""
    appt_id = int(callback.data.split(':')[1])

    from asgiref.sync import sync_to_async

    @sync_to_async
    def cancel_appt():
        try:
            appt = Appointment.objects.get(pk=appt_id)
            if appt.status in ['pending', 'confirmed']:
                appt.status = 'cancelled'
                appt.notes += '\n[Bekor sababi]: Kechikish sababli bemor tomonidan bekor qilindi'
                appt.save()
                return True
            return False
        except Appointment.DoesNotExist:
            return False

    cancelled = await cancel_appt()

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    if cancelled:
        await callback.message.answer(
            "✅ Qabulingiz bekor qilindi.\n\n"
            "Yangi qabul yaratish uchun quyidagi tugmani bosing:",
            reply_markup=main_menu_keyboard(WEBAPP_URL)
        )
    else:
        await callback.message.answer("❌ Qabulni bekor qilib bo'lmadi yoki allaqachon bekor qilingan.")


@router.callback_query(F.data.startswith('cancel_appt:'))
async def cancel_appointment_callback(callback: CallbackQuery):
    """Eslatma xabaridan bekor qilish"""
    appt_id = int(callback.data.split(':')[1])

    from asgiref.sync import sync_to_async

    @sync_to_async
    def cancel_appt():
        try:
            appt = Appointment.objects.select_related('doctor', 'service').get(pk=appt_id)
            if appt.status in ['pending', 'confirmed']:
                appt.status = 'cancelled'
                appt.notes += '\n[Bekor sababi]: Bemor tomonidan bekor qilindi (eslatmadan)'
                appt.save()
                return appt
            return None
        except Appointment.DoesNotExist:
            return None

    appt = await cancel_appt()

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    if appt:
        await callback.message.answer(
            f"✅ <b>{appt.date} soat {appt.start_time.strftime('%H:%M')}</b> dagi "
            f"Dr. {appt.doctor.last_name} qabuli bekor qilindi.\n\n"
            "Yangi qabul yaratish uchun 👇",
            parse_mode='HTML',
            reply_markup=main_menu_keyboard(WEBAPP_URL)
        )
    else:
        await callback.message.answer("❌ Qabulni bekor qilib bo'lmadi.")


# ─── Helper ───────────────────────────────────────────────────────────────────

async def _get_or_none_patient(telegram_id: int):
    from asgiref.sync import sync_to_async

    @sync_to_async
    def get():
        try:
            return Patient.objects.get(telegram_id=telegram_id)
        except Patient.DoesNotExist:
            return None

    return await get()
