# -*- coding: utf-8 -*-

from odoo import fields, models


class L10nChSalaryCertificateFormula(models.Model):
    _name = "l10n.ch.salary.certificate.formula"
    _description = "Swiss Salary Certificate Field Formula"
    _order = "sequence, id"

    sequence = fields.Integer(
        default=10,
        help="Reihenfolge der Feldberechnung innerhalb der Vorlage.",
    )
    template_id = fields.Many2one(
        comodel_name="l10n.ch.salary.certificate.template",
        required=True,
        ondelete="cascade",
        index=True,
        help="Vorlage, zu der diese Feldformel gehört.",
    )
    pdf_field_id = fields.Many2one(
        comodel_name="l10n.ch.salary.certificate.pdf.field",
        required=True,
        ondelete="restrict",
        index=True,
        help="Technical PDF target field (field code in Form 11).",
    )
    pdf_field_key = fields.Char(
        related="pdf_field_id.code",
        store=True,
        index=True,
        help="Stable PDF field key for audit and reproducibility.",
    )
    label = fields.Char(
        related="pdf_field_id.label",
        store=True,
        help="Business label of the field according to form/guidance terminology.",
    )
    formula = fields.Text(
        required=True,
        help="Calculation logic for this field (for example salary rule sums, percentages, or Python logic).",
    )
    formula_kind = fields.Selection(
        selection=[
            ("fixed", "Fixed Value"),
            ("percentage", "Percentage"),
            ("assignment", "Field Assignment"),
            ("aggregation", "Aggregation"),
            ("python", "Python Code"),
        ],
        required=True,
        default="assignment",
        help="Art der Formel (fixer Wert, Aggregation, Zuweisung oder Python-Logik).",
    )
    active = fields.Boolean(
        default=True,
        help="Only active formulas are executed during salary certificate calculation.",
    )

    _sql_constraints = [
        (
            "salary_certificate_formula_field_unique",
            "unique(template_id, pdf_field_id)",
            "Each PDF field can only be configured once per template.",
        )
    ]
