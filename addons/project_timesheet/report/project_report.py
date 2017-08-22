# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp import fields,models
from openerp import tools

class report_project_task_user(models.Model):
    _inherit = "report.project.task.user"
    hours_planned = fields.Float('Planned Hours', readonly=True)
    hours_effective = fields.Float('Effective Hours', readonly=True)
    hours_delay = fields.Float('Avg. Plan.-Eff.', readonly=True)
    remaining_hours = fields.Float('Remaining Hours', readonly=True)
    progress = fields.Float('Progress', readonly=True, group_operator='avg')
    total_hours = fields.Float('Total Hours', readonly=True)

    def _select(self):
        return  super(report_project_task_user, self)._select() + ", progress as progress, t.effective_hours as hours_effective, remaining_hours as remaining_hours, total_hours as total_hours, t.delay_hours as hours_delay, planned_hours as hours_planned"

    def _group_by(self):
        return super(report_project_task_user, self)._group_by() + ", remaining_hours, t.effective_hours, progress, total_hours, planned_hours, hours_delay"
