from marshmallow import Schema, fields

class HealthResponseSchema(Schema):
    status = fields.String(metadata={"example": "ok"})

class ModelInfoSchema(Schema):
    model_tag = fields.String()
    model_info = fields.Dict()

class ModelListItemSchema(Schema):
    model_tag = fields.String(required=True, metadata={"example": "DecisionTreeRegressor_win03"})
    model = fields.String(required=True, metadata={"example": "DecisionTreeRegressor"})
    window_size = fields.Integer(required=True, metadata={"example": 3})

class ModelListResponseSchema(Schema):
    # Represent the /models response as an array of minimal model records
    models = fields.List(fields.Nested(ModelListItemSchema), required=True)
