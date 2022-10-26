# © 2019 - 2021 Vanmoof BV (<https://www.vanmoof.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import mock
import requests
from odoo.tests import tagged
from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase

@tagged("post_install", "-at_install")
class TestAdyenWebhooks(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["payment.acquirer"].create(
            {
                "name": __name__,
                "provider": "adyen",
                "environment": "test",
                "adyen_valid_for_days": 10,
                "adyen_skin_code": "obsolete_dummy",
                "adyen_skin_hmac_key": "obsolete_dummy",
                "adyen_merchant_account": "VANMOOF_NL",
                "adyen_api_key": "a_very_long_key",
                "adyen_checkout_api_url": "https://adyen",
                "adyen_hmac_key": "42",
                "company_id": cls.env.ref("base.main_company").id,
            }
        )

        cls.so = cls.env.ref('sale.sale_order_8')
        # create payment transaction
        values = {
            "acquirer_id": cls.config.id,
            "reference": cls.so.name,
            "amount": 201,
            "currency_id": cls.env.ref("base.GBP").id,
            "partner_id": cls.env.ref("base.res_partner_12").id,
            "type": "form",
            "sale_order_ids": [(6, 0, cls.so.ids)]
        }
        cls.transaction = (
            cls.env["payment.transaction"].sudo().with_context(
                lang=None).create(values)
        )

    def test_fraud_notification(self):
        """Test the webhook by simulating Adyen sending us a open dispute
        notification. Cancel Order cae
         'eventCode': 'NOTIFICATION_OF_CHARGEBACK',
        """
        self.assertEqual(self.transaction.state, "draft")

        # mock adyen webhook response for authorized transaction
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        url = base_url + "/payment/adyen/notification"
        payload = (
            "additionalData.autoDefended=false&"
            "additionalData.chargebackReasonCode=10.4&"
            "additionalData.chargebackSchemeCode=visa&"
            "additionalData.defendable=true&"
            "additionalData.defensePeriodEndsAt=2023-01-24T12:17:23+01:00&"
            "additionalData.disputeStatus=Undefended&"
            "additionalData.hmacSignature=xxx&"
            "currency=EUR&"
            "eventCode=NOTIFICATION_OF_CHARGEBACK&"
            "eventDate=2022-09-26T10:17:23.00Z&"
            "live=false&"
            "merchantAccountCode=VANMOOF_NL&"
            "merchantReference={merchantReference}&"
            "operations=&"
            "originalReference=NXDJ258MG5BV9D82&"
            "paymentMethod=visa&"
            "pspReference=8626641874058257&"
            "reason=Other Fraud-Card Absent Environment&"
            "success=true&"
            "value=1000"
        ).format(merchantReference=self.so.name)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # mock where we search for the transaction beacuse tests run in a
        # separate transaction from the requests.request() call. Because of
        # this you will never find the transaction created above.
        mock_method = (
            "odoo.addons.payment_adyen_paybylink.models."
            "payment_transaction.PaymentTransaction."
            "_adyen_form_get_tx_from_data"
        )
        with mock.patch(mock_method) as mock_func:
            mock_func.return_value = self.transaction

            # mock the function where we check the HMAC signature of the
            # message. Now we can send any message without calculate
            # message the signature
            mock_hmac_signature = (
                "odoo.addons.payment_adyen_paybylink."
                "controllers.main.AdyenPayByLinkController."
                "_verify_notification_signature"
            )
            with mock.patch(mock_hmac_signature) as mock_signature:
                mock_signature.return_value = True

                response = requests.request(
                    "POST", url, headers=headers, data=payload)

        self.assertEqual(response.text, "[accepted]")
        self.assertEqual(response.status_code, 200)

        self.transaction.refresh()
        self.assertEqual(self.transaction.state, "cancel")
        self.assertEqual(self.transaction.sale_order_ids.state, 'cancel')

        # does the transaction state message contain all of the elements
        for message_element in ['NOTIFICATION_OF_CHARGEBACK',
                                self.so.name,
                                '10.4',
                                'Other Fraud-Card Absent Environment']:
            self.assertTrue(message_element in self.transaction.state_message)

        # does the Sale Order have the cancel message posted
        cancel_message_posted = False
        for posted_message in self.so.message_ids:
            if 'NOTIFICATION_OF_CHARGEBACK' in posted_message.body:
                cancel_message_posted = True
        self.assertTrue(cancel_message_posted)
