import os

from dotenv import load_dotenv

# Load environment variables once at module import
load_dotenv(override=True)

# Environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT")

# Database settings
DATABASE_URL = os.environ["DATABASE_URL"]
CONNECTION_STRING = os.getenv("CONNECTION_STRING")

# Authentication settings
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_SECRET_KEY_DEVELOPMENT = os.getenv("CLERK_SECRET_KEY_DEVELOPMENT")
URL_JWKS = os.getenv("URL_JWKS")
URL_JWKS_DEVELOPMENT = os.getenv("URL_JWKS_DEVELOPMENT")

# Google Sheets settings
COMMISSIONING_KEY_JSON = os.getenv("COMMISSIONING_KEY_JSON")

# AWS settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

# Weather API settings
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# File paths
EXCEL_PATH = os.getenv("EXCEL_PATH")
