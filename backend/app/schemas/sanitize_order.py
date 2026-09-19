from marshmallow import Schema, fields, validate


SANITIZE_METHODS = ("uv", "chemical")
SANITIZE_STATUSES = ("open", "doing", "done", "void")
# 流转目标只允许终态外的三种动作；合法性由 app.sanitize_rules 状态机判定
SANITIZE_TRANSITION_TARGETS = ("doing", "done", "void")


class SanitizeOrderCreateSchema(Schema):
    room_id = fields.Int(required=True, data_key="roomId")
    method = fields.Str(required=True, validate=validate.OneOf(SANITIZE_METHODS))
    operator_name = fields.Str(required=True, data_key="operatorName", validate=validate.Length(min=1, max=64))
    planned_at = fields.DateTime(required=True, data_key="plannedAt")


class SanitizeOrderTransitionSchema(Schema):
    to = fields.Str(required=True, validate=validate.OneOf(SANITIZE_TRANSITION_TARGETS))


class SanitizeOrderOutSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(data_key="roomId")
    method = fields.Str()
    status = fields.Str()
    operator_name = fields.Str(data_key="operatorName")
    planned_at = fields.DateTime(data_key="plannedAt")
    started_at = fields.DateTime(data_key="startedAt", allow_none=True)
    finished_at = fields.DateTime(data_key="finishedAt", allow_none=True)
