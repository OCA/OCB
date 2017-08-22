# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models
from openerp.tools.translate import _

class project_configuration(models.TransientModel):
    _name = 'project.config.settings'
    _inherit = 'project.config.settings'

    group_tasks_work_on_tasks = fields.Selection(
        [
            (0, "Do not log work activities on task"),
            (1, "Log work activities on tasks")
        ], "Activity Log",
        implied_group='project.group_tasks_work_on_tasks',
        help="Allows you to compute work on tasks.")
