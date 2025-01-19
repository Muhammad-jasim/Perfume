from odoo import fields, models, api, _


class CloneOrderList(models.Model):
    _name = "clone.order.list"
    _rec_name = "order_id"
    _description = "Clone Order List"


    order_id = fields.Many2one('sale.order','Order No')
    order_name = fields.Char('ORDER #')
    partner_id = fields.Many2one('res.partner', "Customer")
    partner_name = fields.Char("FIRST NAME",related='partner_id.name')
    street = fields.Char('Address 1', related="partner_id.street")
    street2 = fields.Char('Address 2', related="partner_id.street2")
    country_id = fields.Many2one('res.country', 'Country', related="partner_id.country_id")
    zip_code = fields.Char('Zip Code', related="partner_id.zip")
    tracking_no = fields.Char('TRACKING #')
    sku = fields.Char('STRAIN CODE')
    picking_id = fields.Many2one('stock.picking', 'Picking')
    is_updated_sheet = fields.Boolean('Is Updated In Sheet', default= False)
    is_update_tracking_ref = fields.Boolean('Is Update Tracking Ref', default=False)
    shipping_address = fields.Char('SHIPPING ADDRESS', compute='compute_shipping_address')
    date_order = fields.Datetime('DATE ORDERED', related="order_id.date_order")
    quantity = fields.Float('QUANTITY')
    price = fields.Float('PRICE')
    paid = fields.Char('Paid')
    city = fields.Char('City', related="partner_id.city")
    state_id = fields.Many2one('res.country.state','State', related="partner_id.state_id")
    product_name = fields.Char('Strain')

    @api.depends('street', 'street2','country_id','zip_code')
    def compute_shipping_address(self):
        for rec in self:
            address = ""
            if rec.street:
                street = rec.street + ", "
                address += street
            if rec.street2:
                street2 = rec.street2 + ", "
                address += street2
            if rec.city:
                city = rec.city + ", "
                address += city
            if rec.state_id:
                state = rec.state_id.name + ", "
                address += state
            if rec.country_id:
                country_id = rec.country_id.name + ", "
                address += country_id
            if rec.zip_code:
                zip_code = rec.zip_code
                address += zip_code
            rec.shipping_address = address


    @api.model
    def create(self, vals):
        res = super(CloneOrderList, self).create(vals)
        transfer = self.env["google.sheet.customer.wiz"].create_row_clone_order(res)
        return res   
    

    def update_picking_tracking_ref(self):
        for order in self.search([('is_update_tracking_ref','=', True)]).filtered(lambda l:l.tracking_no):
            pass


class GoogleSheetMaster(models.Model):
    _inherit = 'google.sheet.name'

    is_order_sheet = fields.Boolean('Is Order Sheet', default=False)
    is_stock_sheet = fields.Boolean('Is Shock Sheet', default=False)