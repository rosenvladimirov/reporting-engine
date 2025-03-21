# Copyright (C) 2025 Rosen Vladimirov
# License AGPL-3.0 or later (https://www.gnuorg/licenses/agpl.html).

import json
import logging

from werkzeug.exceptions import InternalServerError
from werkzeug.urls import url_decode

from odoo.http import (
    content_disposition,
    request,
    route,
    serialize_exception as _serialize_exception,
)
from odoo.tools import html_escape
from odoo.tools.safe_eval import safe_eval, time

from odoo.addons.web.controllers import report

_logger = logging.getLogger(__name__)


class ReportController(report.ReportController):
    @route()
    def report_routes(self, report_name, docids=None, converter=None, **data):
        if converter == "zip":
            zip_report = request.env["ir.actions.report"]._get_report_from_name(report_name)
            context = dict(request.env.context)
            if docids:
                docids = list(map(lambda x: int(x), docids.split(",")))
            if data.get("options"):
                data.update(json.loads(data.pop("options")))
            if data.get("context"):
                # Ignore 'lang' here, because the context in data is the one
                # from the webclient *but* if the user explicitely wants to
                # change the lang, this mechanism overwrites it.
                data["context"] = json.loads(data["context"])
                if data["context"].get("lang"):
                    del data["context"]["lang"]
                context.update(data["context"])
            zip_file = zip_report.with_context(**context)._render_zip(
                report_name, docids, data=data
            )[0]
            zip_http_headers = [
                ("Content-Type", "application/zip"),
                ("Content-Length", len(zip_file)),
            ]
            return request.make_response(zip_file, headers=zip_http_headers)
        return super(ReportController, self).report_routes(
            report_name, docids, converter, **data
        )

    @route()
    def report_download(self, data, context=None):
        request_content = json.loads(data)
        url, report_type = request_content[0], request_content[1]
        report_name = ""
        try:
            if report_type == "zip":
                report_name = url.split("/report/zip/")[1].split("?")[0]
                docids = None
                if "/" in report_name:
                    report_name, docids = report_name.split("/")
                if docids:
                    # Generic report:
                    response = self.report_routes(
                        report_name, docids=docids, converter="zip", context=context
                    )
                else:
                    # Particular report:
                    data = dict(
                        url_decode(url.split("?")[1]).items()
                    )  # decoding the args represented in JSON
                    if "context" in data:
                        context, data_context = json.loads(context or "{}"), json.loads(
                            data.pop("context")
                        )
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(
                        report_name, converter="zip", context=context, **data
                    )

                zip_report = request.env["ir.actions.report"]._get_report_from_name(
                    report_name
                )
                filename = "%s.%s" % (zip_report.name, "zip")

                if docids:
                    obj = request.env[zip_report.model].browse(list(map(lambda x: int(x), docids.split(","))))
                    if zip_report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(
                            zip_report.print_report_name, {"object": obj, "time": time}
                        )
                        filename = "%s.%s" % (report_name, "zip")
                response.headers.add(
                    "Content-Disposition", content_disposition(filename)
                )
                return response
            else:
                return super(ReportController, self).report_download(data, context)
        except Exception as e:
            _logger.exception("Error while generating zip compressed report %s", report_name)
            se = _serialize_exception(e)
            error = {"code": 200, "message": "Odoo Server Error", "data": se}
            res = request.make_response(html_escape(json.dumps(error)))
            raise InternalServerError(response=res) from e
