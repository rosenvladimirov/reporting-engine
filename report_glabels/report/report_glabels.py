# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, tools, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from datetime import date

#import unicodecsv as csv
import csv
import os
import tempfile
import base64
import shutil


import logging
_logger = logging.getLogger(__name__)

class ReportGlabelsAbstract(models.AbstractModel):
    _name = 'report.report_glabels.abstract'

    @api.model
    def records_glabels_report(self, ids, data):
        ctx = self._context.copy()
        model = ctx['active_model']
        _logger.info("cotext %s" % ctx)
        if model == "stock.quant.package":
            records = []
            record_obj = self.env[model].browse(ids)
            for package in record_obj:
                #_logger.info("Package %s:%s" % (package, package.move_line_ids))
                records.append({'name': package.name,
                                'display_name': package.display_name,
                                'date': package.move_line_ids[0].date,
                                'location_name': package.location_id and package.location_id.name or '',
                                'location_barcode': package.location_id and package.location_id.barcode or '',
                                'owner_name': package.owner_id and package.owner_id.display_name or '',
                                'weight': package.weight,
                                'shipping_weight': package.shipping_weight,
                                })
            if records:
                return record_obj, records
        elif model == "stock.production.lot":
            records = []
            record_obj = self.env[model].browse(ids)
            for lot in record_obj:
                #_logger.info("Lot %s:%s" % (lot, lot.name))
                records.append({'name': "".join([lot.product_id.product_tmpl_id.label_prefix_code or '', lot.name]),
                                'last_letter': lot.name and lot.name[-1] or '',
                                'display_name': "+".join([lot.name or '', lot.ref or '', str(int(lot.product_qty or 0.0))]),
                                'date': lot.create_date,
                                'product_name': lot.product_id.name,
                                'product_barcode': lot.product_id.product_tmpl_id.barcode,
                                'product_default_code': lot.product_id.product_tmpl_id.default_code,
                                'product_electrical_properties_package': lot.product_id.product_tmpl_id.electrical_properties_package,
                                'product_electrical_properties_msl': lot.product_id.product_tmpl_id.electrical_properties_msl})
            if records:
                return record_obj, records
        elif model == "stock.move.line":
            records = []
            record_obj = self.env[model].browse(ids)
            for move in record_obj:
                #_logger.info("Move %s:%s" % (move, move.lot_id.name))
                records.append({'name': "".join([move.lot_id.product_id.product_tmpl_id.label_prefix_code or '', move.lot_id.name]),
                                'last_letter': move.lot_id and move.lot_id.name[-1] or '',
                                'display_name': "+".join([move.lot_id or '', move.lot_id or '', str(int(move.qty_done or 0.0))]),
                                'date': move.lot_id.create_date,
                                'product_name': move.lot_id.product_id.name,
                                'product_barcode': move.lot_id.product_id.product_tmpl_id.barcode,
                                'product_default_code': move.lot_id.product_id.product_tmpl_id.default_code,
                                'product_electrical_properties_package': move.lot_id.product_id.product_tmpl_id.electrical_properties_package,
                                'product_electrical_properties_msl': move.lot_id.product_id.product_tmpl_id.electrical_properties_msl})
            if records:
                return record_obj, records

        return self.env[model].browse(ids), self.env[model].search([('id', 'in' , ids)]).read([])

    def glabels_report(self, ids, data):
        ctx = self._context.copy()
        magic_fields = {}
        cr, uid, context = self._cr, self._uid, self._context

        #_logger.info("Get %s" % data)
        temp = tempfile.NamedTemporaryFile(mode='w+t',suffix='.csv')
        outfile = tempfile.NamedTemporaryFile(mode='w+b',suffix='.pdf')
        glabels = tempfile.NamedTemporaryFile(mode='w+b',suffix='.glabels')
        glabels.write(data.get('template'))
        glabels.seek(0)

        #pool = registry(cr.dbname)

        tax_obj = self.env['account.tax'].sudo()
        obj_precision = self.env['decimal.precision'].sudo()
        currency_obj = self.env['res.currency'].sudo()
        #user_obj = self.env['res.users']
        #user = user_obj.browse(uid)
        user = self.env.user

        #_logger.info("Objs %s:%s:%s:%s:%s:%s:%s" % (ids,ctx, data, tax_obj, obj_precision, currency_obj, user))
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        prec = obj_precision.precision_get('Product Price')

        magic_fields.update({'creator': user.name})
        magic_fields.update({'company': user.company_id.name})
        magic_fields.update({'date_now': date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)})

        fields = data.get('csv').decode('utf8').replace('"','').replace('\n','').replace('\r','').split(',')
        fields = [v if isinstance(v, (str,bytes)) else v for v in fields]

        ctx['lang'] = user.lang
        if user.company_id:
            magic_fields.update({'curr': user.company_id.currency_id.symbol})
        else:
            magic_fields.update({'curr': currency_obj.search([('rate', '=', 1.0)])[1]})
        for k, v in magic_fields.items():
            if k in fields:
                fields.remove(k)

        #context=ctx,
        record_obj, records = self.records_glabels_report(ids, data)
        labelwriter = None
        for p in records:
            _logger.info("items %s" % p)
            res = {}
            if not labelwriter:
                labelwriter = csv.DictWriter(temp, fields+[k for k,v in magic_fields.items()])
                _logger.info("label %s" % labelwriter)
                labelwriter.writeheader()
            for k, v in p.items():
                _logger.info("Items %s:%s" % (k, v))
                # set print counter ++
                if isinstance(v, (bool)):
                    if k == 'print_count':
                        record_obj.write({'print_count': v and False})
                        continue
                if isinstance(v, tuple):
                    if k+'/id' in fields:
                        res.update({k+'/id':str(v[0])})
                    if k+'/id/name' in fields:
                        res.update({k+'/id/name':_(v[1])})
                elif isinstance(v, str):
                    if k in fields:
                        res.update({k:_(k == 'website_url' and "%s%s"% (base_url,v) or v)})
                elif isinstance(v, (int, float)):
                    if k == 'print_count':
                        p.write({'print_count': v == 0 and 1 or v + 1})
                        continue
                    if k+'/vat' in fields:
                        res.update({k+'/vat':str("{0:.2f}".format(round(tax_obj.browse(p['taxes_id']).compute_all(v, 1)['total_included'], prec)))})
                    if k in fields:
                        res.update({k:str(v)})
                else:
                    if k in fields:
                        res.update({k:v})
            for mk,mv in magic_fields.items():
                #if mk in fields:
                if isinstance(mv, (int, float)):
                    res.update({mk:str(mv)})
                elif isinstance(mv, str):
                    res.update({mk:_(mv)})
            for c in range(data.get('count')):
                labelwriter.writerow({k:isinstance(v, str) and v or v or '' for k,v in res.items()})
        temp.seek(0)

        res = os.system("glabels-3-batch -o %s -i %s %s" % (outfile.name,temp.name,glabels.name))
        outfile.seek(0)
        pdf = outfile.read()

        #shutil.copy(temp.name, "/tmp/out.csv")
        #shutil.copy(glabels.name, "/tmp/out.glabels")
        outfile.close()
        temp.close()
        glabels.close()
        #_logger.info("Return %s-%s:%s" % (pdf, res, "glabels-3-batch -o %s -i %s %s" %(outfile.name,temp.name,glabels.name)))
        return (pdf,'pdf')

