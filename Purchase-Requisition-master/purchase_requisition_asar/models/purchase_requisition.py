# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from datetime import datetime


class PurchaseRequisition(models.Model):
    _name = "purchase.requisitions"
    _description = "Purchase Requisition"

    name = fields.Char("Name", required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", help="Employee Related To Purchase Requisition.")
    department_id = fields.Many2one("hr.department", string="Department", help="Department to handel requisition.")
    user_id = fields.Many2one("res.users", string="Responsible", help="Responsible Person to handle requisition.")
    requisition_date = fields.Date("Requisition Date")
    received_date = fields.Date("Received Date")
    requisition_dateline = fields.Date("Requisition Deadline")
    reason_for_requisitions = fields.Text("Reason For Requisition")
    confirmed_by = fields.Many2one("res.users", string="Confirmed By", help="User who confirmed requisition.")
    department_manager = fields.Many2one("res.users", string="Department Manager Approved By Rejected by")
    confirmed_date = fields.Date("Confirmed Date")
    department_approval_date = fields.Date("Department Approval Date")
    source_location_id = fields.Many2one("stock.location", "Source Location")
    dest_location_id = fields.Many2one("stock.location", "Destination Location")
    purchase_order_ids = fields.Many2many("purchase.order", "requisition_purchase_rel", "purchase_id", "req_id",
                                          string="Purchase Orders")
    picking_ids = fields.Many2many("stock.picking", "requisition_picking_rel", "picking_id", "req_id",
                                   string="Pickings")
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting_department_approval', 'Waiting Department Approval'),
                              ('waiting_ir_approval', 'Waiting IR Approval'),
                              ('approved', 'Approved'),
                              ('purchase_order_created', 'Purchase Order Created'),
                              ('received', 'Received'),
                              ('cancel', 'Cancel')], string="State", default="draft")
    requisition_line_ids = fields.One2many("purchase.requisitions.line", "purchase_requisition_id",
                                           string="Requisition Lines")
    purchase_order_count = fields.Integer("Purchase Order Count", compute="get_purchase_order_count", store=False)
    picking_count = fields.Integer("Picking Count", compute="get_picking_count", store=False)

    def get_purchase_order_count(self):
        for purchase_requisition in self:
            purchase_requisition.purchase_order_count = len(self.purchase_order_ids.ids)

    def get_picking_count(self):
        for purchase_requisition in self:
            purchase_requisition.picking_count += len(purchase_requisition.purchase_order_ids.picking_ids)

    def action_confirm(self):
        res = self.write({
            'state': 'waiting_department_approval',
            'confirmed_by': self.env.user.id,
            'confirmed_date': datetime.now()
        })
        return res

    def action_approve_department(self):
        res = self.write({'state': 'waiting_ir_approval',
                          'department_approval_date': datetime.now()})
        return res

    def action_approve_ir(self):
        res = self.write({'state': 'approved'})
        return res

    def action_create_purchase_orders(self):
        res = self.write({'state': 'purchase_order_created'})
        self.create_purchase_orders()
        return res

    def action_receive_products(self):
        self.purchase_order_ids.button_confirm()
        res = self.write({'state': 'received'})
        return res

    def action_cancel(self):
        res = self.write({'state': 'action_cancel'})
        return res

    def create_purchase_orders(self):
        purchase_obj = self.env["purchase.order"]
        purchase_order_data = self.get_purchase_order_data()
        po_ids = []
        for vendor_id, po_data in purchase_order_data.items():
            purchase_order = purchase_obj.create(po_data)
            po_ids.append(purchase_order.id)
        self.purchase_order_ids = purchase_obj.browse(po_ids)

    def get_purchase_order_data(self):
        purchase_order_line_obj = self.env["purchase.order.line"]
        purchase_order_data = {}
        for line in self.requisition_line_ids:
            if not line.vendor_id:
                raise Warning(_("Vendors not set in purchase requisition lines."))
            po_line_vals = {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'product_uom': line.product_id.uom_po_id.id,
                    'price_unit': line.product_id.standard_price,
                }
            tmp_line = purchase_order_line_obj.new(po_line_vals)
            tmp_line.onchange_product_id()
            purchase_line_vals = [(0, 0, tmp_line._convert_to_write(tmp_line._cache))]
            po_data = purchase_order_data.get('line.vendor_id.id')
            if po_data:
                po_line_data = po_data.get('order_line', [])
                po_line_data += purchase_order_data
                po_data.update({"order_line": purchase_line_vals})
            else:
                po_data = {
                    'partner_id': line.vendor_id.id,
                    'date_order': datetime.now(),
                    'company_id': self.env.user.company_id.id,
                    'order_line': purchase_line_vals
                }
                purchase_order_data.update({line.vendor_id.id: po_data})
        return purchase_order_data

    def show_purchase_orders(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        if len(self.purchase_order_ids.ids) > 1:
            action['domain'] = [('id', 'in', self.purchase_order_ids.ids)]
        elif len(self.purchase_order_ids.ids) == 1:
            form_view = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = self.purchase_order_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def show_pickings(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        picking_ids = self.env["stock.picking"]
        for purchase_requisition in self:
            for purchase_order in purchase_requisition.purchase_order_ids:
                picking_ids += purchase_order.picking_ids
        if len(picking_ids.ids) > 1:
            action['domain'] = [('id', 'in', picking_ids.ids)]
        elif len(picking_ids.ids) == 1:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = picking_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisitions.line"
    _description = "Purchase Requisition Line"
    _rec_name = "product_id"

    product_id = fields.Many2one("product.product", string="Product", required=True)
    purchase_requisition_id = fields.Many2one("purchase.requisitions", string="Purchase Requisition")
    description = fields.Text("Description")
    quantity = fields.Float("Quantity", required=True)
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True)
    vendor_id = fields.Many2one("res.partner", string="Vendors")
