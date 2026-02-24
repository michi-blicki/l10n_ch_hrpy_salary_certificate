# -*- coding: utf-8 -*-

from odoo import fields, models


class L10nChSalaryCertificateAuditLog(models.Model):
    _name = "l10n.ch.salary.certificate.audit.log"
    _description = "Swiss Salary Certificate Audit Log"
    _order = "event_at desc, id desc"

    event_at = fields.Datetime(required=True, default=fields.Datetime.now)
    action = fields.Selection(
        selection=[
            ("archived", "Archived"),
            ("deleted", "Deleted"),
        ],
        required=True,
    )
    certificate_model = fields.Char(default="l10n.ch.salary.certificate", required=True)
    certificate_id_ref = fields.Integer(required=True)
    certificate_name = fields.Char()
    employee_id = fields.Many2one("hr.employee", ondelete="set null", index=True)
    year = fields.Integer(index=True)
    state_before = fields.Char()
    details = fields.Text()
