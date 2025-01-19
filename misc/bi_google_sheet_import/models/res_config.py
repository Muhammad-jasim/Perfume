from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    import_clone_order_prefix = fields.Char('Import Clone Order Prefix',config_parameter="bi_google_sheet_import.import_clone_order_prefix")
