import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    CORS_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")
    ]
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    MODELS_DIR: str = os.getenv("MODELS_DIR", "ml-models")
    DEFAULT_MODEL_NAME: str = os.getenv("DEFAULT_MODEL_NAME", "RandomForestRegressor_win07")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Discrete domains (must match schemas)
    NOISE_DB_VALUES = [-90, -100, -110, -120]
