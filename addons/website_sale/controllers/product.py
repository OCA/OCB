# -*- coding: utf-8 -*-

import werkzeug

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import login_redirect

from .utils import QueryURL
from .utils import get_attrib_params
from .mixin import Mixin


class ProductController(http.Controller, Mixin):

    @http.route(['/shop/product/comment/<int:product_template_id>'],
                type='http', auth="public", methods=['POST'], website=True)
    def product_comment(self, product_template_id, **post):
        if not request.session.uid:
            return login_redirect()
        cr, uid, context = request.cr, request.uid, request.context
        if post.get('comment'):
            request.registry['product.template'].message_post(
                cr, uid, product_template_id,
                body=post.get('comment'),
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubscribe=True))
        return werkzeug.utils.redirect(
            request.httprequest.referrer + "#comments")

    @http.route(['/shop/product/<model("product.template"):product>'],
                type='http', auth="public", website=True)
    def product(self, product, category='', search='', **kwargs):
        cr, uid, context, pool = \
            request.cr, request.uid, request.context, request.registry
        category_obj = pool['product.public.category']
        template_obj = pool['product.template']

        context.update(active_id=product.id)

        if category:
            category = category_obj.browse(cr, uid, int(category),
                                           context=context)

        attrib_list, attrib_values, attrib_set = get_attrib_params()

        keep = QueryURL('/shop',
                        category=category and category.id,
                        search=search,
                        attrib=attrib_list)

        pricelist = self.get_pricelist()
        price_type = pool.get('product.price.type')
        from_currency = price_type._get_field_currency(cr, uid, 'list_price',
                                                       context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(
            cr, uid, from_currency, to_currency, price, context=context)

        if not context.get('pricelist'):
            context['pricelist'] = int(self.get_pricelist())
            product = template_obj.browse(cr, uid, int(product),
                                          context=context)

        values = {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'compute_currency': compute_currency,
            'attrib_set': attrib_set,
            'keep': keep,
            'categories': self.get_categories(),
            'main_object': product,
            'product': product,
            'get_attribute_value_ids': self.get_attribute_value_ids,
            'variant_values': {}
        }
        return request.website.render("website_sale.product", values)

#     @http.route(['/shop/pproduct/<model("product.product"):product>'],
#                 type='http', auth="public", website=True)
#     def product_product(self, product, category='', search='', **kwargs):
#         cr, uid, context, pool = \
#             request.cr, request.uid, request.context, request.registry
#         category_obj = pool['product.public.category']
#         product_obj = pool['product.product']

#         context.update(active_id=product.id)

#         if category:
#             category = category_obj.browse(cr, uid, int(category),
#                                            context=context)

#         attrib_list, attrib_values, attrib_set = get_attrib_params()

#         keep = QueryURL('/shop',
#                         category=category and category.id,
#                         search=search,
#                         attrib=attrib_list)

#         pricelist = self.get_pricelist()
#         price_type = pool.get('product.price.type')
#         from_currency = price_type._get_field_currency(cr, uid, 'list_price',
#                                                        context)
#         to_currency = pricelist.currency_id
#         compute_currency = lambda price: pool['res.currency']._compute(
#             cr, uid, from_currency, to_currency, price, context=context)

#         if not context.get('pricelist'):
#             context['pricelist'] = int(self.get_pricelist())
#             product = product_obj.browse(cr, uid, int(product),
#                                          context=context)
#         variant_values = {attr.attribute_id.id: attr.id
#                           for attr in product.attribute_value_ids}

#         values = {
#             'search': search,
#             'category': category,
#             'pricelist': pricelist,
#             'attrib_values': attrib_values,
#             'compute_currency': compute_currency,
#             'attrib_set': attrib_set,
#             'keep': keep,
#             'categories': self.get_categories(),
#             'main_object': product,
#             'product': product,
#             'get_attribute_value_ids': self.get_attribute_value_ids,
#             'variant_values': variant_values
#         }
#         return request.website.render("website_sale.product", values)


# # vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
