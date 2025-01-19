import requests
from odoo import api, models, fields
import logging
from datetime import datetime
import json

_logger = logging.getLogger(__name__)


class DataReport(models.Model):
    _name = 'data.report'
    _description = 'Receive data from users'

    @api.model
    def send_data(self, action_type, error_message=None, function_name=None, additional_info=None):
        _logger.warning("----send_data starting----")
        _logger.error(error_message)
        if self.env['ir.config_parameter'].sudo().get_param('report_usage_customer'):
            module = self.env['ir.module.module'].sudo().search([('name', '=', 'odoo_forge_google_sheet_customers')], limit=1)
            module_version = module.latest_version if module else 'unknown'

            data = {
                'timestamp': datetime.now().isoformat(),
                'action_type': action_type,
                'error_message': error_message,
                'function_name': function_name,
                'module_version': module_version,
                'additional_info': additional_info
            }
            _logger.info(f"Sending data: {data}")

            try:
                headers = {'Content-Type': 'application/json'}
                response = requests.post('https://odooforge.com/api/report', json=data, headers=headers)

                if response.status_code == 200:
                    _logger.info(f'Successful request. Response: {response.text}')
                else:
                    _logger.warning(f'Failed request. Status code: {response.status_code}. Response: {response.text}')

            except requests.RequestException as e:
                _logger.error('Error sending data: %s', e)
