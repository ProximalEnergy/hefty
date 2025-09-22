import os
import sys

from dotenv import load_dotenv

load_dotenv(".env.test")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
