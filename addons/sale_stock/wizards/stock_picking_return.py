# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, move):
        result = super(ReturnPicking, self)._prepare_stock_return_picking_line_vals_from_move(move)
        result['to_refund_so'] = True
        return result
