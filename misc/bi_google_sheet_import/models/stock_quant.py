from odoo import fields, api, models

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        res = super(StockQuant, self)._get_inventory_move_values(qty, location_id, location_dest_id, out)
        if 'clone_stock_ref' in self._context:
            value = ' - ' + self._context['clone_stock_ref']
            res['name'] += value
        return res