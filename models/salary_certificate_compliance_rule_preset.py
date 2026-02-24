# -*- coding: utf-8 -*-

from odoo import fields, models


class L10nChSalaryCertificateComplianceRulePreset(models.Model):
    _name = "l10n.ch.salary.certificate.compliance.rule.preset"
    _description = "Swiss Salary Certificate Compliance Rule Preset"
    _order = "sequence, id"

    sequence = fields.Integer(
        default=10,
        help="Default order used when presets are auto-applied to new templates.",
    )
    active = fields.Boolean(
        default=True,
        help="Aktive Presets werden beim Erstellen neuer Templates automatisch übernommen.",
    )

    code = fields.Char(
        required=True,
        help="Eindeutiger technischer Preset-Code.",
    )
    name = fields.Char(
        required=True,
        help="Business name of the preset rule aligned with guidance.",
    )
    chapter = fields.Selection(
        selection=[
            ("chapter_i", "Chapter I"),
            ("chapter_ii", "Chapter II / Rz 72"),
        ],
        required=True,
        default="chapter_i",
        help="Guidance chapter assignment (chapter I or chapter II / Rz 72).",
    )
    guidance_reference = fields.Char(
        help="Specific guidance reference, for example 'Chapter II / Rz 72'.",
    )

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
        help="Type of business validation.",
    )

    target_field_key = fields.Char(
        required=True,
        index=True,
        help="Target field key in the salary certificate validated by this preset.",
    )
    reference_field_key = fields.Char(
        help="Optional reference field, typically used for threshold checks.",
    )
    threshold_value = fields.Float(
        default=0.0,
        help="Threshold/limit for declaration-dependent rules.",
    )
    expected_value = fields.Char(
        help="Expected text/value content for equals or contains checks.",
    )

    _sql_constraints = [
        (
            "salary_certificate_compliance_rule_preset_code_unique",
            "unique(code)",
            "Compliance rule preset code must be unique.",
        )
    ]
