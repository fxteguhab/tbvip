# coding=utf-8
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime

import openerp.addons.purchase_sale_discount as psd
import openerp.addons.chjs_price_list as cpl
import openerp.addons.decimal_precision as dp

# ==========================================================================================================================

class purchase_order(osv.osv):
	_inherit = 'purchase.order'
	
	# FIELD FUNCTION METHODS ------------------------------------------------------------------------------------------------
	
	def _alert(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for data in self.browse(cr, uid, ids):
			max_alert = -1
			for line in data.order_line:
				max_alert = max(max_alert, line.alert)
			result[data.id] = max_alert
		return result
	
	def _default_partner_id(self, cr, uid, context={}):
		model, general_supplier_id = self.pool['ir.model.data'].get_object_reference(
			cr, uid, 'tbvip', 'tbvip_supplier_general')
		return general_supplier_id
	
	def _default_branch_id(self, cr, uid, context={}):
		# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.id or None
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_purchase_id': fields.integer('MySQL Purchase ID'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True,
			states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)],
				'done': [('readonly', True)]}),
		'cashier': fields.char('Cashier'),
		'alert': fields.function(_alert, method=True, type='integer', string="Alert", store=True),
		'adm_point': fields.float('Adm. Point'),
		'pickup_vehicle_id': fields.many2one('fleet.vehicle', 'Pickup Vehicle'),
		'driver_id': fields.many2one('hr.employee', 'Pickup Driver'),
		'partner_ref': fields.char('Supplier Reference', states={'confirmed': [('readonly', True)],
			'approved': [('readonly', True)],
			'done': [('readonly', True)]},
			copy=False, track_visibility='always',
			help="Reference of the sales order or bid sent by your supplier. "
				 "It's mainly used to do the matching when you receive the "
				 "products as this reference is usually written on the "
				 "delivery order sent by your supplier.", ),
		'date_order': fields.datetime('Order Date', required=True, states={'confirmed': [('readonly', True)],
			'approved': [('readonly', True)]},
			select=True, copy=False, track_visibility='always',
			help="Depicts the date where the Quotation should be validated and "
				 "converted into a Purchase Order, by default it's the creation date.", ),
		'shipped_or_taken': fields.selection([
			('shipped', 'Shipped'),
			('taken', 'Taken')
		], 'Shipped or Taken'),
	}
	
	_defaults = {
		'partner_id': _default_partner_id,
		'branch_id': _default_branch_id,
		'shipped_or_taken': 'taken',
	}
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		new_id = super(purchase_order, self).create(cr, uid, vals, context=context)
		# langsung confirm purchasenya bila diinginkan. otomatis dia bikin satu invoice dan satu incoming goods
		if context.get('direct_confirm', False):
			purchase_data = self.browse(cr, uid, new_id)
			self.signal_workflow(cr, uid, [new_id], 'purchase_confirm', context)
			# samakan tanggal invoice dengan tanggal PO, jadi tidak default tanggal hari ini
			invoice_obj = self.pool.get('account.invoice')
			for invoice in purchase_data.invoice_ids:
				invoice_obj.write(cr, uid, [invoice.id], {
					'date_invoice': purchase_data.date_order,
				})
		return new_id
	
	def write(self, cr, uid, ids, vals, context=None):
		result = super(purchase_order, self).write(cr, uid, ids, vals, context)
		if vals.get('state', False) and vals['state'] == 'confirmed':
			demand_line_obj = self.pool.get('tbvip.demand.line')
			for po in self.browse(cr, uid, ids):
				demand_line_ids = demand_line_obj.search(cr, uid, [('purchase_order_line_id','in',po.order_line.ids)])
				demand_line_obj.ready_demand_lines(cr, uid, demand_line_ids, context)
		return result
				
	
	def picking_done(self, cr, uid, ids, context=None):
		"""
		Overrides picking_done to also mark the picking as transfered
		"""
		picking_ids = []
		for po in self.browse(cr, uid, ids, context=context):
			picking_ids += [picking.id for picking in po.picking_ids]
		picking_obj = self.pool.get('stock.picking')
		picking_obj.do_transfer(cr, uid, picking_ids)
		return super(purchase_order, self).picking_done(cr, uid, ids, context)
	
	def action_invoice_create(self, cr, uid, ids, context=None):
		"""Overrides so that on creating invoice from confirming a PO, the invoice is set as open
		:param ids: list of ids of purchase orders.
		:return: ID of created invoice.
		:rtype: int
		"""
		result = super(purchase_order, self).action_invoice_create(cr, uid, ids, context)
		invoice_obj = self.pool.get('account.invoice')
		for invoice in invoice_obj.browse(cr, uid, [result]):
			invoice.signal_workflow('invoice_open')
		return result

# ==========================================================================================================================

