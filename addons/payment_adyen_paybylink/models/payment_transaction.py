# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _adyen_form_get_tx_from_data(self, data):
        """ Override of _adyen_form_get_tx_from_data """
        reference = data.get('merchantReference')
        psp_reference = data.get('pspReference')
        if not reference or not psp_reference:
            error_msg = _(
                "Adyen: received data with missing reference (%s) or "
                "missing pspReference (%s)"
            ) % (reference, psp_reference)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        tx = self.env['payment.transaction'].search([
            ('reference', '=', reference), ('provider', '=', 'adyen')
        ])
        if not tx or len(tx) > 1:
            error_msg = _("Adyen: received data for reference %s") % reference
            if not tx:
                error_msg += _("; no order found")
            else:
                error_msg += _("; multiple order found")
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return tx

    def _adyen_form_get_invalid_parameters(self, data):
        """ Override of _adyen_form_get_invalid_parameters to disable
        this method.

        The pay-by-link implementation doesn't need or want to check for
        invalid parameters.
        """
        return []

    def process_fraud_case(self, post):
        """ Handle the case when Adyen informs us of a fraud and executes a
        chargeback. In this case we block the SO and make a note on the
        SO and (if existing) invoices
        """
        for so in self.sale_order_ids:
            try:
                so.action_cancel()
            except Exception as e:
                so.block_shipment = True
                message = (
                    'Order {order_name} cancellation failed with {error_m}.'
                    ' Order is blocked instead. If DSV is the fulfillment'
                    ' center call them and stop the shipment'.format(
                        order_name=so.name,
                        error_m=str(e)))
                so.message_post(body=message)
                _logger.error(message)
                return False

        tran_message = (
            "Adyen notification with event code {event_code} cancelled the "
            "transaction {tran_num} with reason: {reason}; - and reason code "
            "{reason_code}. Related Sale Order is cancelled/blocked".format(
                event_code=post.get('eventCode'),
                tran_num=post.get('merchantReference'),
                reason=post.get('reason'),
                reason_code=post.get('additionalData.chargebackReasonCode'))
        )
        _logger.info(tran_message)
        self.state_message = tran_message
        self._set_transaction_cancel()
