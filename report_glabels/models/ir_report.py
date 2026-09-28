# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64
import csv
import io
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# Знаците, които парсерът на gLabels НЕ приема в име на поле
# (glabels-qt model/SubstitutionField.cpp:144): `:` започва формата,
# `}` затваря полето. Колона с тях никога няма да се попълни.
GLABELS_FORBIDDEN_CHARS = (":", "}")


def parse_glabels_columns(csv_bytes):
    """Имената на колоните от първия ред на CSV-то.

    Първият ред е договорът между шаблона и двигателя (ADR report-glabels/0001):
    имената му са имената на `${полетата}` в шаблона. Останалите редове са
    примерни данни на дизайнера и тук не значат нищо.
    """
    if not csv_bytes:
        return []
    # utf-8-sig маха BOM-а, който Excel и LibreOffice слагат в началото —
    # иначе първата колона се казва „﻿name“ и никога не съвпада
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    return [col.strip() for col in header if col.strip()]


class ReportAction(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(
        selection_add=[("glabels", "gLabels (PDF labels)")],
        ondelete={"glabels": "set default"},
    )

    glabels_template_file = fields.Binary(
        string="gLabels Template File",
        attachment=True,
        help="The .glabels file as saved by gLabels. The label layout, fonts "
        "and embedded images all come from it.",
    )
    glabels_template_filename = fields.Char(string="gLabels Template File Name")
    glabels_csv_file = fields.Binary(
        string="CSV Data File",
        attachment=True,
        help="The CSV file the label was designed with. Its first line lists "
        "the columns, i.e. the ${fields} used in the template. Each column is "
        "filled from the printed record: a field path such as default_code or "
        "categ_id.name, a magic value (creator, company, date_now, currency) "
        "or a column provided by another module. The other lines are ignored.",
    )
    glabels_csv_filename = fields.Char(string="CSV Data File Name")
    glabels_columns = fields.Text(
        string="Columns",
        compute="_compute_glabels_columns",
        help="Columns read from the first line of the CSV data file.",
    )

    glabels_template = fields.Char(
        string="gLabels Template",
        help="Used only when no template file is uploaded: a template name "
        "from the gLabels database (e.g. 'Avery 5160') or a path to a "
        ".glabels file on the server.",
    )

    glabels_copies = fields.Integer(
        string="Copies per record",
        default=1,
        help="Number of label copies per record.",
    )

    glabels_crop_marks = fields.Boolean(
        string="Crop marks",
        default=False,
    )

    glabels_outlines = fields.Boolean(
        string="Label outlines",
        default=False,
    )

    @api.depends("glabels_csv_file")
    def _compute_glabels_columns(self):
        for report in self:
            report.glabels_columns = "\n".join(report._glabels_get_columns())

    def _glabels_get_columns(self):
        self.ensure_one()
        if not self.glabels_csv_file:
            return []
        return parse_glabels_columns(base64.b64decode(self.glabels_csv_file))

    @api.constrains("glabels_csv_file")
    def _check_glabels_csv_file(self):
        for report in self.filtered("glabels_csv_file"):
            try:
                columns = report._glabels_get_columns()
            except (UnicodeDecodeError, csv.Error) as exc:
                raise ValidationError(
                    _("The CSV data file cannot be read as UTF-8 CSV: %s", exc)
                ) from exc
            if not columns:
                raise ValidationError(
                    _("The first line of the CSV data file lists no columns.")
                )
            bad = [
                col
                for col in columns
                if any(ch in col for ch in GLABELS_FORBIDDEN_CHARS)
            ]
            if bad:
                raise ValidationError(
                    _(
                        "gLabels cannot use a field name containing ':' or '}'. "
                        "Rename these columns: %s",
                        ", ".join(bad),
                    )
                )

    @api.model
    def _render_glabels(self, report_ref, docids, data):
        report_sudo = self._get_report(report_ref)
        # Формата, създадена от човек в базата, няма свой модел
        # `report.<име>` — тогава работи общият двигател
        report_model = self.env.get(f"report.{report_sudo.report_name}")
        if report_model is None:
            report_model = self.env["report.report_glabels.abstract"]
        return (
            report_model.with_context(
                active_model=report_sudo.model,
                glabels_report_id=report_sudo.id,
            )
            .sudo(False)
            .create_glabels_report(docids, data)
        )

    @api.model
    def _get_report_from_name(self, report_name):
        res = super()._get_report_from_name(report_name)
        if res:
            return res
        report_obj = self.env["ir.actions.report"]
        conditions = [
            ("report_type", "in", ["glabels"]),
            ("report_name", "=", report_name),
        ]
        context = self.env["res.users"].context_get()
        return report_obj.with_context(**context).search(conditions, limit=1)
