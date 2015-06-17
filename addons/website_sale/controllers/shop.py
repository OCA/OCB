# -*- coding: utf-8 -*-
import werkzeug

from openerp import http
from openerp.http import request
from openerp.addons.website.models.website import slug

from .mixin import Mixin
from .utils import table_compute
from .utils import QueryURL
from .utils import PPG
from .utils import PPR
from .utils import get_attrib_params


class ShopController(http.Controller, Mixin):

    products_as_table = True
    ppg = PPG
    ppr = PPR
    shop_template_name = "website_sale.products"

    def get_shop_domain(self, search=None, category=None):
        domain = request.website.sale_product_domain()
        if search:
            for srch in search.split(" "):
                domain += [
                    '|', '|', '|',
                    ('name', 'ilike', srch),
                    ('description', 'ilike', srch),
                    ('description_sale', 'ilike', srch),
                    ('product_variant_ids.default_code', 'ilike', srch)
                ]
        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]
        return domain

    def get_attrib_stuff(self):
        domain = []
        attrib_list, attrib_values, attrib_set = get_attrib_params()

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]
        return attrib_list, attrib_values, attrib_set, domain

    def prepare_values(self, **kw):
        # do whatver you want here
        return kw

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '/shop/category/<model("product.public.category"):category>',
        '/shop/category/<model("product.public.category"):category>/page/<int:page>'
    ], type='http', auth="public", website=True)
    def shop(self, page=0, category=None, search='', **post):
        cr, uid, context, pool = request.cr, request.uid, \
            request.context, request.registry

        domain = self.get_shop_domain(search=search,
                                      category=category)

        attrib_list, attrib_values, attrib_set, extra_domain = \
            self.get_attrib_stuff()

        domain += extra_domain

        keep = QueryURL('/shop',
                        category=category and int(category),
                        search=search, attrib=attrib_list)

        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist_model = pool.get('product.pricelist')
            pricelist = pricelist_model.browse(cr, uid, context['pricelist'],
                                               context)

        url = "/shop"
        product_obj = pool.get('product.template')
        product_count = product_obj.search_count(cr, uid, domain,
                                                 context=context)

        if search:
            post["search"] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid,
                                                              int(category),
                                                              context=context)
            url = "/shop/category/%s" % slug(category)

        pager = request.website.pager(url=url, total=product_count,
                                      page=page, step=self.ppg,
                                      scope=7, url_args=post)
        products = self.get_products(domain,
                                     limit=self.ppg,
                                     offset=pager['offset'],
                                     **{'category':category,
                                        'page': page,
                                        'post': post})

        attributes = self.get_attributes()
        price_type_model = pool.get('product.price.type')
        from_currency = price_type_model._get_field_currency(cr, uid,
                                                             'list_price',
                                                             context)
        to_currency = pricelist.currency_id

        compute_currency = lambda price: pool['res.currency']._compute(
            cr, uid, from_currency, to_currency, price, context=context)
        style_in_product = lambda style, product: style.id in [
            s.id for s in product.website_style_ids]
        attrib_encode = lambda attribs: werkzeug.url_encode([('attrib', i)
                                                             for i in attribs])
        values = {
            'search': search,
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'pager': pager,
            'pricelist': pricelist,
            'products': products,
            'styles': self.get_styles(),
            'categories': self.get_categories(),
            'attributes': attributes,
            'compute_currency': compute_currency,
            'keep': keep,
            'style_in_product': style_in_product,
            'attrib_encode': attrib_encode,
            # add some info that can be used
            # into `prepare_values` to do some extra stuff
            '_domain': domain,
        }
        if self.products_as_table:
            values.update({
                'bins': table_compute().process(products),
                'rows': self.ppr,
            })
        values = self.prepare_values(**values)
        return request.website.render(self.shop_template_name, values)


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
