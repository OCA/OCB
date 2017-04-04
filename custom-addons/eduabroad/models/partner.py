# -*- coding: utf-8 -*-
from odoo import fields, models

class Partner(models.Model):
    _inherit = 'res.partner'

    quotation_ids = fields.Many2many('eduabroad.quotation',
                                     string="Quotations", readonly=True)
    # wechat = fields.Char('Wechat')
