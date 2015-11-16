# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv


class product_pricelist(osv.osv):
    _inherit = 'product.pricelist'

    _columns = {
        'visible_discount': fields.boolean('Visible Discount'),
    }
    _defaults = {
         'visible_discount': True,
    }


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
                          uom=False, qty_uos=0, uos=False, name='',
                          partner_id=False, lang=False, update_tax=True,
                          date_order=False, packaging=False,
                          fiscal_position=False, flag=False, context=None):

        def get_real_price_currency(res_dict, product_id, qty, uom,
                                    pricelist):
            """Retrieve the price before applying the pricelist"""
            pricelist_obj = self.pool.get('product.pricelist')
            item_obj = self.pool.get('product.pricelist.item')
            price_type_obj = self.pool.get('product.price.type')
            product_obj = self.pool.get('product.product')
            uom_obj = self.pool.get('product.uom')

            field_name = 'list_price'
            currency_id = None

            rule_id = res_dict.get(pricelist, [False, False])[1]
            if not rule_id:
                # no rule matched on pricelist, take price from product record
                product = product_obj.browse(cr, uid, product_id, context)
                price = getattr(product, field_name)
            else:
                # got a pricelist rule, discriminate according to rule's
                # base_price
                item_base = item_obj.read(cr, uid,
                                          [rule_id], ['base'])[0]['base']
                if item_base > 0:
                    price_type = price_type_obj.browse(cr, uid, item_base)
                    field_name = price_type.field
                    currency_id = price_type.currency_id
                    product = product_obj.browse(cr, uid, product_id, context)
                    price = getattr(product, field_name)
                else:
                    assert item_base == -1, "item_base should be -1"
                    # based on other pricelist
                    values = item_obj.read(cr, uid, [rule_id],
                                           ['base_pricelist_id'])
                    bpl_id = values[0]['base_pricelist_id']
                    base_pl = pricelist_obj.browse(cr, uid, [bpl_id],
                                                   context=context)[0]
                    rule_match = base_pl.price_get(product_id, qty)
                    assert len(rule_match) == 1, "exactly one rule matched"
                    price = rule_match.values()[0]

            if not currency_id:
                currency_id = product.company_id.currency_id.id
            factor = 1.0
            if uom and uom != product.uom_id.id:
                # the unit price is in a different uom
                factor = uom_obj._compute_qty(cr, uid, uom,
                                              1.0, product.uom_id.id)
            return price * factor, currency_id

        def get_real_price(res_dict, product_id, qty, uom, pricelist):
            return get_real_price_currency(res_dict, product_id,
                                           qty, uom, pricelist)[0]

        res = super(sale_order_line,
                    self).product_id_change(cr, uid, ids, pricelist,
                                            product, qty, uom, qty_uos, uos,
                                            name, partner_id, lang,
                                            update_tax, date_order,
                                            packaging=packaging,
                                            fiscal_position=fiscal_position,
                                            flag=flag, context=context)
        # determine discount
        result = res['value']
        result['discount'] = 0.0

        context = {'lang': lang, 'partner_id': partner_id}
        pricelist_obj = self.pool.get('product.pricelist')
        product_obj = self.pool.get('product.product')
        users_obj = self.pool.get('res.users')
        currency_obj = self.pool.get('res.currency')

        if (product and pricelist and
            users_obj.has_group(cr, uid,
                                'sale.group_discount_per_so_line')):
            # discriminate unset price_unit from 0.0 price unit
            if result.get('price_unit', False) is not False:
                price = result['price_unit']
            else:
                return res
            uom = result.get('product_uom', uom)
            product = product_obj.browse(cr, uid, product, context)
            pricelist_ctx = dict(context, uom=uom, date=date_order)
            list_price = pricelist_obj.price_rule_get(cr, uid, [pricelist],
                                                      product.id, qty or 1.0,
                                                      partner_id,
                                                      context=pricelist_ctx)

            so_pricelist = pricelist_obj.browse(cr, uid, pricelist,
                                                context=context)

            new_list_price, currency_id = get_real_price_currency(list_price,
                                                                  product.id,
                                                                  qty, uom,
                                                                  pricelist)

            if (so_pricelist.visible_discount and
                    list_price[pricelist][0] != 0 and new_list_price != 0):
                if (product.company_id and
                    so_pricelist.currency_id.id !=
                        product.company_id.currency_id.id):
                    # new_list_price is in company's currency while price
                    # in pricelist currency
                    ctx = context.copy()
                    ctx['date'] = date_order
                    pl_currency_id = so_pricelist.currency_id.id
                    new_list_price = currency_obj.compute(cr, uid,
                                                          currency_id.id,
                                                          pl_currency_id,
                                                          new_list_price,
                                                          context=ctx)
                if new_list_price == 0.0:
                    discount = 100 if price else 0.0
                else:
                    discount = (new_list_price - price) / new_list_price * 100

                if discount > 0:
                    result['price_unit'] = new_list_price
                    result['discount'] = discount
        return res
