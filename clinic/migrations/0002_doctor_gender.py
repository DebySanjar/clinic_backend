from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinic', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='gender',
            field=models.CharField(
                choices=[('male', 'Erkak'), ('female', 'Ayol')],
                default='male',
                max_length=10,
                verbose_name='Jins',
            ),
        ),
    ]
