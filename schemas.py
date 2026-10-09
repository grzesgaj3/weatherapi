from marshmallow import Schema, fields, validate, ValidationError

class MeasurementSchema(Schema):
    temperature = fields.Float(required=True, validate=validate.Range(min=-100, max=100))
    humidity    = fields.Float(required=True, validate=validate.Range(min=0, max=100))
    pressure    = fields.Float(required=True, validate=validate.Range(min=0, max=2000))
    co          = fields.Float(required=True, validate=validate.Range(min=0, max=100000))
    recorded_at = fields.DateTime(required=False, format="iso")  # ISO 8601


class MeasurementBatchSchema(Schema):
    measurements = fields.List(
        fields.Nested(MeasurementSchema),
        required=True,
        validate=validate.Length(min=1, max=1000),
    )