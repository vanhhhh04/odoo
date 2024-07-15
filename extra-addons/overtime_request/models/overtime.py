from odoo import fields, models, api
from odoo.exceptions import UserError
from . import constraints
from datetime import  datetime, date, time

class Employee(models.Model):
    _inherit = 'hr.employee'

    request_connect = fields.Many2one('request')
    manager = fields.Many2one('hr.employee')

class Attendance(models.Model):

    _inherit = 'hr.attendance'

    request_relationship_attendance = fields.Many2one('request')


# class LeavingTime(models.Model):
#     _inherit = "resource.calendar.leaves"

#     request_relationship_leaving_time = fields.Many2one('request')


class Resource_calender_attendance(models.Model):
    _inherit = "resource.calendar.attendance"

    request_ids = fields.Many2one('request')


class Resource_calender_leaves(models.Model):
    _inherit = "resource.calendar.leaves"

    request_ids = fields.Many2one('request')


class Request(models.Model):
    _name = "request"
    _description="over time request"

    reference = fields.Char(string="Reference", default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee',default=lambda self: self.env.user.employee_id.id,
    domain=lambda self: [('id', '=', self.env.user.employee_id.id)])    
    request_date = fields.Date()
    hour_from = fields.Selection(selection=constraints.from_hour_selection)
    hour_to = fields.Selection(selection=constraints.from_hour_selection)
    total_hours = fields.Float(compute="_compute_total_hours")
    work_description = fields.Char()
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('waiting', 'Waiting'), ('approved', 'Approved'), ('cancel','Cancel')], default='draft')
    hr_attendance = fields.One2many('hr.attendance','request_relationship_attendance', string='Attendance')
    working_time_relation = fields.One2many('resource.calendar.attendance',related='employee_id.resource_calendar_id.attendance_ids')
    leaving_time_relation = fields.One2many('resource.calendar.leaves', related='employee_id.resource_calendar_id.leave_ids')
    manager_of_employee = fields.Char(compute='_compute_manager')
    company_of_employee = fields.Char(compute='_compute_company')
    money_type_= fields.Char(compute='_compute_money_type')
    duration_type = fields.Char(compute='_compute_duration_type')
    overtime_type = fields.One2many('over.time.type', compute='_compute_overtime_type')

    @api.depends('request_date', 'leaving_time_relation')
    def _compute_overtime_type(self):
        for record in self:
            if record.request_date:
                overtime_type = False
                for leave in record.leaving_time_relation:
                    if leave.date_from <= datetime.combine(record.request_date, time.min) <= leave.date_to:
                        overtime_type = leave.overtime_type_ids[0]  
                        break
                if not overtime_type:
                    if 0 <= fields.Datetime.from_string(record.request_date).weekday() <= 5:
                        overtime_type = self.env['over.time.type'].search([('id', '=', 1)], limit=1)
                    else:
                        overtime_type = self.env['over.time.type'].search([('id', '=', 2)], limit=1)
                print(overtime_type)
                record.overtime_type = overtime_type
            else:
                record.overtime_type = None


 
    @api.depends("employee_id")
    def _compute_manager(self):
        for record in self:
            if record.employee_id.manager:
                record.manager_of_employee = record.employee_id.manager.name
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
    # request_ids = fields.Many2one('request')
    name = fields.Char()
    money_type = fields.Char(default='Cash')
    duration_type = fields.Char(default='Hour')
    rule_ids = fields.One2many('over.time.type.rules','overtime_type_ids')



class Over_Time_Type_Rule(models.Model):
    _name = "over.time.type.rules"


    overtime_type_ids = fields.Many2one('over.time.type')
    name = fields.Char(default='Default rule')
    hour_from = fields.Selection(selection=constraints.from_hour_selection, string='From')
    hour_to = fields.Selection(selection=constraints.from_hour_selection, string='To')
    rate = fields.Float(string="Rate")




    