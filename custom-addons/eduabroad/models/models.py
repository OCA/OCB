# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class Quotation(models.Model):
    _name = 'eduabroad.quotation'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    itinerary_ids = fields.One2many('eduabroad.itinerary',
                                    'quotation_id', string="Itinerary", track_visibility='onchange')
    customer_ids = fields.Many2one('res.partner', domain=[('customer', '=', True)], string="Customer")

    number_member = fields.Float(string="# of Members", digits=(4, 0), track_visibility='onchange')
    number_leader = fields.Float(string="# of Leader", digits=(2, 0), track_visibility='onchange')

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    total_days = fields.Float(string="Total Days", digits=(3, 0))
    total_nights = fields.Integer('Total Nights', compute='_compute_total_days', store=True)
    total_cost = fields.Float(compute='_compute_cost', string='Total Cost', store=True, track_visibility='onchange')

    value = fields.Integer()
    value2 = fields.Char()





    @api.multi
    @api.depends('start_date', 'end_date', 'total_days')
    def _compute_total_days(self):
        self.total_nights = 0
        if self.start_date:
            start = datetime.strptime(self.start_date,
                                      "%Y-%m-%d")
            end = datetime.strptime(self.end_date,
                                    "%Y-%m-%d")
            self.total_nights = (end - start).days

    @api.multi
    @api.depends('itinerary_ids.total_price')
    def _compute_cost(self):
        for record in self:
            record.total_cost = sum(itinerary.total_price for itinerary in record.itinerary_ids)

class Itinerary(models.Model):
    _name = 'eduabroad.itinerary'
    _inherit = ['mail.thread']

    name = fields.Char(string="Day", required=True)
    date = fields.Date()
    ag = fields.Boolean(string="Active Guide", default=False, track_visibility='onchange')
    ag_hr = fields.Float(string="AG Hours", digits=(2, 2), default="0", track_visibility='onchange')
    ag_num =fields.Float(string="AG Number", digits=(2, 0), default="1", track_visibility='onchange')

    transportation_id = fields.Many2one('eduabroad.transportation',
                                        ondelete='cascade', string="Transportation", index=True, track_visibility='onchange')
    activities_ids = fields.Many2many('eduabroad.activities',
                                      ondelete='cascade', string="Activites", index=True, track_visibility='onchange')
    accommodation_id = fields.Many2one('eduabroad.accommodation',
                                       ondelete='cascade', string="Accommodation", index=True, track_visibility='onchange')
    quotation_id = fields.Many2one('eduabroad.quotation',
                                   ondelete='cascade', string="Quotation", index=True, track_visibility='onchange')

    # price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    total_price = fields.Float(compute='_compute_amount', string='Subtotal', store=True)


    @api.depends('activities_ids.price', 'transportation_id.price', 'accommodation_id.price', 'ag_hr', 'ag_num')
    def _compute_amount(self):

        for record in self:
            record.total_price = sum(activities.price for activities in record.activities_ids) + \
                                 record.transportation_id.price + \
                                 record.accommodation_id.price + \
                                 record.ag_hr * record.ag_num * 20

class Transportation(models.Model):
    _name = 'eduabroad.transportation'

    name = fields.Char(required=True)
    price = fields.Float(digits=(8, 2))
    description = fields.Text()

    itinerary_ids = fields.One2many('eduabroad.itinerary',
                                    'transportation_id', string="Itinerary")



class Activities(models.Model):
    _name = 'eduabroad.activities'

    name = fields.Char(required=True)
    price = fields.Float(digits=(8, 2))

    description = fields.Text()

    itinerary_ids = fields.One2many('eduabroad.itinerary',
                                    'activities_ids', string="Itinerary")


class Accommodation(models.Model):
    _name = 'eduabroad.accommodation'

    name = fields.Char(required=True)
    price = fields.Float(digits=(8, 2))
    description = fields.Text()
    itinerary_ids = fields.One2many('eduabroad.itinerary',
                                    'activities_ids', string="Accommodation")


class PhoneRecord(models.Model):
    _name = 'eduabroad.phone'

    name = fields.Char()


class WechatRecord(models.Model):
    _name = 'eduabroad.wechat'

    name = fields.Char()


class VisitingRecord(models.Model):
    _name = 'eduabroad.wechat'

    name = fields.Char()
