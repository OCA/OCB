# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AssignRollNo(models.TransientModel):
    '''designed for assigning roll number to a student'''

    _name = 'assign.roll.no'
    _description = 'Assign Roll Number'

    standard_id = fields.Many2one('standard.standard', 'Class', required=True)
    medium_id = fields.Many2one('standard.medium', 'Medium', required=True)
    division_id = fields.Many2one('standard.division', 'Division',
                                  required=True)

    @api.multi
    def assign_rollno(self):
        res = {}
        student_obj = self.env['student.student']
        for student_data in self:
            search_student_ids = student_obj.search([
                ('standard_id', '=', student_data.standard_id.id),
                ('medium_id', '=', student_data.medium_id.id),
                ('division_id', '=', student_data.division_id.id)])
        number = 1
        for student in search_student_ids:
            student.write({'roll_no': number})
            number = number + 1
        return res