class purchase_order_line(osv.osv):
	_inherit = 'purchase.order.line'
	
	WATCHED_FIELDS_FROM_PO = ['product_id', 'product_qty', 'price_unit', 'discount_string']
	SOURCE = [('needs', 'Needs'), ('manual', 'Manual'), ('owner', 'Owner')]
	
	# METHODS ---------------------------------------------------------------------------------------------------------------
	
	def _message_cost_price_changed(self, cr, uid, data, product, order_id, context):
		if product.standard_price > 0 and data['price_unit'] != product.standard_price:
			purchase_order_obj = self.pool.get('purchase.order')
			purchase_order = purchase_order_obj.browse(cr, uid, order_id)
			# message post to SUPERUSER and all users in group Purchases Manager
			group_obj = self.pool.get('res.groups')
			purchase_manager_group_ids = group_obj.search(cr, uid,
				[('category_id.name', '=', 'Purchases'),
					('name', '=', 'Manager')])
			partner_ids = [SUPERUSER_ID]
			for user in group_obj.browse(cr, uid, purchase_manager_group_ids).users:
				partner_ids += [user.partner_id.id]
			partner_ids = list(set(partner_ids))
			purchase_order_obj.message_post(cr, uid, purchase_order.id, context=context, partner_ids=partner_ids,
				body=_(
					"There is a change on cost price for %s in Purchase Order %s. Original: %s, in PO: %s.")
					 % (product.name, purchase_order.name, product.standard_price,
				data['price_unit']))
	
	def _purchase_hour(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		lines = self.browse(cr, uid, ids)
		for line in lines:
			purchase_date = datetime.strptime(line.date_order, '%Y-%m-%d %H:%M:%S')
			result[line.id] = purchase_date.hour * 3600 + purchase_date.minute * 60
		return result
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'source': fields.selection(SOURCE, 'Source'),
		# 'price_subtotal': fields.function(_amount_line_discount, string='Subtotal', digits_compute= dp.get_precision('Account')),
		'mysql_purchase_det_id': fields.integer('MySQL Purchase Detail ID'),
		'purchase_hour': fields.function(_purchase_hour, method=True, string='Purchase Hour', type='float'),
		'alert': fields.integer('Alert'),
	}
	
	# DEFAULTS --------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'source': 'manual',
	}
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context=None):
		new_order_line = super(purchase_order_line, self).create(cr, uid, vals, context)
		if vals.get('product_id', False) and vals.get('price_unit', False):
			product_obj = self.pool.get('product.product')
			product = product_obj.browse(cr, uid, vals['product_id'])
			self._message_cost_price_changed(cr, uid, vals, product, vals['order_id'], context)
			self._message_line_changes(cr, uid, vals, new_order_line, create=True, context=None)
		if not vals.get('location_id', False):
			users_obj = self.pool.get('res.users')
			incoming_location = users_obj.browse(cr, uid, [uid], context).branch_id.default_incoming_location_id
			if incoming_location != False:
				vals['location_id'] = incoming_location
		return new_order_line
	
	def _message_line_changes(self, cr, uid, vals, line_id, create=False, context=None):
		purchase_order_obj = self.pool.get('purchase.order')
		product_obj = self.pool.get('product.product')
		line = self.browse(cr, uid, line_id)
		message = _("Order line changed:") if not create else _("Order line created:")
		for key, val in vals.iteritems():
			if key in self.WATCHED_FIELDS_FROM_PO:
				value_from = ''
				value_to = val
				if key == 'product_id':
					value_from = line.product_id.name
					value_to = product_obj.browse(cr, uid, val).name
				elif key == 'product_qty':
					value_from = line.product_qty
					value_to = val
				elif key == 'price_unit':
					value_from = line.price_unit
					value_to = val
				elif key == 'discount_string':
					value_from = line.discount_string
					value_to = val
				message += "\n<li><b>%s</b>: %s %s %s</li>" % (self._columns[key].string, value_from, u'\u2192', value_to) \
					if not create else \
					"\n<li><b>%s</b>: %s</li>" % (self._columns[key].string, value_to)
		purchase_order_obj.message_post(cr, uid, line.order_id.id, body=message)
		pass
	
	def write(self, cr, uid, ids, vals, context=None):
		for id in ids:
			self._message_line_changes(cr, uid, vals, id, context=None)
		edited_order_line = super(purchase_order_line, self).write(cr, uid, ids, vals, context)
		if vals.get('price_unit', False):
			for purchase_line in self.browse(cr, uid, ids):
				self._message_cost_price_changed(cr, uid, vals, purchase_line.product_id, purchase_line.order_id.id, context)
		return edited_order_line
	
	def unlink(self, cr, uid, ids, context=None):
		result = super(purchase_order_line, self).unlink(cr, uid, ids, context)
		demand_line_obj = self.pool.get('tbvip.demand.line')
		demand_line_ids = demand_line_obj.search(cr, uid, [('purchase_order_line_id','in',ids)])
		demand_line_obj.write(cr, uid, demand_line_ids, {
			'state': 'requested'
		})
		return result
	
	def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
			partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
			name=False, price_unit=False, state='draft', discount_from_subtotal=False, parent_price_type_id=False, context=None):

		result_price_type = cpl.purchase.purchase_order_line.onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
			partner_id, date_order, fiscal_position_id, date_planned, name, price_unit, state, parent_price_type_id=parent_price_type_id, context=context)

		result_discount = psd.purchase_discount.purchase_order_line.onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
			partner_id, date_order, fiscal_position_id, date_planned, name, price_unit, state, discount_from_subtotal=discount_from_subtotal, context=context)

		result = result_discount
		if result_price_type:
			if result_price_type['value'].get('price_type_id', False):
				if result:
					result['value']['price_type_id'] = result_price_type['value']['price_type_id']
				else:
					result = { 'value': { 'price_type_id': result_price_type['value']['price_type_id'] } }
		return result