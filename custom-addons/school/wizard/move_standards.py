# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import except_orm


class MoveStandards(models.TransientModel):
    _name = 'move.standards'

    academic_year_id = fields.Many2one('academic.year', 'Academic Year',
                                       required=True)

    @api.multi
    def move_start(self):
        self._context = dict(self._context or {})
        active_ids = self._context.get('active_ids')
        if not active_ids:
            return {}
        academic_obj = self.env['academic.year']
        school_standard_obj = self.env['school.standard']
        standard_obj = self.env["standard.standard"]
        result_obj = self.env['exam.result']
        student_obj = self.env['student.student']
        stud_history_obj = self.env["student.history"]
        for data in self:
            for standards in school_standard_obj.browse(active_ids):
                for student in standards.student_ids:
                    stud_year_domain = [('academice_year_id',
                                         '=',
                                         data.academic_year_id.id),
                                        ('student_id', '=', student.id)]
                    stud_year_ids = stud_history_obj.search(stud_year_domain)
                    year_id = academic_obj.next_year(student.year.sequence)
                    if year_id and year_id != data.academic_year_id.id:
                        continue
                    if stud_year_ids:
                        raise except_orm(_('Warning !'),
                                         _('Please Select'
                                           'Next Academic year.'))
                    else:
                        result_domain = [('standard_id', '=',
                                          student.standard_id.id),
                                         ('standard_id.division_id',
                                          '=', student.division_id.id),
                                         ('standard_id.medium_id',
                                          '=', student.medium_id.id),
                                         ('student_id', '=', student.id)]
                        result_exists = result_obj.search(result_domain)
                        if result_exists:
                            result_data = result_obj.browse(result_exists.id)
                            a = standards.standard_id.sequence
                            if result_data.result == "Pass":
                                next_class_id = standard_obj.next_standard(a)
                                if next_class_id:
                                    student_id = student_obj.browse(student.id)
                                    d_one = {'year': data.academic_year_id.id,
                                             'standard_id': next_class_id}
                                    student_id.write(d_one)
                                    std_id_id = standards.standard_id.id
                                    div_id_id = standards.division_id.id
                                    v = {'student_id': student.id,
                                         'academice_year_id': student.year.id,
                                         'standard_id': std_id_id,
                                         'division_id': div_id_id,
                                         'medium_id': standards.medium_id.id,
                                         'result': result_data.result,
                                         'percentage': result_data.percentage}
                                    stud_history_obj.create(v)
                            else:
                                raise except_orm(_("Error!"),
                                                 _('Student is not eligible'
                                                   'for Next Standard.'))
        return {}
