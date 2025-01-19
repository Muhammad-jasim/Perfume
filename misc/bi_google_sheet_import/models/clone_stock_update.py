from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CloneStockUpdate(models.Model):
    _name = "clone.stock.update"
    _description = "Clone Stock Updation List"


    sku = fields.Char('Seedsman SKU')
    product_qty = fields.Float('Quantity Available')

    def write(self,vals):
        res = super(CloneStockUpdate,self).write(vals)
        product_id = self.env['product.product'].search([('default_code','=', self.sku)], limit=1)
        location_id = self.env['stock.location'].search([('is_clone_stock_update','=', True)], limit=1)
        if not location_id:
            raise UserError(_('Configuration Location'))
        if product_id:
            if 'product_qty' in vals:
                # quant_id = self.env['stock.quant'].search([('product_id','=', product_id.id),('location_id','=', location_id.id),('quantity','=', vals['product_qty'])])
                # if not quant_id:
                #     self.env['stock.quant']._update_available_quantity(product_id,location_id,vals['product_qty'])
                data = {
                'product_id':product_id.id,
                'location_id': location_id.id,
                'inventory_quantity':vals['product_qty']
                }
                quant_id = self.env['stock.quant'].sudo().with_context(inventory_mode=True).create(data)
                quant_id.with_context(clone_stock_ref='From Clone Stock Update').action_apply_inventory()
        return res
    