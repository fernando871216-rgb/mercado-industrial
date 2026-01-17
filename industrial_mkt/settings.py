import dj_database_url
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SEGURIDAD
SECRET_KEY = 'django-insecure-htgh&@rqt_a!$7ats%a7r_i!ig5u$z$ifjr3&g^uk@mrkzfu#j'
DEBUG = True 
ALLOWED_HOSTS = ["*"]

# APLICACIONES
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'cloudinary',
    'django.contrib.staticfiles',
    'marketplace',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'industrial_mkt.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'industrial_mkt.wsgi.application'

# BASE DE DATOS
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        conn_max_age=600
    )
}

# CONFIGURACIÓN DE CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://mercado-industrial.onrender.com',
    'https://www.mercadopago.com.mx',
    'https://mercadopago.com.mx',
    'https://www.mercadopago.com.ar',
    'https://mercadopago.com.ar',
    'https://*.mercadopago.com',
]

# ARCHIVOS ESTÁTICOS
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# LOGIN / LOGOUT
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# CLOUDINARY (Configuración para Imágenes y PDFs)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dkr9nywvb',
    'API_KEY': '159795361454715',
    'API_SECRET': 'R_pVI8FdS2aQ411SJ0pM_fehj74',
}

# CAMBIO IMPORTANTE: Usamos RawMedia para que acepte PDFs sin errores
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.RawMediaCloudinaryStorage'

# CORREOS
ADMIN_EMAIL = 'fernando871216@gmail.com'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'Mercado Industrial <fernando871216@gmail.com>'

# INTERNACIONALIZACIÓN
LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
