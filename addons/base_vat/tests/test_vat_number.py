# coding: utf-8
# Copyright (C) 2020 Essent <http://www.essent.be>
# @author Robin Conjour <r.conjour@essent.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import SavepointCase

class TestVatNumber(SavepointCase):
    """ Test vat validator """

    def setUp(self):
        super(TestVatNumber, self).setUp()
        self.partner_id = self.env['res.partner'].create(
            {'name': 'Test', 'ref': '__aswr_test'})

    def test_00_nl_vat(self):
        """
        Check NL vat number validation
        """

        valid_vat = '000099998B57'
        invalid_vat = '020099998B01'

        self.assertTrue(self.partner_id.simple_vat_check('nl', valid_vat))
        self.assertFalse(self.partner_id.simple_vat_check('nl', invalid_vat))

