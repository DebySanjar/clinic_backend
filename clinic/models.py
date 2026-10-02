"""
DentFlow — Clinic Models
"""

from django.db import models
from django.utils import timezone


class Doctor(models.Model):
    """Shifokor"""

    WEEKDAYS = [
        (0, 'Dushanba'),
        (1, 'Seshanba'),
        (2, 'Chorshanba'),
        (3, 'Payshanba'),
        (4, 'Juma'),
        (5, 'Shanba'),
        (6, 'Yakshanba'),
    ]

    first_name = models.CharField('Ism', max_length=100)
    last_name = models.CharField('Familiya', max_length=100)
    speciality = models.CharField('Mutaxassislik', max_length=200, default='Stomatolog')
    phone = models.CharField('Telefon', max_length=20, blank=True)
    telegram_id = models.BigIntegerField('Telegram ID', unique=True, null=True, blank=True)
    photo = models.ImageField('Rasm', upload_to='doctors/', null=True, blank=True)

    # Ish vaqti
    slot_duration = models.PositiveIntegerField('Qabul davomiyligi (daqiqa)', default=30)
    work_start = models.TimeField('Ish boshlanishi', default='09:00')
    work_end = models.TimeField('Ish tugashi', default='18:00')
    break_start = models.TimeField('Tanaffus boshlanishi', null=True, blank=True)
    break_end = models.TimeField('Tanaffus tugashi', null=True, blank=True)

    # Ish kunlari (JSON: [0,1,2,3,4] = Du-Ju)
    work_days = models.JSONField('Ish kunlari', default=list)

    is_active = models.BooleanField('Faol', default=True)
    created_at = models.DateTimeField('Yaratilgan', auto_now_add=True)
    updated_at = models.DateTimeField('Yangilangan', auto_now=True)

    class Meta:
        verbose_name = 'Shifokor'
        verbose_name_plural = 'Shifokorlar'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class DoctorLeave(models.Model):
    """Shifokor dam olish / ta'til kunlari"""

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='leaves')
    date = models.DateField('Sana')
    reason = models.CharField('Sabab', max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dam olish kuni"
        verbose_name_plural = "Dam olish kunlari"
        unique_together = ['doctor', 'date']

    def __str__(self):
        return f"{self.doctor} — {self.date}"


class ServiceCategory(models.Model):
    """Xizmat kategoriyasi"""

    name = models.CharField('Nomi', max_length=100)
    icon = models.CharField('Ikonka (emoji)', max_length=10, default='🦷')
    order = models.PositiveIntegerField('Tartib', default=0)

    class Meta:
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Service(models.Model):
    """Stomatologiya xizmati"""

    category = models.ForeignKey(
        ServiceCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='services'
    )
    name = models.CharField("Nomi (UZ)", max_length=200)
    name_ru = models.CharField("Nomi (RU)", max_length=200, blank=True)
    description = models.TextField("Tavsif", blank=True)
    price = models.DecimalField("Narxi (so'm)", max_digits=12, decimal_places=0)
    duration = models.PositiveIntegerField("Davomiyligi (daqiqa)", default=30)
    doctors = models.ManyToManyField(Doctor, related_name='services', blank=True)
    is_active = models.BooleanField('Faol', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Xizmat'
        verbose_name_plural = 'Xizmatlar'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def price_formatted(self):
        return f"{int(self.price):,} so'm".replace(',', ' ')


class Patient(models.Model):
    """Bemor"""

    telegram_id = models.BigIntegerField('Telegram ID', unique=True, null=True, blank=True)
    first_name = models.CharField('Ism', max_length=100)
    last_name = models.CharField('Familiya', max_length=100, blank=True)
    phone = models.CharField('Telefon', max_length=20, blank=True)
    notes = models.TextField('Eslatmalar', blank=True)
    created_at = models.DateTimeField('Ro\'ylxatga olingan', auto_now_add=True)

    class Meta:
        verbose_name = 'Bemor'
        verbose_name_plural = 'Bemorlar'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def visit_count(self):
        return self.appointments.filter(
            status__in=['completed', 'in_progress']
        ).count()


class Appointment(models.Model):
    """Qabul"""

    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('confirmed', 'Tasdiqlangan'),
        ('in_progress', 'Jarayonda'),
        ('completed', 'Tugagan'),
        ('cancelled', 'Bekor qilingan'),
        ('rescheduled', 'Ko\'chirilgan'),
        ('no_show', 'Kelmadi'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, related_name='appointments')

    date = models.DateField('Sana')
    start_time = models.TimeField('Boshlanish vaqti')
    end_time = models.TimeField('Tugash vaqti')

    # Real vaqtlar (shifokor tomonidan belgilanadi)
    actual_start = models.DateTimeField('Haqiqiy boshlanish', null=True, blank=True)
    actual_end = models.DateTimeField('Haqiqiy tugash', null=True, blank=True)

    status = models.CharField('Holat', max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField('Izoh', blank=True)
    price = models.DecimalField('Narx', max_digits=12, decimal_places=0, null=True, blank=True)

    # Reminder tracking
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Qabul'
        verbose_name_plural = 'Qabullar'
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.patient} → Dr. {self.doctor.last_name} | {self.date} {self.start_time}"

    @property
    def delay_minutes(self):
        """Qabul necha daqiqa kechikdi"""
        if self.actual_end and self.actual_start:
            actual_duration = int((self.actual_end - self.actual_start).total_seconds() / 60)
            expected_duration = self.service.duration if self.service else self.doctor.slot_duration
            return max(0, actual_duration - expected_duration)
        return 0

    def save(self, *args, **kwargs):
        # Narxni xizmatdan avtomatik olish
        if not self.price and self.service:
            self.price = self.service.price
        super().save(*args, **kwargs)


class ReminderLog(models.Model):
    """Yuborilgan eslatmalar logi"""

    TYPES = [
        ('24h', '24 soat oldin'),
        ('1h', '1 soat oldin'),
        ('delay', 'Kechikish xabari'),
        ('cancelled', 'Bekor qilish xabari'),
    ]

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField('Tur', max_length=20, choices=TYPES)
    message = models.TextField('Xabar matni')
    sent_at = models.DateTimeField('Yuborilgan vaqt', default=timezone.now)
    is_success = models.BooleanField('Muvaffaqiyatli', default=True)

    class Meta:
        verbose_name = 'Eslatma'
        verbose_name_plural = 'Eslatmalar'

    def __str__(self):
        return f"{self.appointment} — {self.reminder_type}"


class ClinicSettings(models.Model):
    """Klinika sozlamalari (singleton)"""

    name = models.CharField('Klinika nomi', max_length=200, default='DentFlow Klinikasi')
    address = models.CharField('Manzil', max_length=500, blank=True)
    phone = models.CharField('Telefon', max_length=50, blank=True)
    telegram_bot_token = models.CharField('Telegram Bot Token', max_length=200, blank=True)
    work_start = models.TimeField('Ish vaqti boshlanishi', default='09:00')
    work_end = models.TimeField('Ish vaqti tugashi', default='18:00')
    reminder_24h = models.BooleanField('24 soat eslatma', default=True)
    reminder_1h = models.BooleanField('1 soat eslatma', default=True)
    reminder_24h_template = models.TextField(
        'Shablон (24h)',
        default='🦷 Eslatma!\n\nErtaga {date} soat {time} da {doctor} dr. qabuli bor.\n\nKlinika: {clinic_name}\nManzil: {address}'
    )
    reminder_1h_template = models.TextField(
        'Shablon (1h)',
        default='⏰ 1 soatdan so\'ng {time} da {doctor} dr. qabuli bor.\n\nKlinika: {clinic_name}\nManzil: {address}'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Klinika sozlamalari'
        verbose_name_plural = 'Klinika sozlamalari'

    def __str__(self):
        return self.name

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
