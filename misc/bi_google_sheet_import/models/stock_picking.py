from odoo import fields, models, _



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_clone_order = fields.Boolean('Is clone Order', related="sale_id.is_clone_order")

class PickingType(models.Model):
    _inherit = "stock.picking.type"


    def get_action_picking_paid_orders_tree(self):
        picking_ids = self.env["stock.picking"].search(
            [
                ("state", "not in", ("done", "cancel")),
                ("payment_status", "=", "paid"),
                ("picking_type_id", "in", self.ids),
                ("is_clone_order",'!=', True)
            ]
        )
        return {
            "name": _("Paid Orders"),
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "tree,form",
            "domain": [("id", "in", picking_ids.ids)],
        }