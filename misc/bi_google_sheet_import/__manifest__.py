{
    "name": "Bi Google Sheet Import",
    "summary": "Google Sheet",
    "version": "17.0",
    "author": "Bassam Infotech LLP",
    "website": "https://www.bassaminfotech.com",
    "license": "LGPL-3",
    "depends": ["base","sale","stock","odoo_forge_google_sheet_customers","mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/clone_order_list.xml",
        # "views/clone_stock_update.xml",
        "wizard/googlesheet_wiz.xml",
        "views/res_config.xml",
        "data/ir_cron.xml",
        # "views/stock_location.xml",
        "views/sale_order.xml",
        # "views/stock_picking.xml"
    ],
    "installable": True,
    "auto_install": False,
}
