# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L10nChSalaryCertificateTemplate(models.Model):
    _name = "l10n.ch.salary.certificate.template"
    _description = "Swiss Salary Certificate Template"

    name = fields.Char(
        required=True,
        help="Business name of the salary certificate template (for example: Official Template 2026).",
    )
    year = fields.Integer(
        required=True,
        help="Calendar year of the salary certificate (Guidance section D).",
    )
    version = fields.Char(
        required=True,
        default="01.21",
        help="Form version according to docinfo, for example '01.21'.",
    )
    docinfo_lang_code = fields.Char(
        required=True,
        default="dfi",
        help="Language code from the docinfo at the end of the form (for example: dfi).",
    )
    docversion = fields.Char(
        required=True,
        default="605.040.18N",
        help="Document version code from the official form docinfo.",
    )
    official_pdf = fields.Binary(
        required=True,
        attachment=True,
        help="Official interactive PDF template (Form 11) used for field mapping.",
    )
    official_pdf_filename = fields.Char(
        help="Filename of the imported official PDF template.",
    )
    lang_ids = fields.Many2many(
        comodel_name="res.lang",
        relation="l10n_ch_salary_certificate_template_lang_rel",
        column1="template_id",
        column2="lang_id",
        string="Languages",
        required=True,
        default=lambda self: self._default_lang_ids(),
        help="Languages covered by this template, stored as res.lang records.",
    )
    active = fields.Boolean(
        default=True,
        help="Only active templates can be selected for salary certificate generation.",
    )
    formula_line_ids = fields.One2many(
        comodel_name="l10n.ch.salary.certificate.formula",
        inverse_name="template_id",
        string="Formula Lines",
        help="Formula mapping per PDF field (each field position requires a formula).",
    )
    compliance_rule_ids = fields.One2many(
        comodel_name="l10n.ch.salary.certificate.compliance.rule",
        inverse_name="template_id",
        string="Compliance Rules",
        help="Validation rules for Guidance chapter I and chapter II / Rz 72.",
    )

    @api.model
    def _default_compliance_rule_commands(self):
        presets = self.env["l10n.ch.salary.certificate.compliance.rule.preset"].search([
            ("active", "=", True),
        ])
        commands = []
        for preset in presets.sorted("sequence"):
            commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": preset.sequence,
                        "active": preset.active,
                        "code": preset.code,
                        "name": preset.name,
                        "chapter": preset.chapter,
                        "guidance_reference": preset.guidance_reference,
                        "rule_type": preset.rule_type,
                        "target_field_key": preset.target_field_key,
                        "reference_field_key": preset.reference_field_key,
                        "threshold_value": preset.threshold_value,
                        "expected_value": preset.expected_value,
                    },
                )
            )
        return commands

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("compliance_rule_ids"):
                vals["compliance_rule_ids"] = self._default_compliance_rule_commands()
        return super().create(vals_list)

    @api.model
    def _default_lang_ids(self):
        return self.env["res.lang"].search([("code", "in", ["de_CH", "fr_CH", "it_CH"])]).ids

    @api.constrains("formula_line_ids", "docversion")
    def _check_complete_pdf_field_mapping(self):
        for template in self:
            required_fields = self.env["l10n.ch.salary.certificate.pdf.field"].search([
                ("docversion", "=", template.docversion),
                ("required_in_template", "=", True),
                ("active", "=", True),
            ])
            mapped_field_ids = template.formula_line_ids.mapped("pdf_field_id").ids
            missing_fields = required_fields.filtered(lambda f: f.id not in mapped_field_ids)
            if missing_fields:
                raise ValidationError(
                    _(
                        "Template '%(template)s' is incomplete. Missing formula mapping for: %(fields)s",
                        template=template.display_name,
                        fields=", ".join(missing_fields.mapped("code")),
                    )
                )

            empty_formula_lines = template.formula_line_ids.filtered(lambda line: not (line.formula or "").strip())
            if empty_formula_lines:
                raise ValidationError(
                    _(
                        "Template '%(template)s' has empty formulas for fields: %(fields)s",
                        template=template.display_name,
                        fields=", ".join(empty_formula_lines.mapped("pdf_field_key")),
                    )
                )

    @api.constrains("docinfo_lang_code", "lang_ids")
    def _check_docinfo_lang_code_mapping(self):
        code_map = {
            "d": {"de_CH"},
            "f": {"fr_CH"},
            "i": {"it_CH"},
            "e": {"en_US"},
        }
        for template in self:
            expected_codes = set()
            for token in (template.docinfo_lang_code or "").strip().lower():
                expected_codes |= code_map.get(token, set())

            if not expected_codes:
                continue

            selected_codes = set(template.lang_ids.mapped("code"))
            missing_codes = expected_codes - selected_codes
            if missing_codes:
                raise ValidationError(
                    _(
                        "Docinfo language code '%(code)s' requires languages %(langs)s.",
                        code=template.docinfo_lang_code,
                        langs=", ".join(sorted(missing_codes)),
                    )
                )

    @api.constrains("compliance_rule_ids")
    def _check_compliance_rule_coverage(self):
        for template in self:
            active_rules = template.compliance_rule_ids.filtered("active")
            if not active_rules:
                raise ValidationError(
                    _(
                        "Template '%(template)s' requires configured compliance rules "
                        "for guidance validation.",
                        template=template.display_name,
                    )
                )

            chapter_i_rules = active_rules.filtered(lambda rule: rule.chapter == "chapter_i")
            chapter_ii_rules = active_rules.filtered(lambda rule: rule.chapter == "chapter_ii")
            if not chapter_i_rules:
                raise ValidationError(
                    _(
                        "Template '%(template)s' needs at least one active Chapter I compliance rule.",
                        template=template.display_name,
                    )
                )
            if not chapter_ii_rules:
                raise ValidationError(
                    _(
                        "Template '%(template)s' needs at least one active Chapter II/Rz72 compliance rule.",
                        template=template.display_name,
                    )
                )

    _sql_constraints = [
        (
            "salary_certificate_template_year_version_unique",
            "unique(year, version)",
            "A salary certificate template version must be unique per year.",
        )
    ]
