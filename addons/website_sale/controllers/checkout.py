# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.tools.translate import _

from .mixin import Mixin
from .utils import validate_email
from .utils import HAS_PyDNS
from .utils import validate_phonenumber


FIELDS_LABELS = {
    'name': _(u'Name'),
    'phone': _(u'Phone'),
    'email': _(u'Email'),
    'street2': _(u'Street'),
    'city': _(u'City'),
    'country_id': _(u'Country'),
    'zip': _(u'Zip / Postal code'),
    'street': _(u'Company Name'),
    'state_id': _(u'State / Province'),
    'vat': _(u'VAT Number'),
    # shipping
    'shipping_name': _(u'Name (Shipping)'),
    'shipping_phone': _(u'Phone'),
    'shipping_email': _(u'Email'),
    'shipping_street': _(u'Street'),
    'shipping_city': _(u'City'),
    'shipping_country_id': _(u'Country'),
    'shipping_zip': _(u'Zip / Postal code'),
    'shipping_state_id': _(u'State / Province'),
}


class CheckoutController(http.Controller, Mixin):

    labels = FIELDS_LABELS
    # use this to inject your form fields helpers
    form_fields_helpers = {}

    def translate(self, term):
        cr, uid, context, registry = \
            request.cr, request.uid, request.context, request.registry
        translations = registry.get('ir.translation')
        name = ''  # can ben empty since we are passing the source = term
        _type = 'code'
        lang = context.get('lang')
        return translations._get_source(cr, uid, name, _type, lang,
                                        source=term)

    def checkout_redirection(self, order):
        context = request.context

        # must have a draft sale order with lines at this point, otherwise reset
        if not order or order.state != 'draft':
            request.session['sale_order_id'] = None
            request.session['sale_transaction_id'] = None
            return request.redirect('/shop')

        # if transaction pending / done: redirect to confirmation
        tx = context.get('website_sale_transaction')
        if tx and tx.state != 'draft':
            return request.redirect('/shop/payment/confirmation/%s' % order.id)

    def checkout_values(self, data=None):
        cr, uid, context, registry = \
            request.cr, request.uid, request.context, request.registry
        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        orm_country = registry.get('res.country')
        state_orm = registry.get('res.country.state')

        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
        states_ids = state_orm.search(cr, SUPERUSER_ID, [], context=context)
        states = state_orm.browse(cr, SUPERUSER_ID, states_ids, context)
        partner = orm_user.browse(cr, SUPERUSER_ID, request.uid, context).partner_id

        order = None

        shipping_id = None
        shipping_ids = []
        checkout = {}
        if not data:
            if request.uid != request.website.user_id.id:
                checkout.update(self.checkout_parse("billing", partner) )
                shipping_ids = orm_partner.search(
                    cr, SUPERUSER_ID,
                    [("parent_id", "=", partner.id),
                     ('type', "=", 'delivery')],
                    context=context)
            else:
                order = request.website.sale_get_order(force_create=1,
                                                       context=context)
                if order.partner_id:
                    domain = [("partner_id", "=", order.partner_id.id)]
                    user_ids = request.registry['res.users'].search(
                        cr, SUPERUSER_ID, domain,
                        context=dict(context or {}, active_test=False))
                    if not user_ids or request.website.user_id.id not in user_ids:  # noqa
                        checkout.update(self.checkout_parse("billing", order.partner_id))  # noqa
        else:
            checkout = self.checkout_parse('billing', data)
            try:
                shipping_id = int(data["shipping_id"])
            except ValueError:
                pass
            if shipping_id == -1:
                checkout.update(self.checkout_parse('shipping', data))

        if shipping_id is None:
            if not order:
                order = request.website.sale_get_order(context=context)
            if order and order.partner_shipping_id:
                shipping_id = order.partner_shipping_id.id

        shipping_ids = list(set(shipping_ids) - set([partner.id]))

        if shipping_id == partner.id:
            shipping_id = 0
        elif shipping_id > 0 and shipping_id not in shipping_ids:
            shipping_ids.append(shipping_id)
        elif shipping_id is None and shipping_ids:
            shipping_id = shipping_ids[0]

        ctx = dict(context, show_address=1)
        shippings = []
        if shipping_ids:
            shippings = shipping_ids and orm_partner.browse(
                cr, SUPERUSER_ID, list(shipping_ids), ctx) or []
        if shipping_id > 0:
            shipping = orm_partner.browse(cr, SUPERUSER_ID, shipping_id, ctx)
            checkout.update(self.checkout_parse("shipping", shipping))

        checkout['shipping_id'] = shipping_id

        # Default search by user country
        if not checkout.get('country_id'):
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country_ids = request.registry.get('res.country').search(
                    cr, uid, [('code', '=', country_code)], context=context)
                if country_ids:
                    checkout['country_id'] = country_ids[0]

        values = {
            'countries': countries,
            'states': states,
            'checkout': checkout,
            'shipping_id': partner.id != shipping_id and shipping_id or 0,
            'shippings': shippings,
            'error': {},
            'form_fields_helpers': self.form_fields_helpers,
            'has_check_vat': hasattr(registry['res.partner'], 'check_vat'),
            'mandatory_fields': self.mandatory_fields,
            'labels': {k: self.translate(v)
                       for k, v in self.labels.iteritems()},
        }
        return values

    mandatory_billing_fields = [
        "name", "phone", "email",
        "street2", "city", "country_id"
    ]
    optional_billing_fields = [
        "street", "state_id", "vat",
        "vat_subjected", "zip"
    ]
    mandatory_shipping_fields = [
        "name", "phone", "street",
        "city", "country_id"
    ]
    optional_shipping_fields = ["state_id", "zip"]
    mandatory_fields = {}.fromkeys(
        mandatory_billing_fields +
        ['shipping_%s' % x for x in mandatory_shipping_fields],
        True
    )

    def checkout_parse(self, address_type, data, remove_prefix=False):
        """ data is a dict OR a partner browse record
        """
        # set mandatory and optional fields
        assert address_type in ('billing', 'shipping')
        if address_type == 'billing':
            all_fields = self.mandatory_billing_fields + self.optional_billing_fields
            prefix = ''
        else:
            all_fields = self.mandatory_shipping_fields + self.optional_shipping_fields
            prefix = 'shipping_'

        # set data
        if isinstance(data, dict):
            query = dict((prefix + field_name, data[prefix + field_name])
                for field_name in all_fields if data.get(prefix + field_name))
        else:
            query = dict((prefix + field_name, getattr(data, field_name))
                for field_name in all_fields if getattr(data, field_name))
            if address_type == 'billing' and data.parent_id:
                query[prefix + 'street'] = data.parent_id.name

        if query.get(prefix + 'state_id'):
            query[prefix + 'state_id'] = int(query[prefix + 'state_id'])
        if query.get(prefix + 'country_id'):
            query[prefix + 'country_id'] = int(query[prefix + 'country_id'])

        if query.get(prefix + 'vat'):
            query[prefix + 'vat_subjected'] = True

        if not remove_prefix:
            return query

        return dict((field_name, data[prefix + field_name])
                    for field_name in all_fields if data.get(prefix + field_name))

    def checkout_form_validate(self, data):
        # Validation
        error = dict()
        for field_name in self.mandatory_billing_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'

        for k, v in data.iteritems():
            validator_key = k
            # handle prefix
            if k != 'shipping_id' and validator_key.startswith('shipping_'):
                validator_key = k[len('shipping_'):]
            validator_name = '_validate_%s' % validator_key
            if hasattr(self, validator_name):
                validator = getattr(self, validator_name)
                validator(k, v, data, error=error)

        error_messages = self.get_error_messages(error)
        return error, error_messages

    def _validate_vat(self, key, value, data, error={}):
        cr, uid, registry = \
            request.cr, request.uid, request.registry

        partner_model = registry["res.partner"]

        if value and hasattr(partner_model, "check_vat"):
            if request.website.company_id.vat_check_vies:
                # force full VIES online check
                check_func = partner_model.vies_vat_check
            else:
                # quick and partial off-line checksum validation
                check_func = partner_model.simple_vat_check
            vat_country, vat_number = partner_model._split_vat(value)
            # simple_vat_check
            if not check_func(cr, uid, vat_country, vat_number, context=None):
                error[key] = 'error'
        return error

    def _validate_shipping_id(self, key, value, data, error={}):
        if value == -1:
            for field_name in self.mandatory_shipping_fields:
                field_name = 'shipping_' + field_name
                if not data.get(field_name):
                    error[field_name] = 'missing'
        return error

    def _validate_email(self, key, value, data, error={}):
        if validate_email(value, verify=HAS_PyDNS) is False:
            # we check specifically if `False` because if the
            # mail MX is no responding you get `None`.
            # In this case let's assume the email is still valid
            # since the validation of the syntax is done anyway.
            error[key] = 'wrong'
        return error

    def _validate_phone(self, key, value, data, error={}):
        if not validate_phonenumber(value):
            error[key] = 'wrong'
        return error

    def get_error_messages(self, errors):
        """ override this to inject your error messages
        """
        return {}

    def checkout_form_save(self, checkout):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        order = request.website.sale_get_order(force_create=1, context=context)

        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        order_obj = request.registry.get('sale.order')

        partner_lang = request.lang if request.lang in [lang.code for lang in request.website.language_ids] else None

        billing_info = {}
        if partner_lang:
            billing_info['lang'] = partner_lang
        billing_info.update(self.checkout_parse('billing', checkout, True))

        # set partner_id
        partner_id = None
        if request.uid != request.website.user_id.id:
            partner_id = orm_user.browse(cr, SUPERUSER_ID, uid, context=context).partner_id.id
        elif order.partner_id:
            user_ids = request.registry['res.users'].search(cr, SUPERUSER_ID,
                [("partner_id", "=", order.partner_id.id)], context=dict(context or {}, active_test=False))
            if not user_ids or request.website.user_id.id not in user_ids:
                partner_id = order.partner_id.id

        # save partner informations
        if partner_id and request.website.partner_id.id != partner_id:
            orm_partner.write(cr, SUPERUSER_ID, [partner_id], billing_info, context=context)
        else:
            # create partner
            partner_id = orm_partner.create(cr, SUPERUSER_ID, billing_info, context=context)

        # create a new shipping partner
        if checkout.get('shipping_id') == -1:
            shipping_info = {}
            if partner_lang:
                shipping_info['lang'] = partner_lang
            shipping_info.update(self.checkout_parse('shipping', checkout, True))
            shipping_info['type'] = 'delivery'
            shipping_info['parent_id'] = partner_id
            checkout['shipping_id'] = orm_partner.create(cr, SUPERUSER_ID, shipping_info, context)

        order_info = {
            'partner_id': partner_id,
            'message_follower_ids': [(4, partner_id), (3, request.website.partner_id.id)],
            'partner_invoice_id': partner_id,
        }
        order_info.update(order_obj.onchange_partner_id(cr, SUPERUSER_ID, [], partner_id, context=context)['value'])
        address_change = order_obj.onchange_delivery_id(cr, SUPERUSER_ID, [], order.company_id.id, partner_id,
                                                        checkout.get('shipping_id'), None, context=context)['value']
        order_info.update(address_change)
        if address_change.get('fiscal_position'):
            fiscal_update = order_obj.onchange_fiscal_position(cr, SUPERUSER_ID, [], address_change['fiscal_position'],
                                                               [(4, l.id) for l in order.order_line], context=None)['value']
            order_info.update(fiscal_update)

        order_info.pop('user_id')
        order_info.update(partner_shipping_id=checkout.get('shipping_id') or partner_id)

        order_obj.write(cr, SUPERUSER_ID, [order.id], order_info, context=context)

    @http.route(['/shop/checkout'], type='http', auth="public", website=True)
    def checkout(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        order = request.website.sale_get_order(force_create=1, context=context)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values()

        return request.website.render("website_sale.checkout", values)

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True)
    def confirm_order(self, **post):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        order = request.website.sale_get_order(context=context)
        if not order:
            return request.redirect("/shop")

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        values = self.checkout_values(post)

        values["error"], values['error_messages'] = \
            self.checkout_form_validate(values["checkout"])
        if values["error"]:
            return request.website.render("website_sale.checkout", values)

        self.checkout_form_save(values["checkout"])

        request.session['sale_last_order_id'] = order.id

        request.website.sale_get_order(update_pricelist=True, context=context)

        return request.redirect("/shop/payment")
