# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import csv
import logging
import os
import tempfile

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, format_datetime, formatLang

from ..glabels_loader import load_glabels

_logger = logging.getLogger(__name__)

# Сливането на gLabels: CSV със запетаи и имената на колоните на първия ред.
# Това е РОДНИЯТ път на gLabels за `${поле}` в шаблона.
GLABELS_MERGE_TYPE = "Text/Comma/Line1Keys"

RELATIONAL_TYPES = ("many2one", "one2many", "many2many")


class ReportGLabelsAbstract(models.AbstractModel):
    """Двигателят на етикетите (ADR report-glabels/0001).

    Печатната форма носи `.glabels` шаблона и CSV-то. Двигателят чете
    колоните от първия ред на CSV-то, попълва ги от записите и подава
    шаблона и попълненото CSV на библиотеката, която рендерира PDF.

    Точката за разширение е `_glabels_value(record, column)`: модулите я
    наследяват, разпознават своите колони и връщат `super()` за чуждите.
    """

    _name = "report.report_glabels.abstract"
    _description = "Abstract gLabels Report"

    # ------------------------------------------------------------------
    # записите и формата
    # ------------------------------------------------------------------

    def _get_objs_for_report(self, docids, data):
        """Returns objects for the gLabels report.

        From WebUI these are either as docids taken from context.active_ids or
        in the case of wizard are in data. Manual calls may rely on regular
        context, setting docids, or setting data.
        """
        if docids:
            ids = docids
        elif data and "context" in data:
            ids = data["context"].get("active_ids", [])
        else:
            ids = self.env.context.get("active_ids", [])
        return self.env[self.env.context.get("active_model")].browse(ids)

    def _glabels_lib(self):
        """Библиотеката glabels — внася се чак тук, при печат."""
        path = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("report_glabels.library_path")
        )
        return load_glabels(path)

    def _glabels_report(self):
        """Печатната форма, която се рендерира в момента."""
        report_id = self.env.context.get("glabels_report_id")
        return self.env["ir.actions.report"].sudo().browse(report_id).exists()

    # ------------------------------------------------------------------
    # колоните и стойностите
    # ------------------------------------------------------------------

    def _glabels_columns(self, report):
        """Колоните, които двигателят трябва да попълни.

        По подразбиране — първият ред на CSV-то от формата. Отчет, строен в
        код, може да ги върне сам (виж адресните етикети на партньорите).
        """
        return report._glabels_get_columns()

    def _glabels_magic_values(self):
        """Стойности, които не зависят от записа (наследство от 11.0)."""
        user = self.env.user
        company = self.env.company
        return {
            "creator": user.name or "",
            "company": company.name or "",
            "date_now": format_date(self.env, fields.Date.context_today(self)),
            "currency": company.currency_id.symbol or "",
        }

    def _glabels_value(self, record, column):
        """Стойността на една колона за един запис.

        Връща низ или None, ако колоната е непозната. Наследниците първо
        проверяват своите колони и връщат `super()` за останалите:

            def _glabels_value(self, record, column):
                if column == "my_column":
                    return "..."
                return super()._glabels_value(record, column)
        """
        magic = self.env.context.get("glabels_magic_values")
        if magic is None:
            magic = self._glabels_magic_values()
        if column in magic:
            return magic[column]
        return self._glabels_field_path_value(record, column)

    def _glabels_field_path_value(self, record, path):
        """Стойност по път от полета: `default_code`, `categ_id.name`.

        Връща None, ако някое име по пътя не е поле, или ако междинно
        звено не е релация. Празна релация по пътя дава празен низ.
        """
        value = record
        names = path.split(".")
        for position, name in enumerate(names):
            field = value._fields.get(name)
            if field is None:
                return None
            if position == len(names) - 1:
                return ", ".join(
                    text
                    for text in (self._glabels_format(rec, field) for rec in value)
                    if text
                )
            if field.type not in RELATIONAL_TYPES:
                return None
            value = value[name]
        return None

    def _glabels_format(self, record, field):
        """Една стойност на поле като текст за етикета, по езика на потребителя."""
        value = record[field.name]
        if field.type == "boolean":
            return "1" if value else ""
        if field.type in ("integer", "float", "monetary"):
            # нулата е стойност, не липса — на етикета „0“ значи нещо
            if field.type == "integer":
                return str(value)
            if field.type == "monetary":
                currency_field = field.get_currency_field(record)
                currency = (
                    record[currency_field]
                    if currency_field
                    else self.env.company.currency_id
                )
                return formatLang(self.env, value, currency_obj=currency)
            digits = field.get_digits(self.env)
            return formatLang(self.env, value, digits=digits[1] if digits else 2)
        if not value:
            return ""
        if field.type in RELATIONAL_TYPES:
            return ", ".join(value.mapped("display_name"))
        if field.type == "selection":
            return dict(field._description_selection(self.env)).get(value, value)
        if field.type == "date":
            return format_date(self.env, value)
        if field.type == "datetime":
            return format_datetime(self.env, value)
        if field.type in ("binary", "image"):
            # байтовете на картинка в CSV нищо не значат за gLabels
            return ""
        return str(value)

    def _glabels_rows(self, objs, columns):
        """Редовете на CSV-то: по един на запис, колоните в реда на CSV-то."""
        this = self.with_context(glabels_magic_values=self._glabels_magic_values())
        rows = []
        unknown = set()
        for record in objs:
            row = {}
            for column in columns:
                value = this._glabels_value(record, column)
                if value is None:
                    unknown.add(column)
                    value = ""
                row[column] = value
            rows.append(row)
        if unknown:
            # Непознатата колона е ГРЕШКА, не празно поле: празният етикет
            # изглежда като успешен печат, а не е
            raise UserError(
                _(
                    "The label cannot be printed: these columns of the CSV data "
                    "file are neither fields of %(model)s nor known values: "
                    "%(columns)s",
                    model=objs._description,
                    columns=", ".join(sorted(unknown)),
                )
            )
        return rows

    # ------------------------------------------------------------------
    # рендерирането
    # ------------------------------------------------------------------

    def _glabels_open_label(self, report, workdir):
        """Шаблонът от формата — качен файл или (резервно) име/път."""
        glabels = self._glabels_lib()
        # съдържанието, не размера — виж _glabels_get_columns
        template_file = report.with_context(bin_size=False).glabels_template_file
        if template_file:
            path = os.path.join(workdir, "template.glabels")
            with open(path, "wb") as fh:
                fh.write(base64.b64decode(template_file))
            return glabels.Label.open(path)
        name = report.glabels_template
        if not name:
            raise UserError(
                _("The report %s has no gLabels template file.", report.name)
            )
        if os.path.isfile(name):
            return glabels.Label.open(name)
        label = glabels.Label(template=name)
        self._glabels_build_layout(label)
        return label

    def _glabels_build_layout(self, label):
        """Съдържание на етикет, строен в код (без шаблонен файл).

        Шаблонът от базата на gLabels е само хартия — празни рамки.
        Отчет без качен `.glabels` файл слага текста си тук.
        """

    def create_glabels_report(self, docids, data):
        """Шаблон + CSV → PDF.

        Returns:
            tuple: (pdf_bytes, "glabels")
        """
        if self._glabels_lib() is None:
            raise UserError(
                _(
                    "The gLabels library is not installed on this server, so "
                    "labels cannot be rendered."
                )
            )
        report = self._glabels_report()
        objs = self._get_objs_for_report(docids, data)
        if not objs:
            raise UserError(_("There is nothing to print."))

        columns = self._glabels_columns(report)
        if not columns:
            raise UserError(
                _(
                    "The report %s has no CSV data file listing the label "
                    "columns.",
                    report.name,
                )
            )
        rows = self._glabels_rows(objs, columns)

        with tempfile.TemporaryDirectory(prefix="odoo-glabels-") as workdir:
            label = self._glabels_open_label(report, workdir)

            csv_path = os.path.join(workdir, "data.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
            label.set_merge_source(GLABELS_MERGE_TYPE, csv_path)

            pdf_path = os.path.join(workdir, "labels.pdf")
            label.render_pdf(
                pdf_path,
                copies=max(report.glabels_copies, 1),
                crop_marks=report.glabels_crop_marks,
                outlines=report.glabels_outlines,
            )
            with open(pdf_path, "rb") as fh:
                pdf = fh.read()

        # Празен PDF е отказ, не резултат: надолу по веригата нула байта
        # изглеждат като „отпечата се“
        if not pdf:
            raise UserError(_("gLabels produced an empty PDF."))
        return pdf, "glabels"
