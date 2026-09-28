# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)

try:
    import glabels
except ImportError:
    glabels = None


class PartnerGLabels(models.AbstractModel):
    """Адресни етикети — образец на отчет, строен в КОД.

    Няма качен шаблон и CSV: хартията идва от базата на gLabels (`Avery 5160`),
    колоните и текстът са тук. Данните минават през същия двигател, както при
    формите, създадени от човек.
    """

    _name = "report.report_glabels.partner_glabels"
    _inherit = "report.report_glabels.abstract"
    _description = "Partner gLabels Address Labels"

    def _glabels_columns(self, report):
        return ["name", "street", "city", "zip", "country_id.name"]

    def _glabels_build_layout(self, label):
        frame = label.frame
        fw = frame.w().to_mm()
        fh = frame.h().to_mm()
        margin = 2.0  # mm
        name_h = min(5.0, fh * 0.25)

        label.add_text(
            x=glabels.mm(margin),
            y=glabels.mm(margin),
            w=glabels.mm(fw - 2 * margin),
            h=glabels.mm(name_h),
            text="${name}",
            font_size=10.0,
        )
        label.add_text(
            x=glabels.mm(margin),
            y=glabels.mm(margin + name_h + 1.0),
            w=glabels.mm(fw - 2 * margin),
            h=glabels.mm(fh - 2 * margin - name_h - 1.0),
            text="${street}\n${city} ${zip}\n${country_id.name}",
            font_size=8.0,
        )
