from odoo import models, fields, api
import base64

class CustomOdooForgeSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_sheet_json_data = fields.Binary(string='Google Sheet JSON File')
    google_sheet_json_name = fields.Char(string='File Name')
    module_google_sheet_json = fields.Boolean("Google Sheets JSON")
    report_usage = fields.Boolean(string="Enable Reporting")

    @api.model
    def set_values(self):
        super(CustomOdooForgeSettings, self).set_values()
        self.set_google_sheet_json() 
        self.env['ir.config_parameter'].sudo().set_param('report_usage_customer', str(self.report_usage))

    def set_google_sheet_json(self):
        if self.google_sheet_json_data:
            decoded_data = base64.b64decode(self.google_sheet_json_data)
            self.env['ir.config_parameter'].sudo().set_param('google.sheet.json.customer', decoded_data.decode('utf-8'))

    @api.model
    def get_values(self):
        res = super(CustomOdooForgeSettings, self).get_values()
        report_usage_param = self.env['ir.config_parameter'].sudo().get_param('report_usage_customer')
        res.update(
            report_usage=(report_usage_param == 'True')
        )
        return res

    @api.model
    def set_report_usage(self, value):
        self.env['ir.config_parameter'].sudo().set_param('report_usage_customer', value)