class ReportGlabels_rowsAbstract(models.AbstractModel):
    _name = 'report.report_glabels_rows.abstract'

    def report_glabels_rows(self, ids, data):
        cr, uid, context = self._cr, self._uid, self._context
        active_model = conext.get('active_model')
        temp = tempfile.NamedTemporaryFile(mode='w+t',suffix='.csv')
        outfile = tempfile.NamedTemporaryFile(mode='w+b',suffix='.pdf')
        glabels = tempfile.NamedTemporaryFile(mode='w+t',suffix='.glabels')
        glabels.write(base64.b64decode(data.get('template')))
        glabels.seek(0)

        col_name = data.get('col_name')
        col_value = data.get('col_value')

        #pool = registry(self._cr.dbname)
        labelwriter = csv.DictWriter(temp,[h[col_name] for h in self.env[self.model].read(self.env[self.model].search([]),[col_name])])
        labelwriter.writeheader()
        for c in range(self.count):
            #~ labelwriter.writerow({p[self.col_name]:isinstance(p[self.col_value], (str, unicode)) and p[self.col_value].encode('utf8') or p[self.col_value] or '' for p in pool.get(self.model).read(cr,uid,pool.get(self.model).search(cr,uid,[]),[self.col_name,self.col_value])])})
            labelwriter.writerow({p[col_name]: str(p[col_value]) if not str(p[col_value]) == '0.0' else '' for p in self.env[active_model].read(self.env[active_model].search([]),[col_name,col_value])})
        temp.seek(0)
        res = os.system("glabels-3-batch -o %s -l -C -i %s %s" % (outfile.name,temp.name,glabels.name))
        outfile.seek(0)
        pdf = outfile.read()
        outfile.close()
        temp.close()
        glabels.close()
        return (pdf,'pdf')
