from odoo import fields, models, api, _


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_clone_stock_update = fields.Boolean('Is Clone Stock Update', default=False)