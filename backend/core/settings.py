STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'staticfiles' / 'frontend']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_INDEX_FILE = True
WHITENOISE_ROOT = BASE_DIR / 'staticfiles' / 'frontend'