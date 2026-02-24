# -*- coding: utf-8 -*-

from odoo import fields, models


class L10nChSalaryCertificatePdfField(models.Model):
    _name = "l10n.ch.salary.certificate.pdf.field"
    _description = "Swiss Salary Certificate PDF Field Catalog"
    _order = "sequence, id"

    sequence = fields.Integer(
        default=10,
        help="Sorting of fields in business editing order.",
    )
    docversion = fields.Char(
        required=True,
        default="605.040.18N",
        index=True,
        help="Document version of the official form (docinfo code).",
    )
    code = fields.Char(
        required=True,
        index=True,
        help="Technischer Feldcode aus dem interaktiven PDF (stabiler Identifier).",
    )
    section = fields.Char(
        required=True,
        help="Business section, for example item 1, item 13, or remarks (item 15).",
    )
    label = fields.Char(
        required=True,
        help="Clear business label for payroll specialists, aligned with guidance terminology.",
    )
    help_text = fields.Text(
        help="Business meaning and guidance notes (chapter I/II, Rz 72).",
    )
    required_in_template = fields.Boolean(
        default=True,
        help="Mandatory mapping field: this PDF field must have a formula in the template.",
    )
    active = fields.Boolean(
        default=True,
        help="Only active field definitions are considered in completeness checks.",
    )

    _sql_constraints = [
        (
            "salary_certificate_pdf_field_docversion_code_unique",
            "unique(docversion, code)",
            "PDF field code must be unique per document version.",
        )
    ]
