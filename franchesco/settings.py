"""
Configuración del proyecto Franchesco - Plataforma web de venta y control de stock.
"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad -------------------------------------------------------------
# En producción definir DJANGO_SECRET_KEY, DJANGO_DEBUG=0 y DJANGO_ALLOWED_HOSTS.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-franchesco-solo-para-desarrollo-cambiar-en-produccion',
)
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# --- Aplicaciones ----------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Módulos del sistema
    'cuentas',       # Módulo de usuarios (registro, login, perfiles)
    'tienda',        # Módulo de catálogo (productos, categorías, stock)
    'promociones',   # Módulo de promociones, cupones y descuentos
    'carrito',       # Módulo de carrito de compras
    'pedidos',       # Módulo de compras, pedidos y pagos
    'panel',         # Módulo administrativo
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'franchesco.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'tienda.context_processors.navegacion',
                'carrito.context_processors.carrito',
            ],
        },
    },
]

WSGI_APPLICATION = 'franchesco.wsgi.application'

# --- Base de datos relacional ---------------------------------------------
# SQLite para desarrollo. Para producción se puede cambiar a PostgreSQL/MySQL.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- Correo -------------------------------------------------------------------
# Si se definen EMAIL_HOST_USER y EMAIL_HOST_PASSWORD (ej. Gmail con contraseña
# de aplicación) los mails se envían de verdad. Si no, se guardan como archivos
# en la carpeta "correos_enviados" para poder probar sin configurar nada.
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = True
else:
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = BASE_DIR / 'correos_enviados'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', f'Franchesco <{EMAIL_HOST_USER or "no-responder@franchesco.com"}>')
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24  # el enlace vence en 24 horas

# --- Autenticación ---------------------------------------------------------
AUTH_USER_MODEL = 'cuentas.Usuario'
LOGIN_URL = 'cuentas:login'
LOGIN_REDIRECT_URL = 'tienda:inicio'
LOGOUT_REDIRECT_URL = 'tienda:inicio'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'cuentas.validators.MayusculaValidator'},
    {'NAME': 'cuentas.validators.SimboloValidator'},
    {'NAME': 'cuentas.validators.NumeroValidator'},
]

# --- Internacionalización --------------------------------------------------
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos y multimedia --------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Bootstrap usa "danger" en lugar de "error"
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}

# --- Endurecimiento para producción ---------------------------------------
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
