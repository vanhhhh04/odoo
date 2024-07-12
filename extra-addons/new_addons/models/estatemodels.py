from odoo import fields, models, api
from datetime import timedelta
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users" 
    
    property_ids = fields.One2many("estate.property", "saler", string="Properties", domain=[('state', 'in', ["new", "offer received"])])
        

class Estate_property(models.Model):
    _name = "estate.property"
    _description = "estate property"
    _order = "id desc"

    name = fields.Char(required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(copy=False, default=fields.Datetime.today)
    expected_price = fields.Float(default=0)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer()
    facades = fields.Integer()
    garage = fields.Boolean(default=False)
    garden = fields.Boolean(default=False)
    garden_area = fields.Integer()
    garden_orientation = fields.Selection(
        selection=[('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West')])
    active = fields.Boolean(default=True)
    state = fields.Selection(
        selection=[('new', 'New'), ('offer received', 'Offer Received'), ('offer accepted', 'Offer Accepted'),
                   ('sold', 'Sold'), ('canceled', 'Canceled')])
    property_type_id = fields.Many2one('estate.property.type')
    saler = fields.Many2one('res.users', string='Salesperson', index=True, tracking=True,
                            default=lambda self: self.env.user)
    buyer = fields.Many2one('res.partner', string='Buyer', index=True, tracking=True)
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")
    best_price = fields.Float(compute='_compute_bestprice')
    total_area = fields.Integer(compute='_compute_total_area')

    _sql_constraints = [
        ('check_expected_price_positive', 'CHECK(expected_price > 0)', 'The expected price must be strictly positive'),
        ('check_selling_price_positive', 'CHECK(selling_price > 0)', 'The selling price must be strictly positive'),
        ('check_offer_price_positive', 'CHECK(price > 0)', 'The offer price must be strictly positive')
    ]

    @api.constrains('selling_price')
    def _check_selling_price(self):
        for record in self:
            if record.selling_price:
                if record.selling_price < (record.expected_price * 90 / 100):
                    raise ValidationError("the selling price must be at least 90% of expected price ")

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids")
    def _compute_bestprice(self):
        for record in self:
            if record.offer_ids:
                record.best_price = max(record.offer_ids.mapped('price'))
            else:
                record.best_price = 0.0

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            self.garden_area = False
            self.garden_orientation = False

    def sold_action(self):
        for record in self:
            if record.state == 'canceled':
                raise UserError('Canceled property cannot be sold', )
            else:
                record.state = 'sold'
        return True

    def Cancel_action(self):
        for record in self:
            if record.state == 'sold':
                raise UserError('Canceled property cannot be cancel')
            record.state = "canceled"
        return True


class Estate_Property_Type(models.Model):
    _name = "estate.property.type"
    _order = "name"
    name = fields.Char(required=True)
    property_ids = fields.One2many("estate.property", "property_type_id", string="Properties")
    sequence = fields.Integer('Sequence', default=1, help="Used to order  by name")
    offer_ids = fields.One2many('estate.property.offer', 'property_type_id', string="Offer_ids")
    offer_count = fields.Integer(compute="_compute_offer_count", store=True)


    @api.depends('property_ids')
    def _compute_offer_count(self):
        for prop_type in self:
            offer_count = 0
            for property in prop_type.property_ids:
                offer_count += len(property.offer_ids)
            prop_type.offer_count = offer_count
    
    def action_view_offers(self):
        self.ensure_one()
        return {
            'name': ('Offers'),
            'view_mode': 'tree,form',
            'res_model': 'estate.property.offer',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False,'update': False, 'edit': False,},
            'domain' : [("id", "in", self.offer_ids.ids)],
            'target': 'current',
        }


class Estate_Property_Tag(models.Model):
    _name = "estate.property.tag"
    _order = "name"
    name = fields.Char(required=True)
    color = fields.Integer()

    _sql_constraints = [
        ('check_unique_type_name', 'UNIQUE(name)', 'The name of type must be unique')
    ]


class Real_Estate_Property_Offer(models.Model):
    _name = "estate.property.offer"
    _order = "price desc"
    price = fields.Float()
    state = fields.Selection(copy=False, selection=[('accepted', 'Accepted'), ('refused', 'Refused')], tracking=True)
    partner_id = fields.Many2one('res.partner', required=True, index=True, tracking=True,
                                 default=lambda self: self.env.user.partner_id)
    property_id = fields.Many2one('estate.property', required=True)
    validity = fields.Integer(default=7)
    date_deadline = fields.Date(compute="_compute_datedeadline", inverse="_inverse_date_deadline")
    property_type_id = fields.Many2one("estate.property.type", related="property_id.property_type_id",
                                       string="Property Type", store=True)


    @api.model 
    def create(self, vals):
        if vals.get("property_id") and vals.get("price") :
            property = self.env['estate.property'].browse(vals['property_id'])    
            if property.offer_ids: 
                max_offer_price = max(property.mapped("offer_ids.price"))
                if vals.get("price") < max_offer_price :
                    raise UserError(f"The offer must be higher than {max_offer_price}")
            property.state = "offer received"
        return super().create(vals)

    @api.depends("validity")
    def _compute_datedeadline(self):
        for record in self:
            if record.validity:
                now = fields.Datetime.now()
                record.date_deadline = now.date() + timedelta(days=record.validity)
            else:
                record.date_deadline = fields.Date.today()

    def _inverse_date_deadline(self):
        for record in self:
            if record.date_deadline:
                now = fields.Datetime.now().date()
                record.validity = (record.date_deadline - now).days
            else:
                record.validity = 7

    def Accept_action(self):
        for record in self:
            if record.state == 'refused':
                raise UserError('Cannot accept an offer that is already refused')
            record.state = 'accepted'
            record.property_id.buyer = record.partner_id
            record.property_id.selling_price = record.price
        return True

    def Refuse_action(self):
        for record in self:
            if record.state == 'accepted':
                raise UserError('Cannot refuse an offer that is already accepted')
            record.state = 'refused'
        return True
