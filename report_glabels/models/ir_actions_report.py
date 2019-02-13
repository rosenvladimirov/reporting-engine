# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64

import logging
_logger = logging.getLogger(__name__)

class ReportAction(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[('glabels', 'Glabels'),('glabels_rows', 'Glabels (rows)')])
    glabels_template = fields.Binary(string="Glabels template")
    csv_template = fields.Binary(string="CSV data template")
    label_count = fields.Integer(string="Count",default=1,help="One if you want to fill the sheet with new records, the count of labels of the sheet to fill each sheet with one record")
    col_name = fields.Char(string="Column",help="(Glabels rows) the name of name column for use in gLabels")
    col_value = fields.Char(string="Column",help="(Glabels rows) the name of value column for use in gLabels")

    @api.model
    def render_glabels(self, docids, data):
        ctx = self._context.copy()
        report_model_name = 'report.%s' % self.report_name
        #report_model = self.env.get(report_model_name)
        report_model = self.env.get('report.report_glabels.abstract')
        #_logger.info("Report name %s:%s:%s:%s" % (report_model, report_model_name, docids, data))
        data.update({'template': base64.b64decode(self.glabels_template if self.glabels_template else ''),
                     'csv': base64.b64decode(self.csv_template if self.csv_template else ''),
                     'count': self.label_count,
                     'col_name': self.col_name,
                     'col_value': self.col_value,
                    })
        if report_model is None:
            raise UserError(_('%s model was not found' % report_model_name))
        if not ctx.get('active_model', False):
            ctx.update(dict(active_model=self.model))
        _logger.info("context %s:%s:%s" % (ctx, data, report_model))
        return report_model.with_context(ctx).glabels_report(docids, data)

    @api.model
    def render_glabels_rows(self, docids, data):
        report_model_name = 'report.%s' % self.report_name
        report_model = self.env.get('report_glabels.glabels_report_raw')
        _logger.info("Report name %s:%s:%s:%s" % (report_model, report_model_name, docids, data))
        data.update({'template': self.glabels_template if self.glabels_template else '',
                     'csv': self.csv_template if self.csv_template else '',
                     'count': self.label_count,
                     'col_name': self.col_name,
                     'col_value': self.col_value,
                    })
        if report_model is None:
            raise UserError(_('%s model was not found' % report_model_name))
        return report_model.with_context({
            'active_model': self.model
        }).glabels_report_rows(docids, data)

    @api.model
    def _get_report_from_name(self, report_name):
        res = super(ReportAction, self)._get_report_from_name(report_name)
        _logger.info("Glabel res %s" % res)
        if res:
            return res
        report_obj = self.env['ir.actions.report']
        qwebtypes = ['glabels', 'glabels_rows']
        conditions = [('report_type', 'in', qwebtypes),
                      ('report_name', '=', report_name)]
        context = self.env['res.users'].context_get()
        #_logger.info("Glabel %s" % conditions)
        return report_obj.with_context(context).search(conditions, limit=1)

    @api.multi
    def print_document_glabels(self, record_ids, data=None):
        """ Print a document, do not return the document file """
        ctx = self._context.copy()
        ctx.update(dict(must_skip_send_to_printer=True))
        #_logger.info("cotext %s" % ctx)
        report = self.env['ir.actions.report']._get_report_from_name(data['report_name'])
        document, doc_format = report.with_context(ctx).render_glabels(
                record_ids, data=data)
        #_logger.info("Check seg %s:%s" % (report,document))
        behaviour = report.behaviour()
        printer = behaviour.pop('printer', None)

        if not printer:
            raise exceptions.Warning(
                _('No printer configured to print this report.')
            )
        # TODO should we use doc_format instead of report_type
        return printer.print_document(self, document,
                                      doc_format=self.report_type,
                                      **behaviour)
