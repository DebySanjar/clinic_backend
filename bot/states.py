"""
DentFlow Bot — FSM States (aiogram 3.x)
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Qabul yozilish holatlari"""
    choosing_doctor = State()
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()


class RescheduleStates(StatesGroup):
    """Qabulni ko'chirish holatlari"""
    choosing_appointment = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()


class CancelStates(StatesGroup):
    """Qabulni bekor qilish holatlari"""
    choosing_appointment = State()
    confirming = State()


class DoctorStates(StatesGroup):
    """Shifokor panel holatlari"""
    main_menu = State()
    managing_schedule = State()
    viewing_appointments = State()
