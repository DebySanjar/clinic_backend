# PythonAnywhere Deploy Qo'llanmasi

## 1. Loyihani yuklash

```bash
git clone https://github.com/yourusername/DjangoProject.git
cd DjangoProject
```

## 2. Virtual environment yaratish

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. .env fayl yaratish

```bash
cp .env.example .env
nano .env
# Qiymatlarni to'ldiring:
# SECRET_KEY=...
# DEBUG=False
# ALLOWED_HOSTS=yourusername.pythonanywhere.com
# CORS_ALLOWED_ORIGINS=https://your-admin.vercel.app,https://your-webapp.vercel.app
# TELEGRAM_BOT_TOKEN=...
# WEBAPP_URL=https://your-webapp.vercel.app
# WEBHOOK_URL=https://yourusername.pythonanywhere.com
```

## 4. Migratsiya va statik fayllar

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_data        # Demo ma'lumotlar (ixtiyoriy)
```

## 5. WSGI konfiguratsiya

PythonAnywhere dashboard → Web → WSGI configuration file:

```python
import sys, os
sys.path.insert(0, '/home/yourusername/DjangoProject')
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## 6. Telegram Webhook o'rnatish

Deploydan so'ng bir marta ishlatish:

```bash
python -c "
import asyncio, django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()
from django.conf import settings
from aiogram import Bot
async def set_wh():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    await bot.set_webhook(f'{settings.WEBHOOK_URL}/api/bot/webhook/')
    await bot.session.close()
asyncio.run(set_wh())
print('Webhook o\'rnatildi!')
"
```

## 7. Always-on task (Reminder uchun)

PythonAnywhere → Tasks → Always-on task:
```
/home/yourusername/DjangoProject/.venv/bin/python /home/yourusername/DjangoProject/bot/main.py
```

---

## Vercel Deploy (Frontend)

### Admin Panel
1. GitHub → `frontend/admin_panel` papkasini import qiling
2. Framework: Vite
3. Environment variable: `VITE_API_BASE_URL=https://yourusername.pythonanywhere.com/api`

### User Panel (Telegram Web App)
1. GitHub → `frontend/user_panel` papkasini import qiling
2. Framework: Vite
3. Environment variable: `VITE_API_BASE_URL=https://yourusername.pythonanywhere.com/api`
4. Vercel URL ni `.env` ga `WEBAPP_URL` sifatida kiriting
5. BotFather da `/setmenubutton` → Web App URL ni yangilang
