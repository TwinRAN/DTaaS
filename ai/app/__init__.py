# app/__init__.py
import os.path
from flask import Flask, redirect, url_for
from flasgger import Swagger
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from .config import Config
from .services.model_registry import load_models
from .routes.predict import bp as predict_bp
from .routes.meta import bp as meta_bp

from .schemas.predict import PredictItemSchema, PredictResponseSchema
from .schemas.meta import HealthResponseSchema, ModelInfoSchema, ModelListItemSchema, ModelListResponseSchema

from flask_cors import CORS
import logging
from logging.config import dictConfig


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            }
        },
        "root": {
            "level": app.config["LOG_LEVEL"],
            "handlers": ["console"],
        },
    })
    app.logger.info("Logging initialized at %s", app.config["LOG_LEVEL"])


    cors_origins = app.config.get("CORS_ORIGINS")
    CORS(
        app,
        resources={
            r"/api*": {"origins": cors_origins},
            r"/models*": {"origins": cors_origins},
            r"/model_info*": {"origins": cors_origins},
            r"/health*": {"origins": cors_origins},
        },
    )

    app.extensions["default_model_name"] = app.config["DEFAULT_MODEL_NAME"]
    models_dct = load_models(app.config["MODELS_DIR"])
    app.extensions["models"] = models_dct

    # Register blueprints
    app.register_blueprint(predict_bp, url_prefix="/api")
    app.register_blueprint(meta_bp)

    # Build OpenAPI template with apispec + MarshmallowPlugin
    plugin = MarshmallowPlugin()

    desc = """
Machine-learning model serving API for OAI-derived experiments.

Overview
• Purpose: expose trained ML models behind a stable REST interface for prediction and model metadata.
• Inputs/Outputs: numeric features defined by the trained model (see **GET /api/schema**). Returns numeric predictions (single or batch).

Key Endpoints
• GET  /health        — liveness check
• GET  /models        — list of available models
• GET  /model_info    — model type, feature names, parameters
• GET  /api/schema    — required feature order and example payloads
• POST /api/predict   — single object or array body; returns predictions

Usage Notes
• Content-Type must be **application/json**.
"""

    spec = APISpec(
        title="Model Serving API",
        version="1.0.0",
        openapi_version="2.0",  # Flasgger’s UI expects swagger 2.0 structure
        plugins=[plugin],
        info={"description": desc},
    )

    # Component schemas
    spec.components.schema("PredictItem", schema=PredictItemSchema)
    spec.components.schema("PredictResponse", schema=PredictResponseSchema)
    spec.components.schema("HealthResponse", schema=HealthResponseSchema)
    spec.components.schema("ModelInfo", schema=ModelInfoSchema)
    spec.components.schema("ModelListItem", schema=ModelListItemSchema)
    spec.components.schema("ModelListResponse", schema=ModelListResponseSchema)


    # Swagger UI config
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/apidocs/",
    }

    # Final template handed to Flasgger
    # (Optional) add basePath/schemes so clients form URLs correctly in more environments
    template = spec.to_dict()
    template.setdefault("basePath", "/")
    template.setdefault("schemes", ["http"])

    Swagger(app, config=swagger_config, template=template)

    @app.route("/")
    def index():
        # Redirect to the Swagger UI using the registered endpoint (robust to route changes)
        return redirect(url_for("flasgger.apidocs"))

    return app
