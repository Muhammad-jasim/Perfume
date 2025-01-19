# -*- coding: utf-8 -*-
from oauth2client.service_account import ServiceAccountCredentials
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
import logging
from datetime import datetime
import json
import traceback

import gspread
from .format_gspread import format_google_sheet


_logger = logging.getLogger(__name__)


class GoogleSheetContactWizard(models.TransientModel):
    _inherit = 'google.sheet.customer.wiz'

    clone_order_ids = fields.Many2many(comodel_name = 'clone.order.list',string="Clone Order List")
    model_id = fields.Many2one('ir.model','Model')
    model = fields.Char(related='model_id.model')
    customer_field_ids = fields.Many2many(
        string="Fields",
        domain="[('model_id.model', '=', model)]",
        default=False
    )
    clone_stock_update_ids = fields.Many2many(comodel_name = 'clone.stock.update',string="Clone Stock Update")
    is_existing_sheet = fields.Boolean(string="Is Existing Sheet", default=True)

    def create_google_sheet_new(self):
        client = self.authenticate_google()  
        self.handle_missing_field_values()
        self.set_report_usage()
        try:
            sheet = client.create(title=self.google_sheet_name)
            self.share_google_sheet(sheet)
            worksheet = sheet.sheet1
            field_names = [field.field_description for field in self.customer_field_ids]
            headers = ['ID'] + field_names + ['Odoo URL']
            worksheet.append_row(headers)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if self.clone_order_ids:
                clone_order_added_status = self.add_clone_to_sheet(worksheet, self.clone_order_ids)
            if self.clone_stock_update_ids:
                clone_order_added_status = self.add_clone_to_sheet(worksheet, self.clone_stock_update_ids)
            if not clone_order_added_status: raise UserError(_("customers were not added to the google sheet!"))
            self.set_config_default_values()
            # store sheet in model to be searchable later by user
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet.id}"
            self.env['google.sheet.name'].create({'name': self.google_sheet_name, 'url': sheet_url})
            format_google_sheet(sheet)
            wizard = self.env['google.sheet.open.wizard'].create({'sheet_url': sheet_url})
            self.env['data.report'].send_data(
                action_type='function_call',
                error_message='None',
                function_name='create_google_sheet',
                additional_info='n/a'
            )
            return {
                'name': 'Google Sheet Created!',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'google.sheet.open.wizard',
                'res_id': wizard.id,
                'target': 'new',
            }

        except gspread.exceptions.APIError as e:
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.env['data.report'].send_data(
                action_type='error',
                error_message=str(e),
                function_name='create_google_sheet',
                additional_info='n/a'
            )      
            raise UserError(_(f"Google API Error: Please check the logs for more details. {error_message}"))

        except Exception as e:
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.env['data.report'].send_data(
                action_type='error',
                error_message=str(e),
                function_name='create_google_sheet',
                additional_info='n/a'
            )
            raise UserError(_(f"Unexpected Error: Please check the logs for more details. {error_message}"))


    def add_clone_to_sheet(self, worksheet, clone_order) -> bool:
        _logger.info(f"--- Starting 'add_clone_order_to_sheet' - Clone Record to process {clone_order}")
        row_number = 0    
        for clone_order in clone_order:
            row_number += 1
            clone_order_data = [clone_order.id]  
            # clone_order_data.append(self.generate_public_image(clone_order=clone_order))
            for field in self.customer_field_ids:
                field_value = getattr(clone_order, field.name, None)  
                if field_value is None or field_value is False: field_value = ''
                if str(field_value).startswith('+'): field_value = field_value[len('+'):]
                # Check if field_value is a recordset (relational field)
                if isinstance(field_value, models.BaseModel):
                    field_value = field_value.display_name if field_value else ''
                elif isinstance(field_value, bytes):
                    try:
                        field_value = field_value.decode('utf-8')
                    except UnicodeDecodeError:
                        error_message = f"Decoding error for clone_order {clone_order.id} field {field.name}"
                        self.env['data.report'].send_data(
                            action_type='error',
                            error_message=error_message,
                            function_name='add_clone_order_to_sheet',
                            additional_info='n/a'
                        )
                        field_value = "Error: Undecodable bytes"
                clone_order_data.append(field_value)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            odoo_url = f"{base_url}/web#id={clone_order.id}&view_type=form&model=res.partner"
            clone_order_data.append(odoo_url)
            try:
                worksheet.append_row(clone_order_data, value_input_option='USER_ENTERED')
            except Exception as e:
                _logger.error(f"Error appending row for clone_order {clone_order.id}: {e}")
                self.env['data.report'].send_data(
                    action_type='error',
                    error_message=str(e),
                    function_name='add_clone_orders_to_sheet',
                    additional_info='n/a'
                )
        
        worksheet.update_cell(row_number + 5, 2, 'For syncing purposes, ID column and Row titles should not be changed.')

        _logger.info("Google Sheet created and populated successfully.")
        return True

    def handle_missing_field_values(self):
        if not self.google_sheet_name:
            raise UserError(_(f"Please add a Google Sheet Name."))
        if not self.email_share_list:
            raise UserError(_("Please add Google email addresses to share the sheet with!"))
        if not self.model_id:
            raise UserError(_("Please add Model"))
        if self.model_id:
            if not self.clone_order_ids and self.model == 'clone.order.list':
                raise UserError(_("Please add clone order to be added as google sheet rows!"))
            if not self.clone_stock_update_ids and self.model == 'clone.stock.update':
                raise UserError(_("Please add clone stock to be added as google sheet rows!"))
        # if not self.partner_ids:
        #     raise UserError(_("Please add customers to be added as google sheet rows!"))
        # if not self.product_field_ids:
        #     raise UserError(_("Please add customer fields to be added as google sheet columns!"))


    def set_config_default_values(self):
        self.env['ir.config_parameter'].sudo().set_param('google.sheet.email', self.email_share_list)
        default_field_ids_str = ','.join(map(str, self.customer_field_ids.ids))
        self.env['ir.config_parameter'].sudo().set_param('google.sheet.customer.wiz.default_field_ids', default_field_ids_str)

    def share_google_sheet(self, sheet):
        """ 
        share google sheet to email list
        """
        for email_address in self.email_share_list.split(","):
            email_address = email_address.strip() 
            if email_address:  
                sheet.share(email_address, perm_type='user', role='writer')
            else:
                _logger.warning("Skipped an empty email address.")

    def generate_public_image(self, customer):
        attachment_obj = self.env['ir.attachment']
        try:
            if customer.avatar_256:
                image_name = customer.display_name or f"customer_{customer.id}_Image"
                make_public_image = attachment_obj.create({
                    'name': image_name,
                    'type': 'binary',
                    'public': True,
                    'datas': customer.avatar_256,
                    'mimetype': 'image/png'
                })
                public_image_id = make_public_image.id
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                image_link = f'=image("{base_url}/web/content/{public_image_id}/avatar_256.png")'
                _logger.warning(f"image_link: {image_link}")
                return image_link
            else:
                _logger.warning("No image found for customer with display_name: %s" % customer.display_name)
                return 'No Image Available'
        except Exception as e:
            error_message = f"Error creating public image attachment: {str(e)}" 
            self.env['data.report'].send_data(
                    action_type='error',
                    error_message=error_message,
                    function_name='generate_public_image',
                    additional_info='n/a'
                )
            return 'No Image Available'

    
    def open_odoo_list_view(self):
        """Open Google Sheet customers in Odoo menu item"""
        try:
            google_spread_sheet_to_sync_from = self.google_spread_sheet_to_sync_from.name
            if not google_spread_sheet_to_sync_from: raise UserError(_("Please select a google sheet to open."))
            client = self.authenticate_google()
            existing_sheet = client.open(google_spread_sheet_to_sync_from)
            if not existing_sheet: raise UserError(_("Please select a google sheet to open."))
            existing_sheet_url = "https://docs.google.com/spreadsheets/d/%s" % existing_sheet.id

            sheet1 = existing_sheet.get_worksheet(0)
            gs_records_list = sheet1.get_all_records()
            
            partner_ids = []
            for customer in gs_records_list:
                if customer['ID']: partner_ids.append(customer['ID'])
                        
            tree_view_id = self.env.ref('odoo_forge_google_sheet_customers.res_partner_custom_tree_gs').id
            form_view_id = self.env.ref('base.view_partner_form').id  
            kanban_view_id = self.env.ref('base.res_partner_kanban_view').id  
            self.env['data.report'].send_data(
                    action_type='function_call',
                    error_message='None',
                    function_name='open_odoo_list_view',
                    additional_info='n/a'
                )
            return {
                'name': f'Customers from Google Sheet, {self.google_spread_sheet_to_sync_from.display_name}.',
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form,kanban',
                'res_model': 'res.partner',
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form'), (kanban_view_id, 'kanban')],
                'domain': [('id', 'in', partner_ids)],
            }
        except Exception as e:
            error_message = f"Error opening customer's in Odoo: {str(e)}" 
            self.env['data.report'].send_data(
                    action_type='error',
                    error_message=error_message,
                    function_name='open_odoo_list_view',
                    additional_info='n/a'
                )

    def open_google_sheet_external(self):
        """Open Previously Created Google Sheet menu item
        """
        google_spread_sheet_to_sync_from = self.google_spread_sheet_to_sync_from.name
        if not google_spread_sheet_to_sync_from:
            raise UserError(_("Please select a google sheet to open."))
        client = self.authenticate_google()
        existing_sheet = client.open(google_spread_sheet_to_sync_from)
        if not existing_sheet:
            raise UserError(_("Please select a google sheet to open."))
        existing_sheet_url = "https://docs.google.com/spreadsheets/d/%s" % existing_sheet.id
        _logger.info("Opening google sheet at %s" % existing_sheet_url)         
        return {
            'type': 'ir.actions.act_url',
            'url': existing_sheet_url,
            'target': 'new',
        }

    def sync_google_sheet(self):
        """Open Previously Created Google Sheet menu item
        """
        client = self.authenticate_google()

        existing_sheet = client.open(self.google_spread_sheet_to_sync_from.name)
        if not existing_sheet:
            raise UserError(_("Please select a google sheet to sync."))
        # Note possible error with get_worksheet if user adds ID field manually. Column titles must be unique.
        sheet1 = existing_sheet.get_worksheet(0)
        gs_records_list = sheet1.get_all_records()
        
        model = self._context.get('model')
        if model == "clone.stock.update":
            new_gs_records_list = []
            skus = list(set([i['Seedsman SKU'] for i in gs_records_list]))
            for sku in skus:
                if sku not in ['','Seedsman SKU','n/a']:
                    val = sum([int(i['1']) for i in gs_records_list if i['Seedsman SKU'] == sku and i['1']])
                    new_gs_records_list.append({'Seedsman SKU':sku,'Quantity Available':str(val)})

            gs_records_list = new_gs_records_list
        model_fields = self.env['ir.model.fields'].search([('model', '=', self._context.get('model'))])
        field_mapping = {field.field_description: field.name for field in model_fields}
        reverse_field_mapping = {field.name: field.field_description for field in model_fields}
        updated_report = ""
        relational_field_names = {
            field.name for field in model_fields if field.ttype in ['many2one', 'one2many', 'many2many']
        }
        for gs_record in gs_records_list:
            try:
                if not self.is_existing_sheet:
                    odoo_id = gs_record.get('ID')
                    if not odoo_id or odoo_id == 'For syncing purposes, ID column must not be changed.':
                        continue 
                    odoo_matching_customer = self.env[self._context.get('model')].search([('id', '=', odoo_id)], limit=1)
                    if not odoo_matching_customer:
                        _logger.warning(f"No matching record found for ID {odoo_id}")
                        continue

                    update_vals = {}
                    for key, value in gs_record.items():
                        if key not in ['ID','Image','Barcode']:  # Skip these columns since they shouldn't be changed.
                            field_name = field_mapping.get(key)
                            if field_name and field_name not in relational_field_names:
                                update_vals[field_name] = value
                            else:
                                _logger.warning(f"Skipped updating relational or excluded field '{key}' for customer ID {odoo_id}.")

                    odoo_matching_customer.write(update_vals)
                    updated_report_for_customer = self.dict_to_html_list_string(update_vals, reverse_field_mapping)
                    # _logger.info(f"customer {odoo_id} updated with {updated_report_for_customer}")
                    # odoo_matching_customer.message_post(body=f"Data updated from Google Sheet Sync: <br/>{updated_report_for_customer}")
                    updated_report += updated_report_for_customer + "<br/><br/>"
                else:
                    model = self._context.get('model')
                    if model == "clone.stock.update":
                        SKU = gs_record.get('Seedsman SKU')
                        if not SKU:
                            continue 
                        odoo_matching_id = self.env[self._context.get('model')].search([('sku', '=', SKU)], limit=1)
                        if not odoo_matching_id:
                            _logger.warning(f"No matching record found for SKU {SKU}")
                            continue

                        update_vals = {}
                        for key, value in gs_record.items():
                            if key not in ['Seedsman SKU']:  # Skip these columns since they shouldn't be changed.
                                field_name = field_mapping.get(key)
                                if field_name and field_name not in relational_field_names:
                                    update_vals[field_name] = value
                                else:
                                    _logger.warning(f"Skipped updating relational or excluded field '{key}' for Product SKU {SKU}.")

                        odoo_matching_id.write(update_vals)
                        updated_report_for_stock = self.dict_to_html_list_string(update_vals, reverse_field_mapping)
                        # _logger.info(f"customer {odoo_id} updated with {updated_report_for_customer}")
                        # odoo_matching_customer.message_post(body=f"Data updated from Google Sheet Sync: <br/>{updated_report_for_customer}")
                        updated_report += updated_report_for_stock + "<br/><br/>"
                    if model == "clone.order.list":
                        order_name = gs_record.get('ORDER #')
                        SKU = gs_record.get('STRAIN CODE')
                        if not SKU and not order_name:
                            continue 
                        odoo_matching_id = self.env[self._context.get('model')].search([('sku', '=', SKU),('order_name','=',order_name)], limit=1)
                        if not odoo_matching_id:
                            _logger.warning(f"No matching record found for Order No {order_name} and SKU {SKU}")
                            continue

                        update_vals = {}
                        for key, value in gs_record.items():
                            if key not in ['STRAIN CODE','ORDER #']:  # Skip these columns since they shouldn't be changed.
                                field_name = field_mapping.get(key)
                                if field_name and field_name not in relational_field_names:
                                    update_vals[field_name] = value
                                    if field_name == 'date_order' and value:
                                        if isinstance(datetime.strptime(json.loads(value),"%Y-%m-%d %H:%M:%S"), datetime):
                                            update_vals[field_name] = datetime.strptime(json.loads(value),"%Y-%m-%d %H:%M:%S").date()
                                else:
                                    _logger.warning(f"Skipped updating relational or excluded field '{key}' for {value}.")

                        odoo_matching_id.write(update_vals)
                        updated_report_for_order_list = self.dict_to_html_list_string(update_vals, reverse_field_mapping)
                        # _logger.info(f"customer {odoo_id} updated with {updated_report_for_customer}")
                        # odoo_matching_customer.message_post(body=f"Data updated from Google Sheet Sync: <br/>{updated_report_for_customer}")
                        updated_report += updated_report_for_order_list + "<br/><br/>"
                    

            except Exception as e:
                error_message = f"Error updating customer from Google Sheet: {e}"
                self.env['data.report'].send_data(
                    action_type='error',
                    error_message=error_message,
                    function_name='sync_google_sheet',
                    additional_info='n/a'
                )
                raise UserError(_(f"Error updating record from Google Sheet: {e}. Please fix the record and try again.")) 

        message_id = self.env['google.sheet.customer.wiz'].create({'message': _(f"Data updated from Google Sheet Sync: <br/>{updated_report}")})
        _logger.info("Google Sheet sync complete.")
        self.env['data.report'].send_data(
                action_type='function_call',
                error_message='None',
                function_name='sync_google_sheet',
                additional_info='n/a'
            )
        return {
                        'name': 'Odoo Data Updated!',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'google.sheet.customer.wiz',
                        'view_id': self.env.ref('odoo_forge_google_sheet_customers.wizard_return_success_message_customer').id,
                        'res_id': message_id.id,
                        'target': 'new',
                    }
        

    def dict_to_html_list_string(self, input_dict, field_mapping=None):
        """Convert a dictionary to a bulleted HTML list as a string, using field descriptions as keys."""
        bulleted_list_string = ""
        for key, value in input_dict.items():
            friendly_key = field_mapping.get(key, key) if field_mapping else key
            bulleted_list_string += f"- {friendly_key}: {value} <br/>"
        return bulleted_list_string

    
    def authenticate_google(self):
        param_record = self.env['ir.config_parameter'].search([('key', '=', 'google.sheet.json.customer')], limit=1)
        param_record_url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if param_record:
            param_record_url = f"{base_url}/web#id={param_record.id}&view_type=form&model=ir.config_parameter" 
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']       
        try:
            google_json_file = self.env['ir.config_parameter'].sudo().get_param(
                'google.sheet.json.customer')
            google_credentials_dict = json.loads(google_json_file)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials_dict, scope)
            client = gspread.authorize(creds)
            _logger.info(f"Authorize google success - {client}")
            return client
        except json.decoder.JSONDecodeError as e:
            self.env['data.report'].send_data(
                    action_type='error',
                    error_message=str(e),
                    function_name='authenticate_google',
                    additional_info='n/a'
                )
            raise UserError(_(f"Please make sure the google.sheet.json.customer value is the google json! Go to this link to set it or go to the google sheet settings to upload the json file. {param_record_url}"))
        except TypeError as e:
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.env['data.report'].send_data(
                    action_type='error',
                    error_message=error_message,
                    function_name='authenticate_google',
                    additional_info='n/a'
                )
            raise UserError(_(f"Please make sure the google.sheet.json.customer value is the google json! Go to this link to set it or go to the google sheet settings to upload the json file. {param_record_url} --- {error_message}"))
        except Exception as e:
            error_message = ''.join(traceback.format_exception(None, e, e.__traceback__))
            self.env['data.report'].send_data(
                    action_type='error',
                    error_message=error_message,
                    function_name='authenticate_google',
                    additional_info='n/a'
                )
            raise UserError(_(f"Unexpected Error: {error_message}"))
        


    def create_row_clone_order(self,val):
        google_sheet_id = self.env['google.sheet.name'].search([('is_order_sheet','=', True)],limit=1)
        client = self.authenticate_google()
        if not google_sheet_id:
            raise UserError(_('Configuration Google Clone Order Sheet in Google Sheet Master'))

        existing_sheet = client.open(google_sheet_id.name)
        if not existing_sheet:
            raise UserError(_("Please select a google sheet to sync."))
        worksheet = existing_sheet.sheet1
        self.add_clone_to_sheet_new(worksheet, val)
        return True


    def add_clone_to_sheet_new(self, worksheet, clone_order) -> bool:
        _logger.info(f"--- Starting 'add_clone_order_to_sheet' - Clone Record to process {clone_order}")
        row_number = len(worksheet.get_all_values())
        col_number = 0 
        for clone_order in clone_order:
            row_number += 1
            clone_order_data = []  
            # clone_order_data.append(self.generate_public_image(clone_order=clone_order))
            for field in worksheet.get_all_values()[0]:
                field = self.env['ir.model.fields'].search([('field_description','=', field)], limit=1)
                field_value = field and getattr(clone_order, field.name, None) or ""  
                if field_value is None or field_value is False: field_value = ''
                if str(field_value).startswith('+'): field_value = field_value[len('+'):]
                # Check if field_value is a recordset (relational field)
                if isinstance(field_value, datetime):
                    field_value = json.dumps(field_value.strftime("%Y-%m-%d %H:%M:%S"))
                if isinstance(field_value, models.BaseModel):
                    field_value = field_value.display_name if field_value else ''
                elif isinstance(field_value, bytes):
                    try:
                        field_value = field_value.decode('utf-8')
                    except UnicodeDecodeError:
                        error_message = f"Decoding error for clone_order {clone_order.id} field {field and field.name or ''}"
                        self.env['data.report'].send_data(
                            action_type='error',
                            error_message=error_message,
                            function_name='add_clone_order_to_sheet',
                            additional_info='n/a'
                        )
                        field_value = "Error: Undecodable bytes"
                clone_order_data.append(field_value)

            try:
                worksheet.insert_row(clone_order_data,row_number)
                clone_order.is_updated_sheet = True
            except Exception as e:
                _logger.error(f"Error appending row for clone_order {clone_order.id}: {e}")
                self.env['data.report'].send_data(
                    action_type='error',
                    error_message=str(e),
                    function_name='add_clone_orders_to_sheet',
                    additional_info='n/a'
                )
                
            # worksheet.update_cell(row_number + 5, 2, 'For syncing purposes, ID column and Row titles should not be changed.')

            _logger.info("Google Sheet created and populated successfully.")
            return True
        


    def update_clone_order_from_sheet(self):
        google_sheet_id = self.env['google.sheet.name'].search([('is_order_sheet','=', True)],limit=1)
        if not google_sheet_id:
            raise UserError(_('Configuration Google Clone Order Sheet in Google Sheet Master'))
        
        update_clone_order_wiz_id = self.create({
            'google_spread_sheet_to_sync_from':google_sheet_id.id,
            'is_existing_sheet': True
        })
        update_clone_order_wiz_id.with_context(model='clone.order.list').sync_google_sheet()

        return True
    
    def update_clone_stock_from_sheet(self):
        google_sheet_id = self.env['google.sheet.name'].search([('is_stock_sheet','=', True)],limit=1)
        if not google_sheet_id:
            raise UserError(_('Configuration Google Clone Stock Sheet in Google Sheet Master'))
        
        update_clone_stock_wiz_id = self.create({
            'google_spread_sheet_to_sync_from':google_sheet_id.id,
            'is_existing_sheet': True
        })
        update_clone_stock_wiz_id.with_context(model='clone.stock.update').sync_google_sheet()

        return True
    



class GoogleSheetOpenWizard(models.TransientModel):
    _name = 'google.sheet.open.wizard'
    _description = 'Google Sheet Open Wizard'

    sheet_url = fields.Char("Sheet URL", readonly=True)

    def open_google_sheet(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.sheet_url,
            'target': 'new',
        }