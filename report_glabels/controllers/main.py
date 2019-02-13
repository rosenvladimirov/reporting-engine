# Copyright (C) 2017 Creu Blanca
# License AGPL-3.0 or later (https://www.gnuorg/licenses/agpl.html).

from odoo.addons.web.controllers import main as report
from odoo.http import route, request

import json

import logging
_logger = logging.getLogger(__name__)

class ReportController(report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        _logger.info("Report %s:%s:%s:%s" % (reportname, docids, converter, data))
        if converter in ('glabels', 'glabels_raws'):
            report = request.env['ir.actions.report']._get_report_from_name(reportname)
            context = dict(request.env.context)

            if docids:
                docids = [int(i) for i in docids.split(',')]
            if data.get('options'):
                data.update(json.loads(data.pop('options')))
            if data.get('context'):
                # Ignore 'lang' here, because the context in data is the one
                # from the webclient *but* if the user explicitely wants to
                # change the lang, this mechanism overwrites it.
                data['context'] = json.loads(data['context'])
                if data['context'].get('lang'):
                    del data['context']['lang']
                context.update(data['context'])
            if converter == 'glabels':
                pdf = report.with_context(context).render_glabels(docids, data=data)[0]
            elif converter == 'glabels_raws':
                pdf = report.with_context(context).render_glabels_raws(docids, data=data)[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf)), ('Content-Disposition', 'attachment; filename=' + reportname + '.pdf')]
            #_logger.info("Pdf %s" % pdf)
            return request.make_response(pdf, headers=pdfhttpheaders)
        return super(ReportController, self).report_routes(
            reportname, docids, converter, **data
        )
