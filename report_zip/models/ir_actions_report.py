# Copyright (C) 2014-2015  Grupo ESOC <www.grupoesoc.es>
# License AGPL-3.0 or later (https://www.gnuorg/licenses/agpl.html).

from odoo import api, fields, models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(
        selection_add=[("zip", "Zipped report")], ondelete={"zip": "set default"}
    )
    report_to_zip_ids = fields.One2many("ir.actions.report", 'parent_id', string="Reports to zip")
    parent_id = fields.Many2one("ir.actions.report", string="Parent report", index=True, ondelete="cascade")

    @api.model
    def _render_zip(self, report_ref, res_ids, data=None):
        """
        Call `generate_report` method of report abstract class
        `report.<report technical name>` or of standard class for XML report
        rendering - `report.report_xml.abstract`

        Args:
         * docids(list) - IDs of instances for those report will be generated
         * data(dict, None) - variables for report rendering

        Returns:
         * str - result content of report
         * str - type of result content
        """
        report = self._get_report(report_ref)
        report_model = self.env.get(
            f"report.{report.report_name}", self.env["report.report_zip.abstract"]
        )
        return report_model.zip_report(
            ir_report=report,  # will be used to get settings of report
            docids=res_ids,
            data=data or {},
        )
