from flask import Blueprint, current_app, request, jsonify
import logging
from flasgger import swag_from
from ..services.predict import predict_with_model

bp = Blueprint("predict", __name__)

logger = logging.getLogger("predict")


@bp.post("/predict")
@swag_from(
    {
        "tags": ["ml"],
        "consumes": ["application/json"],
        "parameters": [
            {
                "in": "body",
                "name": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Optional model tag; falls back to default if omitted",
                            "example": "RandomForestRegressor_win07",
                        },
                        "features": {
                            "type": "object",
                            "additionalProperties": {"type": ["number", "string"]},
                            "description": "Dictionary of feature_name -> value (keys must match model metadata feature_names).",
                            "example": {
                                "DL_hist_t_minus_6": 5972.43,
                                "DL_hist_t_minus_5": 5676.08,
                                "DL_hist_t_minus_4": 6051.62,
                                "DL_hist_t_minus_3": 6071.67,
                                "DL_hist_t_minus_2": 5784.66,
                                "DL_hist_t_minus_1": 6240.32,
                                "DL_hist_t_minus_0": 5695.44,
                                "noise_target": -100.0,
                                "noise_other_1": -110.0
                            },
                        },
                    },
                    "required": ["features"],
                },
            }
        ],
        "responses": {
            200: {
                "description": "Prediction result",
                "schema": {"$ref": "#/definitions/PredictResponse"},
            },
            400: {"description": "Bad Request"},
            404: {"description": "Model Not Found"},
            415: {"description": "Unsupported Media Type"},
            500: {"description": "Internal Server Error"},
        },
    }
)
def predict():
    logger.debug("Headers: %s", dict(request.headers))
    try:
        raw_body = request.get_data(as_text=True)
        logger.debug("Raw body: %s", raw_body)
    except Exception as e:
        logger.error("Failed to read request body: %s", e)

    # content-type / json guard 
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    # model registry check 
    models_dct: dict[str, dict] = current_app.extensions.get("models", {})
    if not models_dct:
        logger.error("Model registry not initialized (app.extensions['models'] missing).")
        return jsonify({"error": "Model registry not initialized."}), 500

    # resolve model tag 
    requested_tag = payload.get("model")
    model_tag = requested_tag or current_app.extensions.get("default_model_name")
    if not model_tag:
        return jsonify({"error": "No model specified and no default model configured."}), 400

    entry = models_dct.get(model_tag)
    if entry is None:
        return jsonify({"error": f"Model '{model_tag}' not found."}), 404

    model = entry["model"]
    metadata = entry["metadata"]

    # fetch expected feature names from metadata 
    feature_names = metadata.get("feature_names") or metadata.get("feature_names_in") or []
    if not feature_names:
        return jsonify({"error": f"Model '{model_tag}' has no feature_names in metadata."}), 500

    # input: generic features dict 
    features = payload.get("features")
    if not isinstance(features, dict) or not features:
        return jsonify({"error": "Field 'features' must be a non-empty object {feature_name: value}."}), 400

    # validate that all required features are provided & numeric 
    missing = [fn for fn in feature_names if fn not in features]
    if missing:
        return jsonify({"error": f"Missing required features: {missing}"}), 400

    # Coerce to floats (allow strings like "12.3")
    coerced_features = {}
    try:
        for fn in feature_names:
            coerced_features[fn] = float(features[fn])
    except Exception as e:
        return jsonify({"error": f"All feature values must be numeric (failed at '{fn}')"}), 400

    # predict 
    try:
        result = predict_with_model(
            model=model,
            metadata=metadata,
            features=coerced_features,  # flat dict keyed by model feature names
        )
    except Exception as e:
        logger.exception("Prediction failed: %s", e)
        return jsonify({"error": f"Prediction failed: {e}"}), 500

    return jsonify({"prediction": result["y_pred"], "model_tag": model_tag}), 200




@bp.get("/schema")
@swag_from(
    {
        "tags": ["ml"],
        "summary": "Describe required feature names and show an example request body",
        "parameters": [
            {
                "name": "model",
                "in": "query",
                "type": "string",
                "required": False,
                "description": "Model tag to inspect. Uses default model if not specified.",
            }
        ],
        "responses": {
            200: {
                "description": "Model feature contract and example PredictItem payload",
                "schema": {
                    "type": "object",
                    "properties": {
                        "model_tag": {"type": "string"},
                        "window_size": {"type": "integer"},
                        "feature_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Exact feature names in the order used during training",
                        },
                        "example_request": {"$ref": "#/definitions/PredictItem"},
                    },
                    "required": ["model_tag", "feature_names", "example_request"],
                },
                "examples": {
                    "application/json": {
                        "model_tag": "DecisionTreeRegressor_win03",
                        "window_size": 3,
                        "feature_names": [
                            "noise_target",
                            "noise_other_1",
                            "DL_hist_t_minus_0",
                            "DL_hist_t_minus_1",
                            "DL_hist_t_minus_2"
                        ],
                        "example_request": {
                            "model": "DecisionTreeRegressor_win03",
                            "features": {
                                "DL_hist_t_minus_2": 5784.66,
                                "DL_hist_t_minus_1": 6240.32,
                                "DL_hist_t_minus_0": 5695.44,
                                "noise_target": -100.0,
                                "noise_other_1": -110.0
                            }
                        }
                    }
                },
            },
            404: {
                "description": "Model not found",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                    "required": ["error"],
                },
            },
        },
    }
)
def schema():
    # Resolve model tag
    model_tag = request.args.get("model") or current_app.extensions.get("default_model_name")
    if not model_tag:
        return jsonify({"error": "No model specified and no default model configured."}), 404

    models_dct: dict[str, dict] = current_app.extensions.get("models", {})
    entry = models_dct.get(model_tag)
    if entry is None:
        return jsonify({"error": f"Model '{model_tag}' not found"}), 404

    metadata = entry["metadata"]
    feature_names = metadata.get("feature_names") or metadata.get("feature_names_in") or []
    window_size = int(metadata.get("window_size", 0))

    # Build example strictly from feature_names order
    example_features: dict[str, float] = {}

    example_data = {
        "DL_hist_t_minus_6": 5972.43,
        "DL_hist_t_minus_5": 5676.08,
        "DL_hist_t_minus_4": 6051.62,
        "DL_hist_t_minus_3": 6071.67,
        "DL_hist_t_minus_2": 5784.66,
        "DL_hist_t_minus_1": 6240.32,
        "DL_hist_t_minus_0": 5695.44,
        "noise_target": -100.0,
        "noise_other_1": -110.0
    }
                                
    for name in feature_names:
        if name in example_data:
            example_features[name] = example_data[name]
        else:
            # default for any other scalar features
            example_features[name] = 0.0

    example_request = {
        "model": model_tag,   # optional; included for clarity
        "features": example_features,
    }

    return jsonify(
        {
            "model_tag": model_tag,
            "window_size": window_size,
            "feature_names": feature_names,
            "example_request": example_request,
        }
    )
