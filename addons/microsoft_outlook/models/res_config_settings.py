# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    microsoft_outlook_client_identifier = fields.Char(related='company_id.microsoft_outlook_client_identifier', string='Outlook Client Id')
    microsoft_outlook_client_secret = fields.Char(related='company_id.microsoft_outlook_client_secret', string='Outlook Client Secret')


class Company(models.Model):
    _inherit = "res.company"

    microsoft_outlook_client_identifier = fields.Char()
    microsoft_outlook_client_secret = fields.Char()
