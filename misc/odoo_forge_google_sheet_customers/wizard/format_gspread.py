# -*- coding: utf-8 -*-
import gspread
import os
import logging
from datetime import datetime, timedelta
import sys
import time
from gspread_formatting import *

def format_google_sheet(sheet):
    worksheet = sheet.sheet1

    title_fmt = cellFormat(
        backgroundColor=color(23,32,42),
        textFormat=textFormat(bold=True, foregroundColor=color(229,231,233),fontSize=8),
        horizontalAlignment='CENTER',verticalAlignment='MIDDLE',wrapStrategy='WRAP',
        )
    body_fmt = cellFormat(
        horizontalAlignment='CENTER', verticalAlignment='MIDDLE',wrapStrategy='WRAP', textFormat=textFormat(fontSize=8)
        )

    read_only_fmt = cellFormat(
        backgroundColor=color(28,20,10),
        textFormat=textFormat(bold=True, italic=True, foregroundColor=color(229,231,233),fontSize=8))
    
    last_column_with_text = len(worksheet.row_values(1)) 
    column_letter = col_num_to_letter(last_column_with_text)

    format_cell_range(worksheet, f'A1:{column_letter}1', title_fmt)
    format_cell_range(worksheet, f'A2:{column_letter}1000', body_fmt)
    format_cell_range(worksheet, f'A1:A1000', read_only_fmt)

    sheet_id = worksheet._properties['sheetId']  
    request_body = {
        'requests': [  
            {
                'addProtectedRange': {
                    'protectedRange': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,  # Start at the first row
                            'endRowIndex': 1000,  # Protect up to row 1000
                            'startColumnIndex': 0,  # Start at the first column (A)
                            'endColumnIndex': 1   # End at the second column (exclusive of B)
                        },
                        'description': 'Protecting first column',  
                        'warningOnly': False,  
                        'requestingUserCanEdit': True,  
                    }
                }
            }
        ]
    }

    sheet.batch_update(request_body)  
    set_row_height(worksheet, '1', 100)
    set_row_height(worksheet, '2:1000', 80)
    set_frozen(worksheet, rows=1)


def col_num_to_letter(col_num):
    """Convert a numeric column number to a letter."""
    letters = ''
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters