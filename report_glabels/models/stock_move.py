# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = "stock.move"

    def action_lots_glabel_print(self):
        self.ensure_one()
        lot_id = self._context.get('default_active_id', False)
        lots = self.move_line_ids.mapped('lot_id')
        ctx = self._context.copy()
        ctx['active_model'] = 'stock.production.lot'
        ctx['active_ids'] = lots.ids
        ctx['active_id'] = lot_id
        docids = self.env['stock.production.lot'].browse(lot_id and [lot_id] or lots.ids)
        _logger.info("Actions -- %s" % lots)
        return self.env['ir.actions.report']._get_report_from_name('lot_label').with_context(ctx).report_action(docids)
