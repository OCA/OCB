# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': "pos_cache",

    'summary': """
        Enable a cache on products for a lower pos loading time""",

    'description': """
        Creates a cache on products per pos.session
        To avoid long pos loading time when a high number of products have to be loaded
    """,

    'author': "Odoo",
    'website': "https://www.odoo.com/page/point-of-sale",
    'category': 'Point Of Sale',
    'version': '0.1',
    'depends': ['point_of_sale'],
    'data': [
        'data/cron.xml',
        'security/ir.model.access.csv',
        'views/posconfig.xml',
        'views/templates.xml',
    ]
}
