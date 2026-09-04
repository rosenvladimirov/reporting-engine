# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)


class ReportAction(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(
        selection_add=[("glabels", "gLabels (PDF labels)")],
        ondelete={"glabels": "set default"},
    )

    glabels_template = fields.Char(
        string="gLabels Template",
        help="Path to the .glabels template file, or a template name "
        "from the gLabels database (e.g. 'Avery 5160').",
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

    @api.model
    def _render_glabels(self, report_ref, docids, data):
        report_sudo = self._get_report(report_ref)
        report_model_name = f"report.{report_sudo.report_name}"
        report_model = self.env[report_model_name]
        return (
            report_model.with_context(
                active_model=report_sudo.model,
                glabels_template=report_sudo.glabels_template,
                glabels_copies=report_sudo.glabels_copies or 1,
                glabels_crop_marks=report_sudo.glabels_crop_marks,
                glabels_outlines=report_sudo.glabels_outlines,
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
