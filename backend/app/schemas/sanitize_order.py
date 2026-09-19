from marshmallow import Schema, fields, validate


SANITIZE_METHODS = ("uv", "chemical")
SANITIZE_STATUSES = ("open", "doing", "done", "void")


class SanitizeOrderCreateSchema(Schema):
    room_id = fields.Int(required=True, data_key="roomId")
    method = fields.Str(required=True, validate=validate.OneOf(SANITIZE_METHODS))
    operator_name = fields.Str(required=True, data_key="operatorName", validate=validate.Length(min=1, max=64))
    planned_at = fields.DateTime(required=True, data_key="plannedAt")


class SanitizeOrderTransitionSchema(Schema):
    to_status = fields.Str(
        required=True,
        data_key="toStatus",
        validate=validate.OneOf(("doing", "done", "void")),
    )


class SanitizeOrderOutSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(data_key="roomId")
    method = fields.Str()
    status = fields.Str()
    operator_name = fields.Str(data_key="operatorName")
    planned_at = fields.DateTime(data_key="plannedAt")
    started_at = fields.DateTime(allow_none=True, data_key="startedAt")
    finished_at = fields.DateTime(allow_none=True, data_key="finishedAt")
