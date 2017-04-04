# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import except_orm


class StudentMeeting(models.TransientModel):
    _name = "student.meeting"

    name = fields.Char('Meeting Subject', size=128, required=True)
    meeting_date = fields.Datetime('Meeting Date', required=True)
    deadline = fields.Datetime('Deadline', required=True)
    description = fields.Text('Description')

    @api.multi
    def set_meeting(self):
        cur_rec = self.browse(self.id)
        student_obj = self.env['student.student']
        cal_event_obj = self.env['calendar.event']
        attendee_ids = []
        flag = False
        error_student = ''
        for student in student_obj.browse(self._context['active_ids']):
            if not student.email:
                flag = True
                error_student += student.pid + " : " + student.name\
                    + " " + student.middle + " " + student.last + "\n"
            else:
                attendee_ids.append((0, 0, {'user_id': student.user_id.id,
                                            'email': student.email}))
        if flag:
            raise except_orm(_('Error !'),
                             _('Following Student'
                               'does not have Email ID.\n'
                               '\n' + error_student +
                               '\nMeeting cannot be scheduled.'))
        cal_event_obj.create({'name': cur_rec.name,
                              'start': cur_rec.meeting_date,
                              'stop': cur_rec.deadline,
                              'description': cur_rec.description,
                              'attendee_ids': attendee_ids})
        return {'type': 'ir.actions.act_window_close'}
