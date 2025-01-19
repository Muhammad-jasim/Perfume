from odoo import fields, models, api,_

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_update_to_clone_order_list = fields.Boolean('Is Update To Clone Order List', default=False)


    def create_clone_order(self):
        order_clone_import = (self.env["ir.config_parameter"].sudo().get_param("bi_google_sheet_import.import_clone_order_prefix")) or ""
        for line in self.search([('order_id.is_clone_order','=', True),('state','=','sale'),('is_update_to_clone_order_list','=', False)]).filtered(lambda l:l.product_id.detailed_type == 'product' and order_clone_import in l.order_id.name):
            payment_status = line.order_id.picking_ids.filtered(lambda p:p.payment_status == 'paid')
            if payment_status:
                clone_order_id = self.env['clone.order.list'].search([('order_name','=', line.order_id.name),('sku','=', line.product_id.default_code)])
                if not clone_order_id:
                    clone_order_id = self.env['clone.order.list'].create({
                        'order_id': line.order_id.id,
                        'order_name': line.order_id.name,
                        'partner_id':line.order_id.partner_shipping_id.id,
                        'sku':line.product_id.default_code,
                        'quantity': line.product_uom_qty,
                        'price':line.price_unit or 0.00,
                        'picking_id': payment_status[0].id or False,
                        'paid' : "YES",
                        'product_name':line.product_id.name
                    })
                    line.is_update_to_clone_order_list = True
                else:
                    continue
    

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_clone_order = fields.Boolean('Is Clone Order', default=False)


    @api.model_create_multi
    def create(self, vals_list):
        res = super(SaleOrder,self).create(vals_list)
        order_clone_prefix = (self.env["ir.config_parameter"].sudo().get_param("bi_google_sheet_import.import_clone_order_prefix")) or ""
        for rec in res:
            if order_clone_prefix in rec.name:
                rec.is_clone_order = True
        return res