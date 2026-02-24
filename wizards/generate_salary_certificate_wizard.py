# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nChGenerateSalaryCertificateWizard(models.TransientModel):
    _name = "l10n.ch.salary.certificate.generate.wizard"
    _description = "Generate Salary Certificate Wizard"

    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
        help="Employee for whom the salary certificate is generated.",
    )
    year = fields.Integer(
        required=True,
        default=lambda self: fields.Date.today().year,
        help="Calendar year of the salary certificate (current year or previous year only).",
    )

    existing_confirmed_id = fields.Many2one(
        "l10n.ch.salary.certificate",
        compute="_compute_existing",
        readonly=True,
        help="Already confirmed salary certificate for employee + year.",
    )
    replace_existing = fields.Boolean(
        string="Replace Existing Confirmed Certificate",
        help="Enable to replace an existing confirmed salary certificate with a corrected version.",
    )
    warning_message = fields.Text(compute="_compute_existing", readonly=True)

    @api.depends("employee_id", "year")
    def _compute_existing(self):
        cert_model = self.env["l10n.ch.salary.certificate"]
        for wizard in self:
            existing = cert_model.search(
                [
                    ("employee_id", "=", wizard.employee_id.id),
                    ("year", "=", wizard.year),
                    ("state", "=", "confirmed"),
                ],
                limit=1,
            )
            wizard.existing_confirmed_id = existing
            if existing:
                wizard.warning_message = _(
                    "A confirmed salary certificate already exists for this employee and year. "
                    "Enable 'Replace Existing Confirmed Certificate' to create a replacement draft."
                )
            else:
                wizard.warning_message = False

    def _check_year_scope(self):
        current_year = fields.Date.today().year
        allowed_years = {current_year, current_year - 1}
        if self.year not in allowed_years:
            raise UserError(
                _(
                    "Only current year (%(current)s) or previous year (%(previous)s) can be generated.",
                    current=current_year,
                    previous=current_year - 1,
                )
            )

    def _get_template(self):
        template = self.env["l10n.ch.salary.certificate.template"].search(
            [("year", "=", self.year), ("active", "=", True)],
            order="version desc,id desc",
            limit=1,
        )
        if not template:
            raise UserError(
                _("No active salary certificate template found for year %(year)s.", year=self.year)
            )
        return template

    def action_generate(self):
        self.ensure_one()
        self._check_year_scope()

        if not self.employee_id.needs_salary_certificate:
            raise UserError(
                _(
                    "Employee '%(employee)s' does not have 'Needs Salary Certificate' enabled.",
                    employee=self.employee_id.display_name,
                )
            )

        existing_draft = self.env["l10n.ch.salary.certificate"].search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("year", "=", self.year),
                ("state", "=", "draft"),
                ("create_uid", "=", self.env.user.id),
            ],
            limit=1,
        )
        if existing_draft:
            return {
                "type": "ir.actions.act_window",
                "name": "Salary Certificate",
                "res_model": "l10n.ch.salary.certificate",
                "res_id": existing_draft.id,
                "view_mode": "form",
                "target": "current",
            }

        if self.existing_confirmed_id and not self.replace_existing:
            raise UserError(self.warning_message)

        template = self._get_template()
        vals = {
            "name": _(
                "Salary Certificate %(employee)s %(year)s",
                employee=self.employee_id.display_name,
                year=self.year,
            ),
            "employee_id": self.employee_id.id,
            "year": self.year,
            "template_id": template.id,
        }
        if self.existing_confirmed_id:
            vals["replacement_of_id"] = self.existing_confirmed_id.id

        certificate = self.env["l10n.ch.salary.certificate"].create(vals)
        certificate.action_compute_field_values()
        certificate.action_generate_pdf()

        return {
            "type": "ir.actions.act_window",
            "name": "Salary Certificate",
            "res_model": "l10n.ch.salary.certificate",
            "res_id": certificate.id,
            "view_mode": "form",
            "target": "current",
        }
