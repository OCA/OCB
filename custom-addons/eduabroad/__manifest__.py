# -*- coding: utf-8 -*-
{
    'name': "eduabroad",

    'summary': """
        """,

    'description': """

    """,

    'author': "Yoshi",
    'website': "http://www.eduabroad.us",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'crm'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/eduabroad.xml',
        'views/templates.xml',
        # 'views/partner.xml',
        # 'views/lead.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
'installable': True,
'application': True,
}