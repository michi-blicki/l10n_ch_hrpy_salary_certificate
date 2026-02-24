# -*- coding: utf-8 -*-

from odoo import fields, models


class L10nChSalaryCertificateComplianceRule(models.Model):
    _name = "l10n.ch.salary.certificate.compliance.rule"
    _description = "Swiss Salary Certificate Compliance Rule"
    _order = "sequence, id"

    sequence = fields.Integer(
        default=10,
        help="Execution order of guidance compliance checks.",
    )
    active = fields.Boolean(
        default=True,
        help="Only active rules are validated before confirming the salary certificate.",
    )

    template_id = fields.Many2one(
        comodel_name="l10n.ch.salary.certificate.template",
        required=True,
        ondelete="cascade",
        index=True,
        help="Template to which this compliance rule applies.",
    )
    code = fields.Char(
        required=True,
        help="Technical rule code for auditability, testing, and traceability.",
    )
    name = fields.Char(
        required=True,
        help="Business rule name aligned with guidance topics (for example item 15 replacement note).",
    )
    chapter = fields.Selection(
        selection=[
            ("chapter_i", "Chapter I"),
            ("chapter_ii", "Chapter II / Rz 72"),
        ],
        required=True,
        default="chapter_i",
        help="Guidance chapter of the rule: mandatory declarations (chapter I) or exceptions (chapter II/Rz 72).",
    )
    guidance_reference = fields.Char(help="Reference to guidance section, for example 'Rz 72'.")

    rule_type = fields.Selection(
        selection=[
            ("required_non_empty", "Target must be non-empty"),
            ("required_empty", "Target must be empty"),
            ("numeric_min", "Target numeric >= threshold"),
            ("numeric_max", "Target numeric <= threshold"),
            ("equals_value", "Target equals expected value"),
            ("contains_value", "Target contains expected value"),
            ("calendar_year_equals", "Target equals certificate year"),
            ("replacement_remark_exact", "Replacement remark exact text"),
            ("non_declarable_threshold", "Declare only above threshold"),
        ],
        required=True,
        default="required_non_empty",
        help="Validation type for field values, thresholds, and declaration logic.",
    )

    target_field_key = fields.Char(
        required=True,
        index=True,
        help="Target field key in the salary certificate validated by this rule.",
    )
    reference_field_key = fields.Char(
        help="Optional reference field key used for threshold-based checks."
    )
    threshold_value = fields.Float(
        default=0.0,
        help="Declaration threshold/limit according to guidance (for example chapter II / Rz 72).",
    )
    expected_value = fields.Char(
        help="Expected field content for exact-match or contains checks.",
    )

    _sql_constraints = [
        (
            "salary_certificate_compliance_rule_code_unique",
            "unique(template_id, code)",
            "Compliance rule code must be unique per template.",
        )
    ]
