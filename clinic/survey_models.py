"""
DentFlow — Survey Models
"""
import uuid
from django.db import models
from django.utils import timezone


class Survey(models.Model):
    """So'rovnoma"""

    STATUS_CHOICES = [
        ('draft',    'Qoralama'),
        ('active',   'Faol'),
        ('closed',   'Yopilgan'),
    ]

    title       = models.CharField('Sarlavha', max_length=255)
    description = models.TextField('Tavsif', blank=True)
    status      = models.CharField('Holat', max_length=10, choices=STATUS_CHOICES, default='draft')
    slug        = models.UUIDField('Link ID', default=uuid.uuid4, unique=True, editable=False)
    is_anonymous = models.BooleanField('Anonim', default=True)
    allow_multiple = models.BooleanField('Bir necha marta to\'ldirish', default=False)
    expires_at  = models.DateTimeField('Amal qilish muddati', null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "So'rovnoma"
        verbose_name_plural = "So'rovnomalar"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def public_url(self):
        return f"/survey/{self.slug}"

    @property
    def response_count(self):
        return self.responses.count()

    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class Question(models.Model):
    """So'rovnoma savoli"""

    TYPE_CHOICES = [
        ('text',       'Matn'),
        ('textarea',   'Ko\'p qatorli matn'),
        ('radio',      'Bir tanlov'),
        ('checkbox',   'Ko\'p tanlov'),
        ('select',     'Ro\'yxatdan tanlash'),
        ('rating',     'Reyting (1-5)'),
        ('scale',      'Shkala (1-10)'),
        ('date',       'Sana'),
        ('email',      'Email'),
        ('phone',      'Telefon'),
        ('number',     'Son'),
    ]

    survey      = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField('Savol matni')
    question_type = models.CharField('Savol turi', max_length=20, choices=TYPE_CHOICES, default='text')
    options     = models.JSONField('Variantlar', default=list, blank=True)
    is_required = models.BooleanField('Majburiy', default=False)
    order       = models.PositiveIntegerField('Tartib', default=0)
    placeholder = models.CharField('Placeholder', max_length=255, blank=True)
    help_text   = models.CharField('Yordam matni', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Savol'
        verbose_name_plural = 'Savollar'
        ordering = ['order']

    def __str__(self):
        return f"[{self.survey.title}] {self.question_text[:50]}"


class SurveyResponse(models.Model):
    """So'rovnomaga javob (bitta to'ldirilgan forma)"""

    survey      = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    respondent_name  = models.CharField('Arizachi ismi', max_length=200, blank=True)
    respondent_phone = models.CharField('Telefon', max_length=30, blank=True)
    respondent_email = models.CharField('Email', max_length=200, blank=True)
    ip_address  = models.GenericIPAddressField('IP manzil', null=True, blank=True)
    submitted_at = models.DateTimeField('Yuborilgan vaqt', default=timezone.now)

    class Meta:
        verbose_name = 'Javob'
        verbose_name_plural = 'Javoblar'
        ordering = ['-submitted_at']

    def __str__(self):
        name = self.respondent_name or 'Anonim'
        return f"{self.survey.title} — {name} ({self.submitted_at.strftime('%d.%m.%Y')})"


class Answer(models.Model):
    """Bitta savol uchun javob"""

    response    = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name='answers')
    question    = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    value       = models.TextField('Javob', blank=True)  # JSON string for multi-select

    class Meta:
        verbose_name = 'Javob elementi'
        verbose_name_plural = 'Javob elementlari'
        unique_together = ['response', 'question']

    def __str__(self):
        return f"{self.question.question_text[:30]}: {self.value[:30]}"
