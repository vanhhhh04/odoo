from odoo import fields, models, api
from odoo.exceptions import UserError
from . import constraints


class Employee(models.Model):
    _inherit = 'res.users'

    # working_time = fields.One2many(
    #     'resource.calendar.attendance', 'working_time_corresponse_company', string='Working time')
    # leaving_time = fields.One2many(
    #     'resource.calendar.leaves', 'leaving_time_corresponse_company', string="Global leaves")
    request_id = fields.One2many('request', 'employee_id')


class Working_time(models.Model):
    _inherit = "resource.calendar.attendance"

    # working_time_corresponse_company = fields.Many2one("res_users")

    request_relationship_working_time = fields.Many2one('request')


class Leaving_time(models.Model):
    _inherit = "resource.calendar.leaves"

    # leaving_time_corresponse_company = fields.Many2one("res.users")

    request_relationship_leaving_time = fields.Many2one('request')




class Request(models.Model):
    _name = "request"

    employee_id = fields.Many2one('res.users', name='Employee')
    request_date = fields.Date()
    hour_from = fields.Selection(selection=constraints.from_hour_selection)
    hour_to = fields.Selection(selection=constraints.from_hour_selection)
    total_hours = fields.Float(compute="_compute_total_hours")
    work_description = fields.Char()
    state = fields.Selection(selection=[(
        'draft', 'Draft'), ('waiting', 'Waiting'), ('approved', 'Approved')], default='draft')
    working_time_relation = fields.One2many('resource.calendar.attendance','request_relationship_working_time')
    leaving_time_relation = fields.One2many('resource.calendar.leaves','request_relationship_leaving_time')

    def action_view_working_time(self):
        self.ensure_one()
        return {
            'name': ('Working_Time'),
            'view_mode': 'tree,form',
            'res_model': 'resource.calendar.attendance',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False,'update': False, 'edit': False,},
            'domain' : [("id", "in", self.request_ids.ids)],
            'target': 'current',
        }

    def action_view_leaving_time(self):
        self.ensure_one()
        return {
            'name': ('Leaving_Time'),
            'view_mode': 'tree,form',
            'res_model': 'resource.calendar.leaves',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False,'update': False, 'edit': False,},
            'domain' : [("id", "in", self.request_ids.ids)],
            'target': 'current',
        }


    @api.depends("hour_from", "hour_to")
    def _compute_total_hours(self):
        for record in self:
            if record.hour_from and record.hour_to:
                if int(record.hour_to) < int(record.hour_from):
                    raise UserError("Hour to need to be bigger than Hour From")
                period = int(record.hour_to) - int(record.hour_from)
                period_float = float(period/60)
                record.total_hours = period_float
            else:
                record.total_hours = 0.0

    def submit_action(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('cannot submit')
            else:
                record.state = 'waiting'
        return True


class Over_Time_Type(models.Model):

    _name = "over.time.type"

    money_type = fields.Char(default='Cash')
    duration_type = fields.Char(default='Hour')
