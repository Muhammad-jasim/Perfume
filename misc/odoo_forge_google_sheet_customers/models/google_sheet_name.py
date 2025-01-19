# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class GoogleSheetName(models.Model):
    _name = 'google.sheet.name'
    _description = 'Holds google sheet name records to search for and then write from google sheet to odoo'
    _order="create_date desc"

    name = fields.Char("Google Sheet Name")
    url = fields.Char("URL of Google Sheet")