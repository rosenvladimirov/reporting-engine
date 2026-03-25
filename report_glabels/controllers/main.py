# Copyright 2025 Rosen
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import json
import logging

from werkzeug.urls import url_decode

from odoo.http import (
    content_disposition,
    request,
    route,
)
from odoo.http import (
    serialize_exception as _serialize_exception,
)
from odoo.tools import html_escape
from odoo.tools.safe_eval import safe_eval, time

from odoo.addons.web.controllers.report import ReportController

_logger = logging.getLogger(__name__)


class ReportController(ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter == "glabels":
            report = request.env["ir.actions.report"]._get_report_from_name(
                reportname
            )
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(",")]
            if data.get("options"):
                data.update(json.loads(data.pop("options")))
            if data.get("context"):
                data["context"] = json.loads(data["context"])
                context.update(data["context"])
            pdf = report.with_context(**context)._render_glabels(
                reportname, docids, data=data
            )[0]
            pdfhttpheaders = [
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
            ]
            return request.make_response(pdf, headers=pdfhttpheaders)
        return super().report_routes(
            reportname, docids=docids, converter=converter, **data
        )

    @route()
    def report_download(self, data, context=None, token=None):
        requestcontent = json.loads(data)
        url, report_type = requestcontent[0], requestcontent[1]
        if report_type == "glabels":
            try:
                reportname = url.split("/report/glabels/")[1].split("?")[0]
                docids = None
                if "/" in reportname:
                    reportname, docids = reportname.split("/")
                if docids:
                    response = self.report_routes(
                        reportname,
                        docids=docids,
                        converter="glabels",
                        context=context,
                    )
                else:
                    data = dict(url_decode(url.split("?")[1]).items())
                    if "context" in data:
                        context, data_context = (
                            json.loads(context or "{}"),
                            json.loads(data.pop("context")),
                        )
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(
                        reportname, converter="glabels", context=context, **data
                    )

                report = request.env[
                    "ir.actions.report"
                ]._get_report_from_name(reportname)
                filename = f"{report.name}.pdf"

                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(
                            report.print_report_name,
                            {"object": obj, "time": time},
                        )
                        filename = f"{report_name}.pdf"
                if not response.headers.get("Content-Disposition"):
                    response.headers.add(
                        "Content-Disposition", content_disposition(filename)
                    )
                return response
            except Exception as e:
                _logger.exception(
                    "Error while generating gLabels report %s", reportname
                )
                se = _serialize_exception(e)
                error = {
                    "code": 200,
                    "message": "Odoo Server Error",
                    "data": se,
                }
                return request.make_response(html_escape(json.dumps(error)))
        else:
            return super().report_download(data, context=context, token=token)
