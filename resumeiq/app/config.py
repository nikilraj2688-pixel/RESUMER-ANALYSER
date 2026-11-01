import os

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "resumeiq-super-secret-key-2026")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    RATELIMIT_STORAGE_URI = "memory://"
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "resume--analyser-96.firebasestorage.app")
    FIREBASE_PROJECT_ID = "resume--analyser-96"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
