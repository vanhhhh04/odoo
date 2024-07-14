from odoo import fields, models, api
from odoo.exceptions import UserError
from . import constraints


class Employee(models.Model):
    _inherit = 'res.users'

    # email = fields.Char(string="Email")
    request_connect = fields.Many2one('request')
    manager = fields.Many2one('res.users')



class WorkingTime(models.Model):
    _inherit = "resource.calendar.attendance"


    request_relationship_working_time = fields.Many2one(
        'request')



class LeavingTime(models.Model):
    _inherit = "resource.calendar.leaves"

    request_relationship_leaving_time = fields.Many2one(
        'request')


class Request(models.Model):
    _name = "request"
    _description="over time request"

    reference = fields.Char(string="Reference", default='New')
    employee_id = fields.Many2one('res.users', name='Employee')
    request_date = fields.Date()
    hour_from = fields.Selection(selection=constraints.from_hour_selection)
    hour_to = fields.Selection(selection=constraints.from_hour_selection)
    total_hours = fields.Float(compute="_compute_total_hours")
    work_description = fields.Char()
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('waiting', 'Waiting'), ('approved', 'Approved'), ('cancel','Cancel')], default='draft')
    working_time_relation = fields.One2many('resource.calendar.attendance', 'request_relationship_working_time', string="Working Time Relation")
    leaving_time_relation = fields.One2many('resource.calendar.leaves', 'request_relationship_leaving_time', string="Leaving Time Relation")
    manager_of_employee = fields.Char(compute='_compute_manager')
    employee_id_email = fields.Char(compute='_compute_employee_email')
    company_of_employee = fields.Char(compute='_compute_company')


    @api.depends("employee_id")
    def _compute_employee_email(self):
        for record in self:
            record.employee_id_email = record.employee_id.login

    @api.depends("employee_id")
    def _compute_manager(self):
        for record in self:
            if record.employee_id.manager:
                record.manager_of_employee = record.employee_id.manager.login
            else :
                record.manager_of_employee = ""
    @api.depends("employee_id")
    def _compute_company(self):
        for record in self:
            if record.employee_id.company_id:
                record.company_of_employee = record.employee_id.company_id.name
            else :
                record.company_of_employee = ""


    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if not val.get('reference') or val['reference'] == 'New':
                val['reference'] = self.env['ir.sequence'].next_by_code('request')
        return super().create(vals)




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

    def cancel_action(self):
        for record in self :
            if record.state == 'approved':
                raise UserError('Your request was approved!')
            record.state = 'cancel'

    def approved_action(self):
        for record in self :
            if record.state == 'cancel':
                raise UserError('Your request was canceled !')
            elif record.state != 'waiting':
                raise UserError('You have to submit the request')
            else :
                record.state = 'approved'



class Over_Time_Type(models.Model):

    _name = "over.time.type"

    money_type = fields.Char(default='Cash')
    duration_type = fields.Char(default='Hour')
