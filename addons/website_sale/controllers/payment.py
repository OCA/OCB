# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug

from .mixin import Mixin
from .checkout import CheckoutController


class PaymentController(CheckoutController, Mixin):

    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sale order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        cr, uid, context = request.cr, request.uid, request.context
        payment_obj = request.registry.get('payment.acquirer')
        sale_order_obj = request.registry.get('sale.order')

        order = request.website.sale_get_order(context=context)

        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        shipping_partner_id = False
        if order:
            if order.partner_shipping_id.id:
                shipping_partner_id = order.partner_shipping_id.id
            else:
                shipping_partner_id = order.partner_invoice_id.id

        values = {
            'order': request.registry['sale.order'].browse(cr, SUPERUSER_ID, order.id, context=context)
        }
        values['errors'] = sale_order_obj._get_errors(cr, uid, order, context=context)
        values.update(sale_order_obj._get_website_data(cr, uid, order, context))

        # fetch all registered payment means
        # if tx:
        #     acquirer_ids = [tx.acquirer_id.id]
        # else:
        if not values['errors']:
            acquirer_ids = payment_obj.search(cr, SUPERUSER_ID, [('website_published', '=', True), ('company_id', '=', order.company_id.id)], context=context)
            values['acquirers'] = list(payment_obj.browse(cr, uid, acquirer_ids, context=context))
            render_ctx = dict(context, submit_class='btn btn-primary', submit_txt=_('Pay Now'))
            for acquirer in values['acquirers']:
                acquirer.button = payment_obj.render(
                    cr, SUPERUSER_ID, acquirer.id,
                    order.name,
                    order.amount_total,
                    order.pricelist_id.currency_id.id,
                    partner_id=shipping_partner_id,
                    tx_values={
                        'return_url': '/shop/payment/validate',
                    },
                    context=render_ctx)

        return request.website.render("website_sale.payment", values)

    @http.route(['/shop/payment/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        cr, uid, context = request.cr, request.uid, request.context
        transaction_obj = request.registry.get('payment.transaction')
        order = request.website.sale_get_order(context=context)

        if not order or not order.order_line or acquirer_id is None:
            return request.redirect("/shop/checkout")

        assert order.partner_id.id != request.website.partner_id.id

        # find an already existing transaction
        tx = request.website.sale_get_transaction()
        if tx:
            if tx.state == 'draft':  # button cliked but no more info -> rewrite on tx or create a new one ?
                tx.write({
                    'acquirer_id': acquirer_id,
                })
            tx_id = tx.id
        else:
            tx_id = transaction_obj.create(cr, SUPERUSER_ID, {
                'acquirer_id': acquirer_id,
                'type': 'form',
                'amount': order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'partner_country_id': order.partner_id.country_id.id,
                'reference': order.name,
                'sale_order_id': order.id,
            }, context=context)
            request.session['sale_transaction_id'] = tx_id

        # update quotation
        request.registry['sale.order'].write(
            cr, SUPERUSER_ID, [order.id], {
                'payment_acquirer_id': acquirer_id,
                'payment_tx_id': request.session['sale_transaction_id']
            }, context=context)

        return tx_id

    @http.route('/shop/payment/get_status/<int:sale_order_id>', type='json', auth="public", website=True)
    def payment_get_status(self, sale_order_id, **post):
        cr, uid, context = request.cr, request.uid, request.context

        order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        assert order.id == request.session.get('sale_last_order_id')

        if not order:
            return {
                'state': 'error',
                'message': '<p>%s</p>' % _('There seems to be an error with your request.'),
            }

        tx_ids = request.registry['payment.transaction'].search(
            cr, SUPERUSER_ID, [
                '|', ('sale_order_id', '=', order.id), ('reference', '=', order.name)
            ], context=context)

        if not tx_ids:
            if order.amount_total:
                return {
                    'state': 'error',
                    'message': '<p>%s</p>' % _('There seems to be an error with your request.'),
                }
            else:
                state = 'done'
                message = ""
                validation = None
        else:
            tx = request.registry['payment.transaction'].browse(cr, SUPERUSER_ID, tx_ids[0], context=context)
            state = tx.state
            if state == 'done':
                message = '<p>%s</p>' % _('Your payment has been received.')
            elif state == 'cancel':
                message = '<p>%s</p>' % _('The payment seems to have been canceled.')
            elif state == 'pending' and tx.acquirer_id.validation == 'manual':
                message = '<p>%s</p>' % _('Your transaction is waiting confirmation.')
                if tx.acquirer_id.post_msg:
                    message += tx.acquirer_id.post_msg
            else:
                message = '<p>%s</p>' % _('Your transaction is waiting confirmation.')
            validation = tx.acquirer_id.validation

        return {
            'state': state,
            'message': message,
            'validation': validation
        }

    @http.route('/shop/payment/validate', type='http', auth="public", website=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        cr, uid, context = request.cr, request.uid, request.context
        email_act = None
        sale_order_obj = request.registry['sale.order']

        if transaction_id is None:
            tx = request.website.sale_get_transaction()
        else:
            tx = request.registry['payment.transaction'].browse(cr, uid, transaction_id, context=context)

        if sale_order_id is None:
            order = request.website.sale_get_order(context=context)
        else:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
            assert order.id == request.session.get('sale_last_order_id')

        if not order or (order.amount_total and not tx):
            return request.redirect('/shop')

        if (not order.amount_total and not tx) or tx.state in ['pending', 'done']:
            if (not order.amount_total and not tx):
                # Orders are confirmed by payment transactions, but there is none for free orders,
                # (e.g. free events), so confirm immediately
                order.action_button_confirm()
            # send by email
            email_act = sale_order_obj.action_quotation_send(cr, SUPERUSER_ID, [order.id], context=request.context)
        elif tx and tx.state == 'cancel':
            # cancel the quotation
            sale_order_obj.action_cancel(cr, SUPERUSER_ID, [order.id], context=request.context)

        # send the email
        if email_act and email_act.get('context'):
            composer_obj = request.registry['mail.compose.message']
            composer_values = {}
            email_ctx = email_act['context']
            template_values = [
                email_ctx.get('default_template_id'),
                email_ctx.get('default_composition_mode'),
                email_ctx.get('default_model'),
                email_ctx.get('default_res_id'),
            ]
            composer_values.update(composer_obj.onchange_template_id(cr, SUPERUSER_ID, None, *template_values, context=context).get('value', {}))
            if not composer_values.get('email_from') and uid == request.website.user_id.id:
                composer_values['email_from'] = request.website.user_id.company_id.email
            for key in ['attachment_ids', 'partner_ids']:
                if composer_values.get(key):
                    composer_values[key] = [(6, 0, composer_values[key])]
            composer_id = composer_obj.create(cr, SUPERUSER_ID, composer_values, context=email_ctx)
            composer_obj.send_mail(cr, SUPERUSER_ID, [composer_id], context=email_ctx)

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset(context=context)

        return request.redirect('/shop/confirmation')

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True)
    def payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        cr, uid, context = request.cr, request.uid, request.context

        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.registry['sale.order'].browse(cr, SUPERUSER_ID, sale_order_id, context=context)
        else:
            return request.redirect('/shop')

        return request.website.render("website_sale.confirmation", {'order': order})
