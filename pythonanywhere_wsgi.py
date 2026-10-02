"""
PythonAnywhere WSGI konfiguratsiya fayli.

PythonAnywhere dashboard > Web tab > WSGI configuration file
Bu faylni /var/www/yourusername_pythonanywhere_com_wsgi.py ga nusxalang
yoki to'g'ridan-to'g'ri shu faylni WSGI fayl sifatida ko'rsating.
"""

import sys
import os

# Loyiha papkasini yo'liga qo'shish
# PythonAnywhere da loyihangiz joylashgan papkani ko'rsating
project_home = '/home/yourusername/DjangoProject'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Virtual environment ni aktivlashtirish
# PythonAnywhere virtualenv path ni to'g'rilang
activate_this = '/home/yourusername/.virtualenvs/dentflow/bin/activate_this.py'
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

# .env fayldan environment o'zgaruvchilarini yuklash
from decouple import config as decouple_config

os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'

# Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
