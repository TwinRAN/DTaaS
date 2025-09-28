# app/schemas/predict.py
from marshmallow import Schema, fields
from marshmallow import Schema, fields

class PredictItemSchema(Schema):
    """
    Single-item request for prediction.

    Payload format:
      {
        "model": "OptionalModelTag",        # optional; falls back to default if omitted
        "features": {                       # required; flat dict keyed by model's feature names
            "DL_hist_t_minus_6": 5972.43,
            "DL_hist_t_minus_5": 5676.08,
            "DL_hist_t_minus_4": 6051.62,
            "DL_hist_t_minus_3": 6071.67,
            "DL_hist_t_minus_2": 5784.66,
            "DL_hist_t_minus_1": 6240.32,
            "DL_hist_t_minus_0": 5695.44,
            "noise_target": -100.0,
            "noise_other_1": -110.0
          # ... any other features the model expects
        }
      }

    Notes:
    - Keys in `features` must match the model's `feature_names` exactly.
    - Values must be numeric; further semantic checks (e.g., DL_hist_* > 0, window length, noise scaling)
      are performed using model metadata inside the prediction service.
    """

    model = fields.String(
        required=False,
        metadata={
            "description": "Optional model tag to select a specific trained model. Uses default if omitted.",
            "example": "RandomForestRegressor_win07",
        },
    )

    features = fields.Dict(
        keys=fields.String(),
        values=fields.Float(),
        required=True,
        metadata={
            "description": "Dictionary of feature_name -> numeric value. Keys must match the model's feature_names.",
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
    )


class PredictResponseSchema(Schema):
    """Response for /api/predict."""

    prediction = fields.Float(
        required=True,
        metadata={
            "description": "Prediction result from the model",
            "example": 6025.5,
        },
    )
    model_tag = fields.String(
        required=True,
        metadata={
            "description": "Tag of the trained model used for prediction",
            "example": "RandomForestRegressor_win07",
        },
    )
