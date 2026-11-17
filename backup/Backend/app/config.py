import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]

class Settings:
    PROJECT_NAME = os.getenv("PROJECT_NAME", "Jagspire AI Investigation Platform")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    STORAGE_DIR = Path(os.getenv("EVIDENCE_STORAGE_DIR", str(BASE_DIR / "storage"))).resolve()
    MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100")) * 1024 * 1024
    CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]

settings = Settings()

if not settings.SECRET_KEY or settings.SECRET_KEY == "secret":
    raise RuntimeError("Set a strong SECRET_KEY in Backend/.env before starting the API.")
if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Set it in Backend/.env.")
