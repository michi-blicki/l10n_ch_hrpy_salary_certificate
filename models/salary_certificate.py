# -*- coding: utf-8 -*-

import base64
import io
import re
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class L10nChSalaryCertificate(models.Model):
    _name = "l10n.ch.salary.certificate"
    _description = "Swiss Salary Certificate"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "year desc, id desc"

    name = fields.Char(required=True, default=lambda self: _("New"), tracking=True)
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    year = fields.Integer(required=True, index=True, tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("replaced", "Replaced"),
            ("archived", "Archived"),
        ],
        required=True,
        default="draft",
        tracking=True,
    )
    template_id = fields.Many2one(
        comodel_name="l10n.ch.salary.certificate.template",
        required=True,
        ondelete="restrict",
    )
    pdf_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="PDF Attachment",
        readonly=True,
        ondelete="set null",
        copy=False,
    )
    field_value_snapshot = fields.Json(default=dict, copy=False)

    replacement_of_id = fields.Many2one(
        comodel_name="l10n.ch.salary.certificate",
        string="Replacement Of",
        ondelete="set null",
        copy=False,
    )
    replaced_by_id = fields.Many2one(
        comodel_name="l10n.ch.salary.certificate",
        string="Replaced By",
        ondelete="set null",
        readonly=True,
        copy=False,
    )
    replaced_at = fields.Datetime(readonly=True, copy=False)

    confirmed_by_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
        copy=False,
    )
    confirmed_at = fields.Datetime(readonly=True, copy=False)

    is_compliance_valid = fields.Boolean(
        string="Compliance Valid",
        default=False,
        copy=False,
        help="Must be true before confirmation (guidance chapter I/II checks).",
    )
    compliance_message = fields.Text(copy=False)

    def action_download_pdf(self):
        self.ensure_one()
        if not self.pdf_attachment_id:
            raise ValidationError(_("No generated PDF is available for this salary certificate."))
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.pdf_attachment_id.id}?download=true",
            "target": "self",
        }

    @api.model
    def _cron_apply_retention_policy(self):
        current_year = fields.Date.today().year
        archive_threshold = current_year - 3
        delete_threshold = current_year - 10

        audit_model = self.env["l10n.ch.salary.certificate.audit.log"]

        to_archive = self.search([
            ("year", "<=", archive_threshold),
            ("year", ">", delete_threshold),
            ("state", "in", ["draft", "confirmed", "replaced"]),
        ])
        for cert in to_archive:
            old_state = cert.state
            cert.state = "archived"
            audit_model.create(
                {
                    "action": "archived",
                    "certificate_id_ref": cert.id,
                    "certificate_name": cert.name,
                    "employee_id": cert.employee_id.id,
                    "year": cert.year,
                    "state_before": old_state,
                    "details": _("Automatically archived by retention policy."),
                }
            )

        to_delete = self.search([
            ("year", "<=", delete_threshold),
        ])

        if to_delete:
            self.search([("replacement_of_id", "in", to_delete.ids)]).write({"replacement_of_id": False})
            self.search([("replaced_by_id", "in", to_delete.ids)]).write({"replaced_by_id": False})

            for cert in to_delete:
                audit_model.create(
                    {
                        "action": "deleted",
                        "certificate_id_ref": cert.id,
                        "certificate_name": cert.name,
                        "employee_id": cert.employee_id.id,
                        "year": cert.year,
                        "state_before": cert.state,
                        "details": _("Automatically deleted by retention policy (>10 years)."),
                    }
                )
            to_delete.unlink()

        return True

    def _get_pdf_reader_writer(self):
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            try:
                from PyPDF2 import PdfReader, PdfWriter
            except ImportError as exc:
                raise ValidationError(
                    _(
                        "PDF generation dependency is missing. Install python package "
                        "'pypdf' (or 'PyPDF2')."
                    )
                ) from exc
        return PdfReader, PdfWriter

    def _get_period_dates(self):
        self.ensure_one()
        return date(self.year, 1, 1), date(self.year, 12, 31)

    def _get_relevant_contracts(self):
        self.ensure_one()
        date_start, date_end = self._get_period_dates()
        return self.env["hr.contract"].search([
            ("employee_id", "=", self.employee_id.id),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", date_start),
            ("date_start", "<=", date_end),
        ])

    def _get_relevant_payslips(self):
        self.ensure_one()
        date_start, date_end = self._get_period_dates()
        return self.env["hr.payslip"].search([
            ("employee_id", "=", self.employee_id.id),
            ("state", "=", "done"),
            ("date_from", "<=", date_end),
            ("date_to", ">=", date_start),
        ])

    def _build_formula_context(self):
        self.ensure_one()
        contracts = self._get_relevant_contracts()
        payslips = self._get_relevant_payslips()
        payslip_lines = payslips.mapped("line_ids")

        def _sum_rule(rule_code):
            selected = payslip_lines.filtered(
                lambda line: (line.salary_rule_id.code or line.code or "") == rule_code
            )
            return sum(selected.mapped("total"))

        def _sum_rules(rule_codes):
            return sum(_sum_rule(code) for code in (rule_codes or []))

        def _sum_category(category_code):
            selected = payslip_lines.filtered(
                lambda line: (line.category_id.code or "") == category_code
            )
            return sum(selected.mapped("total"))

        def _percentage(base_amount, rate):
            return (base_amount or 0.0) * (rate or 0.0) / 100.0

        return {
            "employee": self.employee_id,
            "year": self.year,
            "contracts": contracts,
            "payslips": payslips,
            "payslip_lines": payslip_lines,
            "sum_rule": _sum_rule,
            "sum_rules": _sum_rules,
            "sum_category": _sum_category,
            "percentage": _percentage,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "abs": abs,
            "round": round,
        }

    def _evaluate_formula_line(self, formula_line, base_context):
        localdict = dict(base_context)
        formula = (formula_line.formula or "").strip()
        if not formula:
            raise ValidationError(
                _("Formula is empty for PDF field '%(field)s'.", field=formula_line.pdf_field_key)
            )

        try:
            if formula_line.formula_kind == "python":
                localdict["result"] = ""
                safe_eval(formula, localdict, mode="exec", nocopy=True)
                value = localdict.get("result", "")
            else:
                value = safe_eval(formula, localdict, mode="eval")
        except Exception as exc:
            raise ValidationError(
                _(
                    "Formula evaluation failed for PDF field '%(field)s': %(error)s",
                    field=formula_line.pdf_field_key,
                    error=str(exc),
                )
            ) from exc

        if value is None:
            return ""
        return str(value)

    def _snapshot_value(self, field_key):
        self.ensure_one()
        return (self.field_value_snapshot or {}).get(field_key, "")

    @staticmethod
    def _to_float(value):
        if value in (None, False, ""):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        normalized = str(value).strip()
        normalized = normalized.replace("'", "").replace(" ", "")
        if normalized.count(",") == 1 and normalized.count(".") == 0:
            normalized = normalized.replace(",", ".")
        elif normalized.count(",") >= 1 and normalized.count(".") >= 1:
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
        try:
            return float(normalized)
        except Exception:
            return 0.0

    def _expected_replacement_remark(self):
        self.ensure_one()
        if not self.replacement_of_id:
            return ""

        source_date = (
            self.replacement_of_id.confirmed_at
            or self.replacement_of_id.replaced_at
            or self.replacement_of_id.create_date
            or fields.Datetime.now()
        )
        date_value = fields.Datetime.to_datetime(source_date).date()
        return _(
            "This salary certificate replaces the salary certificate dated %(date)s",
            date=date_value.strftime("%d.%m.%Y"),
        )

    def action_run_compliance_checks(self):
        for record in self:
            record.action_compute_field_values()

            errors = []
            if record.year != record.template_id.year:
                errors.append(
                    _(
                        "Template year (%(template_year)s) and certificate year (%(certificate_year)s) must match.",
                        template_year=record.template_id.year,
                        certificate_year=record.year,
                    )
                )

            rules = record.template_id.compliance_rule_ids.filtered("active").sorted("sequence")
            if not rules:
                errors.append(_("No active compliance rules configured on the selected template."))

            for rule in rules:
                target = (record._snapshot_value(rule.target_field_key) or "").strip()
                reference = (record._snapshot_value(rule.reference_field_key) or "").strip()

                if rule.rule_type == "required_non_empty":
                    if not target:
                        errors.append(_("[%(rule)s] Field '%(field)s' must not be empty.", rule=rule.code, field=rule.target_field_key))

                elif rule.rule_type == "required_empty":
                    if target and record._to_float(target) != 0.0:
                        errors.append(_("[%(rule)s] Field '%(field)s' must be empty.", rule=rule.code, field=rule.target_field_key))

                elif rule.rule_type == "numeric_min":
                    if record._to_float(target) < rule.threshold_value:
                        errors.append(_("[%(rule)s] Field '%(field)s' must be >= %(threshold)s.", rule=rule.code, field=rule.target_field_key, threshold=rule.threshold_value))

                elif rule.rule_type == "numeric_max":
                    if record._to_float(target) > rule.threshold_value:
                        errors.append(_("[%(rule)s] Field '%(field)s' must be <= %(threshold)s.", rule=rule.code, field=rule.target_field_key, threshold=rule.threshold_value))

                elif rule.rule_type == "equals_value":
                    expected = (rule.expected_value or "").strip()
                    if target != expected:
                        errors.append(_("[%(rule)s] Field '%(field)s' must equal '%(expected)s'.", rule=rule.code, field=rule.target_field_key, expected=expected))

                elif rule.rule_type == "contains_value":
                    expected = (rule.expected_value or "").strip()
                    if expected and expected not in target:
                        errors.append(_("[%(rule)s] Field '%(field)s' must contain '%(expected)s'.", rule=rule.code, field=rule.target_field_key, expected=expected))

                elif rule.rule_type == "calendar_year_equals":
                    digits = re.sub(r"\D", "", target or "")
                    if digits and digits != str(record.year):
                        errors.append(_("[%(rule)s] Field '%(field)s' must match calendar year %(year)s.", rule=rule.code, field=rule.target_field_key, year=record.year))
                    elif not target:
                        errors.append(_("[%(rule)s] Field '%(field)s' is required for calendar year declaration.", rule=rule.code, field=rule.target_field_key))

                elif rule.rule_type == "replacement_remark_exact":
                    if record.replacement_of_id:
                        expected_text = record._expected_replacement_remark()
                        if target != expected_text:
                            errors.append(_("[%(rule)s] Field '%(field)s' must exactly be '%(expected)s'.", rule=rule.code, field=rule.target_field_key, expected=expected_text))

                elif rule.rule_type == "non_declarable_threshold":
                    reference_amount = record._to_float(reference)
                    declared_amount = record._to_float(target)
                    if reference_amount <= rule.threshold_value and declared_amount != 0.0:
                        errors.append(_("[%(rule)s] Field '%(field)s' must stay empty/0 below threshold %(threshold)s (reference field '%(reference)s').", rule=rule.code, field=rule.target_field_key, threshold=rule.threshold_value, reference=rule.reference_field_key or "-"))
                    if reference_amount > rule.threshold_value and (not target):
                        errors.append(_("[%(rule)s] Field '%(field)s' must be declared above threshold %(threshold)s.", rule=rule.code, field=rule.target_field_key, threshold=rule.threshold_value))

            record.is_compliance_valid = not errors
            record.compliance_message = "\n".join(errors) if errors else _("Guidance checks passed.")

            if errors:
                raise ValidationError(record.compliance_message)
        return True

    def action_compute_field_values(self):
        for record in self:
            formula_lines = record.template_id.formula_line_ids.filtered("active").sorted("sequence")
            if not formula_lines:
                raise ValidationError(_("The selected template has no active formula lines."))

            base_context = record._build_formula_context()
            computed_values = {}

            for line in formula_lines:
                computed_values[line.pdf_field_key] = record._evaluate_formula_line(line, base_context)

            record.field_value_snapshot = computed_values
        return True

    def action_generate_pdf(self):
        Attachment = self.env["ir.attachment"]
        PdfReader, PdfWriter = self._get_pdf_reader_writer()

        for record in self:
            if not record.template_id.official_pdf:
                raise ValidationError(_("The template has no official PDF uploaded."))

            if not record.field_value_snapshot:
                record.action_compute_field_values()

            template_pdf_bytes = base64.b64decode(record.template_id.official_pdf)
            reader = PdfReader(io.BytesIO(template_pdf_bytes))
            writer = PdfWriter()

            for page_index, page in enumerate(reader.pages):
                writer.add_page(page)
                writer.update_page_form_field_values(writer.pages[page_index], record.field_value_snapshot)

            if hasattr(writer, "set_need_appearances_writer"):
                writer.set_need_appearances_writer()

            output_stream = io.BytesIO()
            writer.write(output_stream)
            output_stream.seek(0)
            generated_pdf = output_stream.read()

            filename = f"salary_certificate_{record.employee_id.id}_{record.year}.pdf"
            attachment_vals = {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(generated_pdf),
                "res_model": record._name,
                "res_id": record.id,
                "mimetype": "application/pdf",
            }
            if record.pdf_attachment_id:
                record.pdf_attachment_id.write(attachment_vals)
                attachment = record.pdf_attachment_id
            else:
                attachment = Attachment.create(attachment_vals)

            record.pdf_attachment_id = attachment.id

        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for vals in vals_list:
            employee = self.env["hr.employee"].browse(vals.get("employee_id"))
            year = vals.get("year")

            if employee and not employee.needs_salary_certificate:
                raise ValidationError(
                    _(
                        "Salary certificate generation is only allowed for employees "
                        "with 'Needs Salary Certificate' enabled."
                    )
                )

            replacement_of_id = vals.get("replacement_of_id")
            replacement_of = self.browse(replacement_of_id) if replacement_of_id else self.browse()

            if replacement_of:
                if replacement_of.employee_id.id != vals.get("employee_id"):
                    raise ValidationError(
                        _("Replacement must target the same employee as the original certificate.")
                    )
                if replacement_of.year != year:
                    raise ValidationError(
                        _("Replacement must target the same year as the original certificate.")
                    )
                vals["state"] = "draft"

            existing_confirmed = self.search_count([
                ("employee_id", "=", vals.get("employee_id")),
                ("year", "=", year),
                ("state", "=", "confirmed"),
            ])
            if existing_confirmed and not replacement_of:
                raise ValidationError(
                    _(
                        "A confirmed salary certificate already exists for this employee and year. "
                        "Create a replacement draft instead."
                    )
                )

        records |= super().create(vals_list)
        return records

    @api.constrains("employee_id", "year", "state")
    def _check_unique_active_states(self):
        for record in self.filtered(lambda r: r.state in ("draft", "confirmed")):
            duplicates = self.search_count([
                ("id", "!=", record.id),
                ("employee_id", "=", record.employee_id.id),
                ("year", "=", record.year),
                ("state", "=", record.state),
            ])
            if duplicates:
                if record.state == "draft":
                    raise ValidationError(
                        _("Only one draft salary certificate is allowed per employee and year.")
                    )
                raise ValidationError(
                    _("Only one confirmed salary certificate is allowed per employee and year.")
                )

    @api.constrains("replacement_of_id", "employee_id", "year")
    def _check_replacement_relation(self):
        for record in self.filtered("replacement_of_id"):
            if record.replacement_of_id == record:
                raise ValidationError(_("A salary certificate cannot replace itself."))
            if record.replacement_of_id.employee_id != record.employee_id:
                raise ValidationError(_("Replacement must point to the same employee."))
            if record.replacement_of_id.year != record.year:
                raise ValidationError(_("Replacement must point to the same year."))

    def _check_confirm_compliance(self):
        for record in self:
            record.action_run_compliance_checks()

    def action_confirm(self):
        self.ensure_one()
        if self.state != "draft":
            raise ValidationError(_("Only draft certificates can be confirmed."))

        self._check_confirm_compliance()
        self.action_generate_pdf()

        if self.replacement_of_id:
            if self.replacement_of_id.state != "confirmed":
                raise ValidationError(
                    _("Replacement is only allowed for a currently confirmed certificate.")
                )
            self.replacement_of_id.write(
                {
                    "state": "replaced",
                    "replaced_by_id": self.id,
                    "replaced_at": fields.Datetime.now(),
                }
            )

        self.write(
            {
                "state": "confirmed",
                "confirmed_by_id": self.env.user.id,
                "confirmed_at": fields.Datetime.now(),
            }
        )
        return True
