# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{'name': 'School',

 'version': '10.0.1.0.0',
 'author': 'Serpent Consulting Services Pvt. Ltd., Odoo SA',
 'website': 'http://www.serpentcs.com',
 'category': 'School Management',
 'license': "AGPL-3",
 'complexity': 'easy',
 'Summary': 'A Module For School Management',
 'depends': ['hr', 'crm', 'report', 'board'],
 'data': ['wizard/wiz_send_email_view.xml',
          'security/school_security.xml',
          'views/school_view.xml',
          'security/ir.model.access.csv',
          'views/admission_workflow.xml',
          'data/student_sequence.xml',
          'wizard/assign_roll_no_wizard.xml',
          'wizard/move_standards_view.xml',
          'wizard/wiz_meeting_view.xml',
          'views/report_view.xml',
          'views/identity_card.xml'],
    'test': ['test/school_test.yml', 'test/assign_roll_no_test.yml'],
    'installable': True,
    'application': True}
