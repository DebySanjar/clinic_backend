import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinic', '0002_doctor_gender'),
    ]

    operations = [
        migrations.CreateModel(
            name='Survey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255, verbose_name='Sarlavha')),
                ('description', models.TextField(blank=True, verbose_name='Tavsif')),
                ('status', models.CharField(choices=[('draft', 'Qoralama'), ('active', 'Faol'), ('closed', 'Yopilgan')], default='draft', max_length=10, verbose_name='Holat')),
                ('slug', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Link ID')),
                ('is_anonymous', models.BooleanField(default=True, verbose_name='Anonim')),
                ('allow_multiple', models.BooleanField(default=False, verbose_name="Bir necha marta to'ldirish")),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Amal qilish muddati')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': "So'rovnoma", 'verbose_name_plural': "So'rovnomalar", 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('question_text', models.TextField(verbose_name='Savol matni')),
                ('question_type', models.CharField(choices=[('text', 'Matn'), ('textarea', "Ko'p qatorli matn"), ('radio', 'Bir tanlov'), ('checkbox', "Ko'p tanlov"), ('select', "Ro'yxatdan tanlash"), ('rating', 'Reyting (1-5)'), ('scale', 'Shkala (1-10)'), ('date', 'Sana'), ('email', 'Email'), ('phone', 'Telefon'), ('number', 'Son')], default='text', max_length=20, verbose_name='Savol turi')),
                ('options', models.JSONField(blank=True, default=list, verbose_name='Variantlar')),
                ('is_required', models.BooleanField(default=False, verbose_name='Majburiy')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Tartib')),
                ('placeholder', models.CharField(blank=True, max_length=255, verbose_name='Placeholder')),
                ('help_text', models.CharField(blank=True, max_length=255, verbose_name='Yordam matni')),
                ('survey', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='clinic.survey')),
            ],
            options={'verbose_name': 'Savol', 'verbose_name_plural': 'Savollar', 'ordering': ['order']},
        ),
        migrations.CreateModel(
            name='SurveyResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('respondent_name', models.CharField(blank=True, max_length=200, verbose_name='Arizachi ismi')),
                ('respondent_phone', models.CharField(blank=True, max_length=30, verbose_name='Telefon')),
                ('respondent_email', models.CharField(blank=True, max_length=200, verbose_name='Email')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP manzil')),
                ('submitted_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Yuborilgan vaqt')),
                ('survey', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='clinic.survey')),
            ],
            options={'verbose_name': 'Javob', 'verbose_name_plural': 'Javoblar', 'ordering': ['-submitted_at']},
        ),
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('value', models.TextField(blank=True, verbose_name='Javob')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='clinic.question')),
                ('response', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='clinic.surveyresponse')),
            ],
            options={'verbose_name': 'Javob elementi', 'verbose_name_plural': 'Javob elementlari', 'unique_together': {('response', 'question')}},
        ),
    ]
