import os
from pathlib import Path
# dj_database_url may not be installed in test/dev environments; import if available
try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# 1. ASOSIY YO'LLAR
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. XAVFSIZLIK SOZLAMALARI (Render uchun muhit o'zgaruvchilaridan olinadi)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-dev')

# Renderda False, Predatoringizda True bo'ladi
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# 3. ILOVALER (Jazzmin har doim admin'dan tepada bo'lishi shart)
INSTALLED_APPS = [
    'jazzmin',
    'app',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# 4. MIDDLEWARE (WhiteNoise statik fayllar uchun qo'shildi)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'app.middleware.OneSessionPerUserMiddleware',
]
# whitenoise is optional (not needed for tests/development without staticfiles)
try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')
except ImportError:
    pass

MIDDLEWARE += [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Agar alohida templates papkangiz bo'lsa
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# 5. MA'LUMOTLAR BAZASI (Render PostgreSQL yoki SQLite-ni o'zi tanlaydi)
if dj_database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL', 'postgresql://postgres:1234@127.0.0.1:5432/exam_db'),
            conn_max_age=600
        )
    }
else:
    # fallback: simple sqlite for development when dj_database_url isn't installed
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# during `manage.py test`, sqlite in-memory database is convenient and avoids
# requiring a running Postgres instance; this mirrors common patterns.
import sys
if 'test' in sys.argv or 'pytest' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }


# 6. PAROL VALIDATSIYASI
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# 7. JAZZMIN SOZLAMALARI (Tartibga keltirildi)
JAZZMIN_SETTINGS = {
    "site_title": "Imtihon Admin",
    "site_header": "Imtihon",
    "welcome_sign": "Admin panelga xush kelibsiz",
    "copyright": "Imtihon Tizimi Ltd",
    "search_model": ["app.User", "app.Group"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Statistika", "url": "admin_statistics", "permissions": ["auth.view_user"]},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "theme": "default",
    "dark_mode_theme": "darkly", # Predator uslubidagi tungi rejim
    "custom_js": "js/admin_theme_toggle.js",
    "custom_css": "css/admin_custom.css",
    "language_chooser": False,
}

# Render serverida fayllar yig'iladigan papka
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise yordamida statik fayllarni siqib yetkazish
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# 9. TIL VA VAQT
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True


# 10. FOYDALANUVCHI MODELI VA LOGIN YO'LLARI
AUTH_USER_MODEL = 'app.User'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'