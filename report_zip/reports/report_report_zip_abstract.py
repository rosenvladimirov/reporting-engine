# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import tempfile

from io import StringIO

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import zipfile
except ImportError:
    _logger.debug("Can not import csvwriter`.")


class ReportZIPAbstract(models.AbstractModel):
    _name = "report.report_zip.abstract"
    _description = "Abstract Model for zipped reports"

    def _get_objs_for_report(self, docids, data):
        """
        Returns objects for csv report.  From WebUI these
        are either as docids taken from context.active_ids or
        in the case of wizard are in data.  Manual calls may rely
        on regular context, setting docids, or setting data.

        :param docids: list of integers, typically provided by
            qwebactionmanager for regular Models.
        :param data: dictionary of data, if present typically provided
            by qwebactionmanager for TransientModels.
        :param ids: list of integers, provided by overrides.
        :return: recordset of active model for ids.
        """
        if docids:
            ids = docids
        elif data and "context" in data:
            ids = data["context"].get("active_ids", [])
        else:
            ids = self.env.context.get("active_ids", [])
        return self.env[self.env.context.get("active_model")].browse(ids)

    def create_zip_report(self, docids, data):
        objs = self._get_objs_for_report(docids, data)
        files_report = data.get("files_report", {})

        with tempfile.NamedTemporaryFile() as buf:
            with zipfile.ZipFile(
                buf, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=False
            ) as zip_buffer:
                for value in files_report.values():
                    for i, content in enumerate(value["file_content"]):
                        zip_buffer.writestr(
                            value["file_name"], content
                        )
            buf.seek(0)
            try:
                return buf.read(), "zip"
            except Exception as e:
                raise UserError(
                    _(_("An error occurred while reading the data. Please check the report's encoding settings."))
                ) from e

    def zip_report_options(self):
        """
        :return: dictionary of parameters. At least return 'fieldnames', but
        you can optionally return parameters that define the export format.
        Valid parameters include 'delimiter', 'quotechar', 'escapechar',
        'doublequote', 'skipinitialspace', 'lineterminator', 'quoting'.
        """
        return {"fieldnames": []}

    def generate_csv_report(self, file, data, objs):
        raise NotImplementedError()
