# -*- coding: utf-8 -*-
{
    'license': 'LGPL-3',
    'name': "Document Management System",
    'summary': "Enterprise online document management",
    'description': """
    """,
    'author': "renjie <i@renjie.me>",
    'website': "https://renjie.me",
    'support': 'i@renjie.me',
    'category': 'Document Management',
    'version': '1.0',
    'depends': ['document', 'mail'],
    'data': [
        'security/account_security.xml',
        'security/ir.model.access.csv',
        'views/webclient_templates.xml',
        'views/document.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}