# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time
import datetime
from dateutil.relativedelta import relativedelta
from openerp import fields, models
from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import UserError

class project_project(models.Model):
    _inherit = 'project.project'

    def open_timesheets(self):
        """ open Timesheets view """
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']

        project = self
        view_context = {
            'search_default_account_id': [project.analytic_account_id.id],
            'default_account_id': project.analytic_account_id.id,
            'default_is_timesheet':True
        }
        help = _("""<p class="oe_view_nocontent_create">Record your timesheets for the project '%s'.</p>""") % (project.name,)

        res = mod_obj.get_object_reference('hr_timesheet', 'act_hr_timesheet_line_evry1_all_form')
        id = res and res[1] or False
        result = act_obj[0]
        result['name'] = _('Timesheets')
        result['context'] = view_context
        result['help'] = help
        return result

    def open_contract(self):
        """ open Contract view """

        res = self.env['ir.actions.act_window'].for_xml_id('project_timesheet', 'action_project_analytic_account')
        contract_ids = self
        account_ids = [x.analytic_account_id.id for x in contract_ids]
        res['res_id'] = account_ids and account_ids[0] or None
        return res


class task(models.Model):
    _inherit = "project.task"

    # Compute: effective_hours, total_hours, progress
    def _hours_get(self, field_names, args):
        res = {}
        for task in self:
            res[task.id] = {
                'effective_hours': 0.0,
                'remaining_hours': task.planned_hours,
                'progress': 100.0 if task.stage_id and task.stage_id.fold else 0.0,
                'total_hours': task.planned_hours,
                'delay_hours': 0.0,
            }
        tasks_data = self.env['account.analytic.line'].read_group([('task_id', 'in')], ['task_id','unit_amount'], ['task_id'])
        for data in tasks_data:
            task = self.search([('task_id', 'in', data['task_id'][0])])
            res[data['task_id'][0]] = {'effective_hours': data.get('unit_amount', 0.0), 'remaining_hours': task.planned_hours - data.get('unit_amount', 0.0)}
            res[data['task_id'][0]]['total_hours'] = res[data['task_id'][0]]['remaining_hours'] + data.get('unit_amount', 0.0)
            res[data['task_id'][0]]['delay_hours'] = res[data['task_id'][0]]['total_hours'] - task.planned_hours
            res[data['task_id'][0]]['progress'] = 0.0
            if (task.planned_hours > 0.0 and data.get('unit_amount', 0.0)):
                res[data['task_id'][0]]['progress'] = round(min(100.0 * data.get('unit_amount', 0.0) / task.planned_hours, 99.99),2)
            # TDE CHECK: if task.state in ('done','cancelled'):
            if task.stage_id and task.stage_id.fold:
                res[data['task_id'][0]]['progress'] = 100.0
        return res

    def _get_task(id):
        res = []
        for line in self.env['account.analytic.line'].search_read([('task_id', '!=', False),('id','in',id)], ['task_id']):
            res.append(line['task_id'][0])
        return res

    def _get_total_hours(self):
        return super(task, self)._get_total_hours() + self.effective_hours

    remaining_hours = fields.Float(
        compute='_hours_get',
        string='Remaining Hours',
        multi='line_id',
        help="Total remaining time, can be re-estimated periodically by the assignee of the task.",
        store = {
            'project.task': (lambda self, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
            'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
        })
    effective_hours = fields.Float(
        compute='_hours_get',
        string='Hours Spent',
        multi='line_id', help="Computed using the sum of the task work done.",
        store = {
            'project.task': (lambda self, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
            'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
        })
    total_hours = fields.Float(
        compute='_hours_get',
        string='Total',
        multi='line_id', help="Computed as: Time Spent + Remaining Time.",
        store = {
            'project.task': (lambda self, ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
            'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
        })
    progress = fields.Float(
        compute='_hours_get',
        string='Working Time Progress (%)',
        multi='line_id',
        group_operator="avg",
        help="If the task has a progress of 99.99% you should close the task if it's finished or reevaluate the time",
        default=0,
        store = {
            'project.task': (lambda self,
                             ['timesheet_ids', 'remaining_hours', 'planned_hours', 'state', 'stage_id'], 10),
            'account.analytic.line': (
                _get_task, ['task_id', 'unit_amount'], 10),
        })
    delay_hours = fields.Float(
        compute='_hours_get',
        string='Delay Hours',
        multi='line_id',
        help="Computed as difference between planned hours by the project manager and the total hours of the task.",
        store = {
            'project.task': (lambda self,
                             ['timesheet_ids', 'remaining_hours', 'planned_hours'], 10),
            'account.analytic.line': (_get_task, ['task_id', 'unit_amount'], 10),
        })
    timesheet_ids = fields.One2many(
        'account.analytic.line',
        'task_id',
        'Timesheets')
    analytic_account_id = fields.Many2one(
        related='project_id.analytic_account_id',
        relation='account.analytic.account', string='Analytic Account', store=True)

    def _prepare_delegate_values(self, delegate_data):
        vals = super(task, self)._prepare_delegate_values(delegate_data)
        for task in self:
            vals[task.id]['planned_hours'] += task.effective_hours
        return vals


class res_partner(models.Model):
    _inherit = 'res.partner'

    def unlink(self, ids):
        parnter_id=self.env['project.project'].search([('partner_id', 'in', ids)])
        if parnter_id:
            raise UserError(_('You cannot delete a partner which is assigned to project, but you can uncheck the active box.'))
        return super(res_partner,self).unlink(ids)

class account_analytic_line(models.Model):
    _inherit = "account.analytic.line"
    task_id = fields.Many2one('project.task', 'Task')
