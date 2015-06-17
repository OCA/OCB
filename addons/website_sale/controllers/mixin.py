# -*- coding: utf-8 -*-

from openerp.http import request

from .utils import PPG
from .utils import get_pricelist


class Mixin(object):

    def get_pricelist(self):
        return get_pricelist()

    def get_attribute_value_ids(self, product):
        cr, uid, context, pool = \
            request.cr, request.uid, request.context, request.registry
        currency_obj = pool['res.currency']
        attribute_value_ids = []
        if request.website.pricelist_id.id != context['pricelist']:
            website_currency_id = request.website.currency_id.id
            currency_id = self.get_pricelist().currency_id.id
            for p in product.product_variant_ids:
                price = currency_obj.compute(cr, uid,
                                             website_currency_id,
                                             currency_id, p.lst_price)
                attribute_value_ids.append(
                    [p.id, [v.id for v in p.attribute_value_ids
                            if len(v.attribute_id.value_ids) > 1],
                     p.price, price])
        else:
            attribute_value_ids = [
                [p.id,
                 [v.id for v in p.attribute_value_ids
                  if len(v.attribute_id.value_ids) > 1],
                 p.price, p.lst_price]
                for p in product.product_variant_ids]

        return attribute_value_ids

    def get_styles(self):
        cr, uid, context, pool = request.cr, request.uid, \
            request.context, request.registry
        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [],
                                     context=context)
        styles = style_obj.browse(cr, uid, style_ids,
                                  context=context)
        return styles

    def get_categories(self):
        cr, uid, context, pool = request.cr, request.uid, \
            request.context, request.registry
        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid,
                                           [('parent_id', '=', False)],
                                           context=context)
        categs = category_obj.browse(cr, uid, category_ids,
                                     context=context)
        return categs

    def get_products(self, domain, limit=PPG, offset=0, order=None, **kw):
        cr, uid, context, pool = request.cr, request.uid, \
            request.context, request.registry
        order = order or ', '.join([
            'website_published desc',
            'website_featured desc',
            'website_sequence desc',
        ])
#        product_obj = pool.get('product.template')
        product_obj = pool.get('product.product')
        product_ids = product_obj.search(
            cr, uid, domain,
            limit=limit, offset=offset,
            order=order,
            context=context)
        products = product_obj.browse(cr, uid, product_ids, context=context)
        return products

    def get_attributes(self):
        cr, uid, context, pool = request.cr, request.uid, \
            request.context, request.registry
        attributes_obj = pool['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [],
                                               context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids,
                                           context=context)
        return attributes


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
