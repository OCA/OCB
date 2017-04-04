# -*- coding: utf-8 -*-
from odoo import http

# class Eduabroad(http.Controller):
#     @http.route('/eduabroad/eduabroad/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/eduabroad/eduabroad/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('eduabroad.listing', {
#             'root': '/eduabroad/eduabroad',
#             'objects': http.request.env['eduabroad.eduabroad'].search([]),
#         })

#     @http.route('/eduabroad/eduabroad/objects/<model("eduabroad.eduabroad"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('eduabroad.object', {
#             'object': obj
#         })