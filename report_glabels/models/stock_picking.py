# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class Picking(models.Model):
    _inherit = "stock.picking"

    @api.depends('move_lines')
    def _has_tracking(self):
        for picking in self:
            picking.has_tracking = len([x.has_tracking for x in picking.move_lines if x.has_tracking != 'none']) > 0

    has_tracking = fields.Boolean(compute=_has_tracking, string='Product with Tracking')


    def action_package_glabel_print(self):
        self.ensure_one()
        packages = self.move_line_ids.mapped('result_package_id')
        ctx = self._context.copy()
        ctx['active_model'] = 'stock.quant.package'
        ctx['active_ids'] = packages.ids
        docids = self.env['stock.quant.package'].browse(packages.ids)
        if docids:
        #_logger.info("Actions %s" % self.env['ir.actions.report']._get_report_from_name('package_label_60_30'))
            return self.env['ir.actions.report']._get_report_from_name('package_label').with_context(ctx).report_action(docids)
        else:
            return False

    def action_lots_glabel_print(self):
        self.ensure_one()
        lots = self.move_line_ids.mapped('lot_id')
        ctx = self._context.copy()
        ctx['active_model'] = 'stock.production.lot'
        ctx['active_ids'] = lots.ids
        docids = self.env['stock.production.lot'].browse(lots.ids)
        #_logger.info("Actions ++ %s" % self.env['ir.actions.report']._get_report_from_name('lot_label_60_30'))
        return self.env['ir.actions.report']._get_report_from_name('lot_label').with_context(ctx).report_action(docids)

    def action_move_glabel_print(self):
        self.ensure_one()
        move_id = self._context.get('default_active_id', False)
        ctx = self._context.copy()
        ctx['active_model'] = 'stock.move.line'
        ctx['active_ids'] = [x.id for x in self.move_line_ids]
        ctx['active_id'] = move_id
        docids = self.move_line_ids
        #_logger.info("Actions ++ %s:%" % (self.move_line_ids, self.env['ir.actions.report']._get_report_from_name('lot_label_60_30')))
        return self.env['ir.actions.report']._get_report_from_name('lot_label').with_context(ctx).report_action(docids)

    #@api.multi
    #def write(self, vals):
    #    res = super(Picking, self).write(vals)
    #    for record in self:
    #        all_done = len([x.id for x in record.move_line_ids]) > 0 and len([x.id for x in record.move_line_ids if x.qty_done > 0]) == len([x.id for x in record.move_line_ids])
    #        if record.state == 'assigned' and all_done:
    #            record.action_move_glabel_print()
    #        _logger.info("What return %s:%s" % (res, [x.id for x in record.move_line_ids if x.qty_done > 0]))
    #    return res
