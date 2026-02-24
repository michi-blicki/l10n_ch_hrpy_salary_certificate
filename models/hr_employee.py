# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    needs_salary_certificate = fields.Boolean(
        string="Needs Salary Certificate",
        help="Indicates whether this employee requires a Swiss salary certificate.",
    )

    def action_open_salary_certificates(self):
        self.ensure_one()
        action = self.env.ref("l10n_ch_hrpy_salary_certificate.action_l10n_ch_salary_certificate").read()[0]
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {
            "default_employee_id": self.id,
            "search_default_filter_confirmed": 1,
            "search_default_group_by_year": 1,
        }
        return action

    def action_open_generate_salary_certificate_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Generate Salary Certificate",
            "res_model": "l10n.ch.salary.certificate.generate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_employee_id": self.id},
        }
