# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import tempfile
import os

from odoo import models

_logger = logging.getLogger(__name__)

try:
    import glabels
except ImportError:
    _logger.debug("Cannot import glabels. Install with: pip install glabels")
    glabels = None


class ReportGLabelsAbstract(models.AbstractModel):
    _name = "report.report_glabels.abstract"
    _description = "Abstract gLabels Report"

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

    def _get_glabels_template(self):
        """Get the gLabels template name or path from context."""
        return self.env.context.get("glabels_template", "")

    def create_glabels_report(self, docids, data):
        """Create a PDF label report using gLabels.

        This method orchestrates the label generation:
        1. Gets the records to report on
        2. Calls generate_glabels_report() to populate the label model
        3. Renders to PDF

        Returns:
            tuple: (pdf_bytes, "glabels")
        """
        objs = self._get_objs_for_report(docids, data)

        template_name = self._get_glabels_template()
        copies = self.env.context.get("glabels_copies", 1)
        crop_marks = self.env.context.get("glabels_crop_marks", False)
        outlines = self.env.context.get("glabels_outlines", False)

        # Create the glabels model
        model = self._create_label_model(template_name)

        # Let the concrete implementation populate the label
        self.generate_glabels_report(model, data, objs)

        # Determine how many copies we need
        n_labels = model.frame().n_labels()
        total_items = len(objs) * copies
        if total_items == 0:
            total_items = n_labels  # Fill one sheet

        # Render to PDF
        renderer = glabels.PageRenderer(model)
        renderer.set_n_copies(total_items)
        renderer.set_start_item(0)
        renderer.set_print_crop_marks(crop_marks)
        renderer.set_print_outlines(outlines)

        # Write to temp file and read back
        fd, tmpfile = tempfile.mkstemp(suffix=".pdf")
        try:
            os.close(fd)
            glabels.render_to_pdf(renderer, tmpfile)
            with open(tmpfile, "rb") as f:
                pdf_data = f.read()
        finally:
            os.unlink(tmpfile)

        return pdf_data, "glabels"

    def _create_label_model(self, template_name):
        """Create a gLabels Model with the specified template.

        Args:
            template_name: Either a template name from the gLabels database
                (e.g. 'Avery 5160') or a path to a .glabels file.

        Returns:
            A glabels.Model instance.
        """
        if template_name and os.path.isfile(template_name):
            # Load from .glabels file
            return glabels.XmlLabelParser.read_file(template_name)

        # Create from template database
        model = glabels.Model()

        if template_name:
            tmpl = glabels.Db.lookup_template_from_name(template_name)
            if tmpl.is_null():
                # Try brand + part split
                parts = template_name.split(None, 1)
                if len(parts) == 2:
                    tmpl = glabels.Db.lookup_template_from_brand_part(
                        parts[0], parts[1]
                    )
            if not tmpl.is_null():
                model.set_tmplate(tmpl)
            else:
                _logger.warning(
                    "gLabels template '%s' not found, using first available",
                    template_name,
                )
                templates = glabels.Db.templates()
                if templates:
                    model.set_tmplate(templates[0])
        else:
            # No template specified, use first available
            templates = glabels.Db.templates()
            if templates:
                model.set_tmplate(templates[0])

        return model

    def _add_text_label(self, model, text, x=None, y=None, w=None, h=None,
                        font_family="Sans", font_size=10.0):
        """Helper: add a text object to the label model.

        If position/size not given, uses sensible defaults based on the frame.
        """
        frame = model.frame()
        if x is None:
            x = glabels.mm(2)
        if y is None:
            y = glabels.mm(2)
        if w is None:
            w = glabels.Distance(frame.w().to_pt() - glabels.mm(4).to_pt())
        if h is None:
            h = glabels.Distance(frame.h().to_pt() - glabels.mm(4).to_pt())

        obj = glabels.ModelTextObject()
        obj.set_x0(x)
        obj.set_y0(y)
        obj.set_w(w)
        obj.set_h(h)
        obj.set_text(text)
        obj.set_font_family(font_family)
        obj.set_font_size(font_size)
        model.add_object(obj)
        return obj

    def generate_glabels_report(self, label_model, data, objs):
        """Override this method to populate the gLabels model with content.

        This is the main extension point for concrete report implementations.
        Use the label_model to add text, barcodes, images, etc. and configure
        merge data from the Odoo records.

        Args:
            label_model: A glabels.Model instance with template already set.
            data: Dictionary of report data/options.
            objs: Recordset of Odoo records to generate labels for.
        """
        raise NotImplementedError()
