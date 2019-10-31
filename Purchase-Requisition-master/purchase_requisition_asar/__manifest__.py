# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Purchase Requisition',
    'version' : '1.0',
    'summary': 'Purchase Requisition',
    'sequence': 18,
    'description': """
This module will allow user to create purchase requisition and purchase manager can create purchase order as per requests.
    """,
    'category': 'Purchase',
    'website': '',
    'author': 'ASARTech',
    'images': [],
    'depends': ['purchase_stock', 'hr'],
    'data': [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "view/purchase_requisition_view.xml",
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
