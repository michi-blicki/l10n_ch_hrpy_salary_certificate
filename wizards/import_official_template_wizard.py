# -*- coding: utf-8 -*-

import base64
import io
import re

from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nChImportOfficialTemplateWizard(models.TransientModel):
    _name = "l10n.ch.salary.certificate.import.template.wizard"
    _description = "Import Official Swiss Salary Certificate Template"

    year = fields.Integer(
        required=True,
        default=lambda self: fields.Date.today().year,
        help="Calendar year for which the official salary certificate template is imported.",
    )
    upload_file = fields.Binary(
        required=True,
        help="Offizielles interaktives PDF (Formular 11) mit Docinfo, z. B. 'Form. 11 dfi 605.040.18N 01.21'.",
    )
    upload_filename = fields.Char(help="Dateiname der importierten PDF-Datei.")

    detected_docinfo = fields.Char(readonly=True, help="Erkannter Docinfo-Text aus dem PDF.")
    detected_lang_code = fields.Char(readonly=True, help="Erkannter Sprachcode aus der Docinfo (z. B. dfi).")
    detected_docversion = fields.Char(readonly=True, help="Erkannter Dokumentcode aus der Docinfo.")
    detected_form_version = fields.Char(readonly=True, help="Erkannte Formularversion aus der Docinfo.")
    detected_field_count = fields.Integer(readonly=True, help="Anzahl erkannter interaktiver PDF-Felder.")
    template_id = fields.Many2one(
        comodel_name="l10n.ch.salary.certificate.template",
        readonly=True,
        help="Template, das durch den Import erstellt oder aktualisiert wurde.",
    )

    def _get_pdf_reader(self, pdf_content):
        try:
            from pypdf import PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader
            except ImportError as exc:
                raise UserError(
                    _(
                        "PDF parsing dependency is missing. Install python package 'pypdf' "
                        "(or 'PyPDF2')."
                    )
                ) from exc

        try:
            return PdfReader(io.BytesIO(pdf_content))
        except Exception as exc:
            raise UserError(_("The uploaded file is not a readable PDF: %(error)s", error=str(exc))) from exc

    def _extract_docinfo(self, reader):
        raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
        normalized = re.sub(r"\s+", " ", raw_text).strip()

        pattern = re.compile(
            r"Form\.\s*11\s*([a-zA-Z]{1,4})\s*([0-9]{3}\.[0-9]{3}\.[0-9]{2}[A-Za-z]?)\s*([0-9]{2}\.[0-9]{2})",
            re.IGNORECASE,
        )
        match = pattern.search(normalized)
        if not match:
            raise UserError(
                _(
                    "No valid official docinfo marker found. Expected pattern like "
                    "'Form. 11 dfi 605.040.18N 01.21' (with flexible spacing)."
                )
            )

        lang_code = (match.group(1) or "").lower()
        docversion = (match.group(2) or "").strip()
        form_version = (match.group(3) or "").strip()

        return {
            "docinfo": match.group(0),
            "lang_code": lang_code,
            "docversion": docversion,
            "form_version": form_version,
        }

    def _extract_pdf_field_codes(self, reader):
        fields_map = reader.get_fields() or {}
        field_codes = sorted(code.strip() for code in fields_map.keys() if isinstance(code, str) and code.strip())
        if not field_codes:
            raise UserError(
                _(
                    "The PDF does not expose any fillable fields. "
                    "Please upload the official interactive form."
                )
            )
        return field_codes

    def _resolve_lang_ids(self, lang_code):
        lang_model = self.env["res.lang"]
        token_to_candidates = {
            "d": ["de_CH", "de_DE"],
            "f": ["fr_CH", "fr_FR"],
            "i": ["it_CH", "it_IT"],
            "e": ["en_US", "en_GB"],
        }

        lang_ids = []
        missing_tokens = []

        for token in lang_code:
            candidates = token_to_candidates.get(token)
            if not candidates:
                continue

            lang = lang_model.search([("code", "in", candidates)], order="code", limit=1)
            if not lang:
                prefix = candidates[0].split("_")[0]
                lang = lang_model.search([("code", "=like", f"{prefix}_%")], order="code", limit=1)

            if lang:
                lang_ids.append(lang.id)
            else:
                missing_tokens.append(token)

        if missing_tokens:
            raise UserError(
                _(
                    "Could not resolve res.lang entries for docinfo language token(s): %(tokens)s",
                    tokens=", ".join(sorted(set(missing_tokens))),
                )
            )

        if not lang_ids:
            raise UserError(_("No languages could be resolved from docinfo language code '%(code)s'.", code=lang_code))

        return list(dict.fromkeys(lang_ids))

    def _build_formula_commands(self, pdf_field_records):
        commands = []
        for index, pdf_field in enumerate(pdf_field_records, start=1):
            commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": index * 10,
                        "pdf_field_id": pdf_field.id,
                        "formula_kind": "fixed",
                        "formula": "''",
                    },
                )
            )
        return commands

    def _sync_template_formulas(self, template, pdf_field_records):
        formula_model = self.env["l10n.ch.salary.certificate.formula"]
        existing_map = {
            line.pdf_field_id.id: line
            for line in template.formula_line_ids
        }

        for index, pdf_field in enumerate(pdf_field_records.sorted("sequence"), start=1):
            line = existing_map.get(pdf_field.id)
            if line:
                line.sequence = index * 10
                continue
            formula_model.create(
                {
                    "template_id": template.id,
                    "sequence": index * 10,
                    "pdf_field_id": pdf_field.id,
                    "formula_kind": "fixed",
                    "formula": "''",
                }
            )

    def action_import(self):
        self.ensure_one()
        if not self.upload_file:
            raise UserError(_("Please upload an official PDF template."))

        pdf_content = base64.b64decode(self.upload_file)
        reader = self._get_pdf_reader(pdf_content)

        docinfo = self._extract_docinfo(reader)
        field_codes = self._extract_pdf_field_codes(reader)

        lang_ids = self._resolve_lang_ids(docinfo["lang_code"])

        template_model = self.env["l10n.ch.salary.certificate.template"]
        pdf_field_model = self.env["l10n.ch.salary.certificate.pdf.field"]

        existing_template = template_model.search(
            [
                ("year", "=", self.year),
                ("version", "=", docinfo["form_version"]),
                ("docversion", "=", docinfo["docversion"]),
                ("docinfo_lang_code", "=", docinfo["lang_code"]),
            ],
            limit=1,
        )

        if existing_template:
            existing_template.write(
                {
                    "lang_ids": [(6, 0, lang_ids)],
                    "official_pdf": self.upload_file,
                    "official_pdf_filename": self.upload_filename,
                }
            )

            pdf_field_records = self.env["l10n.ch.salary.certificate.pdf.field"]
            for index, code in enumerate(field_codes, start=1):
                pdf_field = pdf_field_model.search(
                    [
                        ("docversion", "=", docinfo["docversion"]),
                        ("code", "=", code),
                    ],
                    limit=1,
                )
                if not pdf_field:
                    pdf_field = pdf_field_model.create(
                        {
                            "sequence": index * 10,
                            "docversion": docinfo["docversion"],
                            "code": code,
                            "section": "Imported",
                            "label": code,
                            "required_in_template": True,
                        }
                    )
                pdf_field_records |= pdf_field

            self._sync_template_formulas(existing_template, pdf_field_records)

            self.write(
                {
                    "template_id": existing_template.id,
                    "detected_docinfo": docinfo["docinfo"],
                    "detected_lang_code": docinfo["lang_code"],
                    "detected_docversion": docinfo["docversion"],
                    "detected_form_version": docinfo["form_version"],
                    "detected_field_count": len(field_codes),
                }
            )
            return {
                "type": "ir.actions.act_window",
                "res_model": "l10n.ch.salary.certificate.template",
                "res_id": existing_template.id,
                "view_mode": "form",
                "target": "current",
            }

        pdf_field_records = self.env["l10n.ch.salary.certificate.pdf.field"]
        for index, code in enumerate(field_codes, start=1):
            pdf_field = pdf_field_model.search(
                [
                    ("docversion", "=", docinfo["docversion"]),
                    ("code", "=", code),
                ],
                limit=1,
            )
            if not pdf_field:
                pdf_field = pdf_field_model.create(
                    {
                        "sequence": index * 10,
                        "docversion": docinfo["docversion"],
                        "code": code,
                        "section": "Imported",
                        "label": code,
                        "required_in_template": True,
                    }
                )
            pdf_field_records |= pdf_field

        template_vals = {
            "name": _(
                "Official Template %(docversion)s %(version)s",
                docversion=docinfo["docversion"],
                version=docinfo["form_version"],
            ),
            "year": self.year,
            "version": docinfo["form_version"],
            "docversion": docinfo["docversion"],
            "docinfo_lang_code": docinfo["lang_code"],
            "official_pdf": self.upload_file,
            "official_pdf_filename": self.upload_filename,
            "lang_ids": [(6, 0, lang_ids)],
            "formula_line_ids": self._build_formula_commands(pdf_field_records),
        }
        template = template_model.create(template_vals)

        self.write(
            {
                "template_id": template.id,
                "detected_docinfo": docinfo["docinfo"],
                "detected_lang_code": docinfo["lang_code"],
                "detected_docversion": docinfo["docversion"],
                "detected_form_version": docinfo["form_version"],
                "detected_field_count": len(field_codes),
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "l10n.ch.salary.certificate.template",
            "res_id": template.id,
            "view_mode": "form",
            "target": "current",
        }
