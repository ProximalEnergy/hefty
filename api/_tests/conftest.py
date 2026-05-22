import os
import sys

from dotenv import load_dotenv

load_dotenv(".env.test")
os.environ.setdefault("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
os.environ.setdefault("DISABLE_PARAMETER_STORE_BOOTSTRAP", "1")
os.environ.setdefault("ENVIRONMENT", "development")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
