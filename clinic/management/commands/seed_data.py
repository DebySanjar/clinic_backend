"""
DentFlow — Demo ma'lumotlar yaratish buyrug'i
Ishlatish: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, timedelta
from clinic.models import (
    Doctor, ServiceCategory, Service, Patient,
    Appointment, ClinicSettings
)


class Command(BaseCommand):
    help = 'Demo ma\'lumotlar yaratish'

    def handle(self, *args, **kwargs):
        self.stdout.write('Demo ma\'lumotlar yaratilmoqda...')

        # ── Klinika sozlamalari ────────────────────────────────────
        settings = ClinicSettings.get_settings()
        settings.name = 'DentFlow Klinikasi'
        settings.address = 'Toshkent sh., Chilonzor tumani, 15-uy'
        settings.phone = '+998 71 234 56 78'
        settings.save()

        # ── Kategoriyalar ─────────────────────────────────────────
        cats = {
            'Davolash': ServiceCategory.objects.get_or_create(
                name='Davolash', defaults={'icon': '🦷', 'order': 1}
            )[0],
            'Estetika': ServiceCategory.objects.get_or_create(
                name='Estetika', defaults={'icon': '✨', 'order': 2}
            )[0],
            'Jarrohlik': ServiceCategory.objects.get_or_create(
                name='Jarrohlik', defaults={'icon': '🔧', 'order': 3}
            )[0],
            'Bolalar': ServiceCategory.objects.get_or_create(
                name='Bolalar stomatologiyasi', defaults={'icon': '👶', 'order': 4}
            )[0],
        }

        # ── Xizmatlar ─────────────────────────────────────────────
        services_data = [
            ('Plomba (bir tish)', 'Пломба (один зуб)', 150_000, 45, 'Davolash'),
            ('Tish olish', 'Удаление зуба', 100_000, 30, 'Jarrohlik'),
            ('Tish oqartirish', 'Отбеливание зубов', 800_000, 60, 'Estetika'),
            ('Tish toshini tozalash', 'Снятие зубного камня', 200_000, 45, 'Davolash'),
            ('Kronka o\'rnatish', 'Установка коронки', 1_500_000, 60, 'Estetika'),
            ('Bolalar tish davolash', 'Лечение детских зубов', 120_000, 30, 'Bolalar'),
            ('Implant', 'Имплант', 3_000_000, 90, 'Jarrohlik'),
            ('Tishlarni tuzatish (breketlar)', 'Брекеты', 500_000, 60, 'Estetika'),
        ]

        services = {}
        for name, name_ru, price, duration, cat_name in services_data:
            svc, _ = Service.objects.get_or_create(
                name=name,
                defaults={
                    'name_ru': name_ru,
                    'price': price,
                    'duration': duration,
                    'category': cats[cat_name],
                }
            )
            services[name] = svc

        # ── Shifokorlar ───────────────────────────────────────────
        doctors_data = [
            {
                'first_name': 'Alisher', 'last_name': 'Karimov',
                'speciality': 'Terapevt stomatolog',
                'phone': '+998 90 111 22 33',
                'work_days': [0, 1, 2, 3, 4],
                'slot_duration': 30,
                'work_start': time(9, 0), 'work_end': time(18, 0),
                'break_start': time(13, 0), 'break_end': time(14, 0),
                'services': ['Plomba (bir tish)', 'Tish toshini tozalash', 'Bolalar tish davolash'],
            },
            {
                'first_name': 'Malika', 'last_name': 'Yusupova',
                'speciality': 'Estetik stomatolog',
                'phone': '+998 90 222 33 44',
                'work_days': [0, 1, 2, 3, 4, 5],
                'slot_duration': 45,
                'work_start': time(10, 0), 'work_end': time(19, 0),
                'break_start': time(14, 0), 'break_end': time(15, 0),
                'services': ['Tish oqartirish', 'Kronka o\'rnatish', 'Tishlarni tuzatish (breketlar)'],
            },
            {
                'first_name': 'Bobur', 'last_name': 'Toshmatov',
                'speciality': 'Xirurg stomatolog',
                'phone': '+998 90 333 44 55',
                'work_days': [1, 2, 3, 4, 5],
                'slot_duration': 60,
                'work_start': time(9, 0), 'work_end': time(17, 0),
                'break_start': time(12, 0), 'break_end': time(13, 0),
                'services': ['Tish olish', 'Implant'],
            },
        ]

        doctors = []
        for d in doctors_data:
            svc_names = d.pop('services')
            doc, _ = Doctor.objects.get_or_create(
                first_name=d['first_name'], last_name=d['last_name'],
                defaults=d
            )
            for svc_name in svc_names:
                if svc_name in services:
                    doc.services.add(services[svc_name])
            doctors.append(doc)

        # ── Bemorlar ─────────────────────────────────────────────
        patients_data = [
            ('Jasur', 'Normatov', '+998 90 444 55 66'),
            ('Zulfiya', 'Hasanova', '+998 90 555 66 77'),
            ('Otabek', 'Mirzayev', '+998 90 666 77 88'),
            ('Nilufar', 'Qosimova', '+998 90 777 88 99'),
            ('Sardor', 'Ergashev', '+998 90 888 99 00'),
        ]

        patients = []
        for fn, ln, ph in patients_data:
            p, _ = Patient.objects.get_or_create(
                phone=ph,
                defaults={'first_name': fn, 'last_name': ln}
            )
            patients.append(p)

        # ── Qabullar ─────────────────────────────────────────────
        today = timezone.localdate()
        appts_data = [
            # Bugungi qabullar
            (patients[0], doctors[0], services['Plomba (bir tish)'], today, time(9, 0), 'confirmed'),
            (patients[1], doctors[0], services['Tish toshini tozalash'], today, time(10, 0), 'confirmed'),
            (patients[2], doctors[1], services['Tish oqartirish'], today, time(10, 0), 'pending'),
            (patients[3], doctors[2], services['Tish olish'], today, time(11, 0), 'completed'),
            (patients[4], doctors[0], services['Plomba (bir tish)'], today, time(14, 0), 'pending'),
            # Ertangi qabullar
            (patients[0], doctors[1], services['Kronka o\'rnatish'], today + timedelta(1), time(10, 0), 'pending'),
            (patients[2], doctors[2], services['Implant'], today + timedelta(1), time(11, 0), 'pending'),
            # Kechagi (tarix)
            (patients[1], doctors[0], services['Plomba (bir tish)'], today - timedelta(1), time(9, 0), 'completed'),
            (patients[3], doctors[1], services['Tish oqartirish'], today - timedelta(1), time(11, 0), 'completed'),
            (patients[4], doctors[2], services['Tish olish'], today - timedelta(2), time(9, 0), 'cancelled'),
        ]

        for patient, doctor, service, appt_date, start_t, appt_status in appts_data:
            from datetime import datetime
            end_t = (
                datetime.combine(appt_date, start_t) +
                timedelta(minutes=service.duration)
            ).time()

            Appointment.objects.get_or_create(
                patient=patient, doctor=doctor, service=service,
                date=appt_date, start_time=start_t,
                defaults={
                    'end_time': end_t,
                    'status': appt_status,
                    'price': service.price,
                }
            )

        self.stdout.write(self.style.SUCCESS(
            '✅ Demo ma\'lumotlar muvaffaqiyatli yaratildi!\n'
            f'   Shifokorlar: {Doctor.objects.count()}\n'
            f'   Xizmatlar: {Service.objects.count()}\n'
            f'   Bemorlar: {Patient.objects.count()}\n'
            f'   Qabullar: {Appointment.objects.count()}'
        ))
