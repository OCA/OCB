# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, exceptions, models


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to the online quote for
        portal users that have access to a confirmed order. """
        # TDE note: read access on sale order to portal users granted to followed sale orders
        self.ensure_one()
        if self.state == 'cancel' or (self.state == 'draft' and not self.env.context.get('mark_so_as_sent')):
            return super(sale_order, self).get_access_action()
        if self.env.user.share or self.env.context.get('force_website'):
            try:
                self.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/orders/%s' % self.id,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(sale_order, self).get_access_action()
