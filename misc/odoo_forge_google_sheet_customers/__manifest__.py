# -*- coding: utf-8 -*-
{
    'name': 'Dynamic Google Sheets - Customers',
    'category': 'Tools',
    'author': 'Scott Weber',
    'summary': 'Create Google Sheets from Odoo Customers and Update Odoo Data from created Google sheet',
    'website': 'https://odooforge.com/google-sheet-odoo-customers-integration',
    "application":True,
    'category': 'Sales',
    'version': '17.0.1.0.0',
    'maintainer': 'Odoo Forge',
    'license': 'AGPL-3',
    'support': 'info@odooforge.com',
    'description': """

    
    """,
    'depends': [
        'sale','crm'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/config_settings.xml',
        'data/google_drive_data.xml',
        'wizard/googlesheet_wiz.xml',
        'views/google_sheet_name.xml',
    ],
    
    'qweb': [
        'views/map_template.xml',
    ],
    'images': ['static/description/cover-google-sheets-customers-v13-v17.gif'],
    'external_dependencies': {'python' : ['gspread','gspread_formatting','oauth2client']},
    
}
