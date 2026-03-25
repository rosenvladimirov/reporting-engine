# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import csv
import logging
import os
import tempfile

from odoo import models

_logger = logging.getLogger(__name__)

try:
    import glabels
except ImportError:
    glabels = None


class PartnerGLabels(models.AbstractModel):
    _name = "report.report_glabels.partner_glabels"
    _inherit = "report.report_glabels.abstract"
    _description = "Partner gLabels Address Labels"

    def generate_glabels_report(self, label_model, data, partners):
        """Generate address labels for partners.

        Creates a CSV merge source from partner data and configures the
        label model with text fields using merge substitution variables.
        """
        if not partners:
            return

        # Build label layout with merge fields
        frame = label_model.frame()
        fw = frame.w().to_mm()
        fh = frame.h().to_mm()
        margin = 2.0  # mm

        # Name line (bold, larger)
        self._add_text_label(
            label_model,
            "${name}",
            x=glabels.mm(margin),
            y=glabels.mm(margin),
            w=glabels.mm(fw - 2 * margin),
            h=glabels.mm(min(5.0, fh * 0.25)),
            font_size=10.0,
        )

        # Address block
        address_parts = []
        address_parts.append("${street}")
        address_parts.append("${city} ${zip}")
        address_parts.append("${country}")
        address_text = "\n".join(address_parts)

        self._add_text_label(
            label_model,
            address_text,
            x=glabels.mm(margin),
            y=glabels.mm(margin + min(6.0, fh * 0.3)),
            w=glabels.mm(fw - 2 * margin),
            h=glabels.mm(fh - 2 * margin - min(6.0, fh * 0.3)),
            font_size=8.0,
        )

        # Create CSV merge data from partner records
        fd, csv_path = tempfile.mkstemp(suffix=".csv")
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["name", "street", "city", "zip", "country"])
                for partner in partners:
                    writer.writerow([
                        partner.name or "",
                        partner.street or "",
                        partner.city or "",
                        partner.zip or "",
                        partner.country_id.name if partner.country_id else "",
                    ])

            # Set merge source
            merge = glabels.MergeFactory.create_merge("Text/CSV/Keys")
            if merge:
                merge.set_source(csv_path)
                label_model.set_merge(merge)
        except Exception:
            _logger.exception("Error creating CSV merge data")
            # Clean up on error
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            raise

        # Note: the CSV file will be cleaned up after rendering in
        # create_glabels_report. For now it needs to persist until
        # the renderer reads it.

    def create_glabels_report(self, docids, data):
        """Override to handle CSV temp file cleanup."""
        objs = self._get_objs_for_report(docids, data)
        template_name = self._get_glabels_template()
        copies = self.env.context.get("glabels_copies", 1)
        crop_marks = self.env.context.get("glabels_crop_marks", False)
        outlines = self.env.context.get("glabels_outlines", False)

        model = self._create_label_model(template_name)
        self.generate_glabels_report(model, data, objs)

        # Get merge source path for cleanup later
        merge = model.merge()
        csv_path = merge.source() if merge else None

        # Determine copies
        n_records = len(objs)
        total_items = n_records * copies if n_records > 0 else model.frame().n_labels()

        renderer = glabels.PageRenderer(model)
        renderer.set_n_copies(total_items)
        renderer.set_start_item(0)
        renderer.set_print_crop_marks(crop_marks)
        renderer.set_print_outlines(outlines)

        fd, tmpfile = tempfile.mkstemp(suffix=".pdf")
        try:
            os.close(fd)
            glabels.render_to_pdf(renderer, tmpfile)
            with open(tmpfile, "rb") as f:
                pdf_data = f.read()
        finally:
            os.unlink(tmpfile)
            # Clean up CSV temp file
            if csv_path and os.path.exists(csv_path):
                os.unlink(csv_path)

        return pdf_data, "glabels"
