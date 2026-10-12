from marshmallow import Schema, fields, validate

class MeasurementSchema(Schema):
    t           = fields.Float(required=True, validate=validate.Range(min=-100, max=100))
    h           = fields.Float(required=True, validate=validate.Range(min=0, max=100))
    p           = fields.Float(required=True, validate=validate.Range(min=0, max=2000))
    r           = fields.Float(required=True, validate=validate.Range(min=0, max=100))
    ra          = fields.Integer(required=True, validate=validate.Range(min=0))
    mq          = fields.Integer(required=True, validate=validate.Range(min=0))
    aht         = fields.Boolean(required=True)
    bmp         = fields.Boolean(required=True)
    recorded_at = fields.DateTime(required=False, format="iso")  # ISO 8601


class MeasurementBatchSchema(Schema):
    measurements = fields.List(
        fields.Nested(MeasurementSchema),
        required=True,
        validate=validate.Length(min=1, max=1000),
    )