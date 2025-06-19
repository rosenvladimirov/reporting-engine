# Copyright 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import tempfile

from io import StringIO

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import pyzipper
except ImportError:
    raise UserError("Please install Pyzipper: pip install pyzipper")


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

    def zip_report(self, ir_report=None, docids=None, data=None):
        files_report = data.get("files_report", {})
        zip_params = {
            'compression': pyzipper.ZIP_DEFLATED,
            'allowZip64': False
        }

        if not files_report:
            objs = self._get_objs_for_report(docids, data)
            files_report = self.generate_zip_report(docids, data, objs) or {}

        if files_report.get('password'):
            password = files_report.get('password')
            del files_report['password']
            zip_params.update({
                'encryption': pyzipper.WZ_AES,
            })
        else:
            password = b''

        with tempfile.NamedTemporaryFile() as buf:
            with pyzipper.AESZipFile(
                buf,
                mode="w",
                **zip_params
            ) as zip_buffer:
                if password and password.strip():
                    zip_buffer.pwd = password
                for report_to_zip in ir_report.report_to_zip_ids:
                    files_report = {
                        report_to_zip.report_name.split(".")[-1]: {
                            'file_name': report_to_zip.print_report_name,
                            'file_content': report_to_zip.report_action(docids, data)
                        }
                    }
                    self._write_files_to_zip(files_report, zip_buffer)

                if not ir_report.report_to_zip_ids:
                    self._write_files_to_zip(files_report, zip_buffer)
            buf.seek(0)
            try:
                return buf.read(), "zip"
            except Exception as e:
                raise UserError(
                    _("An error occurred while generating the ZIP file. "
                      "Please check the report's encoding or file structure.")
                ) from e

    def _write_files_to_zip(self, files_report, zip_buffer):
        """Extracted function to handle writing files to a ZIP buffer."""
        encoding = self.env.context.get('encoding')
        for file_key, file_group in files_report.items():
            if file_key == 'password':
                continue
            for file_name, file_metadata in file_group.items():
                file_content = file_metadata.get('file_content')
                if isinstance(file_content, list):
                    file_content = file_content[0]
                if encoding:
                    file_content = file_content.encode(encoding, errors="ignore")
                zip_buffer.writestr(
                    file_metadata["file_name"],
                    file_content,
                )

    def generate_zip_report(self, file, data, objs):
        raise NotImplementedError()
