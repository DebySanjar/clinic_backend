"""
DentFlow Bot — Keyboard builder (aiogram 3.x)
"""

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
)


def main_menu_keyboard(webapp_url: str) -> ReplyKeyboardMarkup:
    """Asosiy menyu — Web App tugmasi bilan"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🦷 Qabulga yozilish",
                    web_app=WebAppInfo(url=f"{webapp_url}/book")
                )
            ],
            [
                KeyboardButton(
                    text="📋 Mening qabullarim",
                    web_app=WebAppInfo(url=f"{webapp_url}/my-appointments")
                )
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def confirm_phone_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqamini yuborish"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def delay_notification_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    """Kechikish xabari uchun inline keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Kutaman",
                    callback_data=f"delay_wait:{appointment_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Bekor qilaman",
                    callback_data=f"delay_cancel:{appointment_id}"
                ),
            ]
        ]
    )


def reminder_keyboard(appointment_id: int, webapp_url: str) -> InlineKeyboardMarkup:
    """Eslatma xabari uchun inline keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Qabulni ko'rish",
                    web_app=WebAppInfo(url=f"{webapp_url}/my-appointments")
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data=f"cancel_appt:{appointment_id}"
                )
            ]
        ]
    )
