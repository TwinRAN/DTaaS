import logging
from flask import Blueprint, current_app, jsonify, request
from flasgger import swag_from

# Set up logger
logger = logging.getLogger(__name__)

bp = Blueprint("meta", __name__)


@bp.get("/health")
@swag_from(
    {
        "tags": ["meta"],
        "responses": {
            200: {
                "description": "Service is alive",
                "schema": {
                    "type": "object",
                    "properties": {"status": {"type": "string", "example": "ok"}},
                    "required": ["status"],
                },
                "examples": {
                    "application/json": {"status": "ok"}
                },
            }
        },
    }
)
def health():
    return jsonify({"status": "ok"})


@bp.get("/model_info")
@swag_from(
    {
        "tags": ["meta"],
        "parameters": [
            {
                "name": "model",
                "in": "query",
                "type": "string",
                "required": False,
                "description": "Model tag to get information about. If not provided, uses the default model tag.",
            }
        ],
        "responses": {
            200: {
                "description": "Full metadata for the requested model",
                "schema": {"$ref": "#/definitions/ModelInfo"},
                "examples": {
                    "application/json": {
                        "model_tag": "DecisionTreeRegressor_win03",
                        "model_info": {
                            "model_tag": "DecisionTreeRegressor_win03",
                            "model": "DecisionTreeRegressor",
                            "window_size": 3,
                            "parameters": {
                                "ccp_alpha": 0.0,
                                "criterion": "squared_error",
                                "max_depth": 5,
                                "max_features": "sqrt",
                                "max_leaf_nodes": None,
                                "min_impurity_decrease": 0.0,
                                "min_samples_leaf": 1,
                                "min_samples_split": 2,
                                "min_weight_fraction_leaf": 0.0,
                                "monotonic_cst": None,
                                "random_state": 1234,
                                "splitter": "best"
                            },
                            "feature_names": [
                                "noise_target",
                                "noise_other_1",
                                "DL_hist_t_minus_0",
                                "DL_hist_t_minus_1",
                                "DL_hist_t_minus_2"
                            ],
                            "training_features": 5,
                            "scaling": {
                                "window_scale_mode": "window_mean",
                                "noise_scaling": {"min_abs_db": 50.0, "max_abs_db": 150.0}
                            },
                            "random_state": 1234
                        }
                    }
                },
            },
            404: {"description": "Model not found"},
            500: {"description": "Internal server error: couldn't get model info"},
        },
    }
)
def model_info():
    """
    Get full metadata for a model by tag.
    If no 'model' query param is provided, returns the default model's metadata.
    """
    try:
        models_dct: dict = current_app.extensions.get("models", {})
        if not models_dct:
            return jsonify({"error": "Model registry not initialized."}), 500

        model_tag = request.args.get("model") or current_app.extensions.get("default_model_name")
        if not model_tag:
            return jsonify({"error": "No model specified and no default model configured."}), 404

        entry = models_dct.get(model_tag)
        if entry is None:
            return jsonify({"error": f"Model '{model_tag}' not found"}), 404

        # Return the full metadata dict without enumerating fields in the schema
        return jsonify({"model_tag": model_tag, "model_info": entry.get("metadata", {})})
    except Exception:
        logger.exception("Error getting model info")
        return jsonify({"error": "Internal server error: couldn't get model info"}), 500



@bp.get("/models")
@swag_from(
    {
        "tags": ["meta"],
        "responses": {
            200: {
                "description": "List of available models (minimal fields)",
                "schema": {
                    "type": "object",
                    "properties": {
                        "models": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/ModelListItem"},
                        }
                    },
                    "required": ["models"],
                },
                "examples": {
                    "application/json": {
                        "models": [
                            {
                                "model_tag": "DecisionTreeRegressor_win03",
                                "model": "DecisionTreeRegressor",
                                "window_size": 3
                            },
                            {
                                "model_tag": "XGBRegressor_win05",
                                "model": "XGBRegressor",
                                "window_size": 5
                            }
                        ]
                    }
                },
            },
            500: {"description": "Internal server error"},
        },
    }
)
def list_models():
    """
    List all available models with minimal metadata.
    Returns: {"models": [{model_tag, model, window_size}, ...]}
    """
    try:
        models_dct: dict = current_app.extensions.get("models", {})
        if not models_dct:
            return jsonify({"models": []}), 200

        models_min = []
        for tag, entry in models_dct.items():
            md = entry.get("metadata", {}) or {}
            models_min.append(
                {
                    "model_tag": tag,
                    "model": md.get("model", ""),
                    "window_size": int(md.get("window_size", 0)),
                }
            )

        return jsonify({"models": models_min}), 200
    except Exception as e:
        logger.exception("Error listing models")
        return jsonify({"error": f"Error getting model list: {e}"}), 500