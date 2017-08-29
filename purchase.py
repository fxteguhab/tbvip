# coding=utf-8
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime

import openerp.addons.purchase_sale_discount as psd
import openerp.addons.sale as imported_sale
import openerp.addons.portal_sale as imported_portal_sale
import openerp.addons.sale_stock as imported_sale_stock
import openerp.addons.purchase_sale_discount as imported_purchase_sale_discount
import openerp.addons.sale_direct_cash as imported_sale_direct_cash
import openerp.addons.product_custom_conversion as imported_product_custom_conversion
import openerp.addons.chjs_price_list as imported_price_list
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
		# 'partner_id': _default_partner_id,
		'branch_id': _default_branch_id,
		'shipped_or_taken': 'shipped',
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

	def onchange_picking_type_id(self, cr, uid, ids, picking_type_id, context=None):
		result = super(purchase_order, self).onchange_picking_type_id(cr, uid, ids, picking_type_id, context)
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		location_id =  user_data.branch_id.default_incoming_location_id.id or None
		result.update({
			'location_id': location_id,
		})
		return {'value': result}
	
	def picking_done(self, cr, uid, ids, context=None):
		"""
		Overrides picking_done to also mark the picking as transfered
		"""
		picking_ids = []
		for po in self.browse(cr, uid, ids, context=context):
			if po.shipped_or_taken == 'shipped':
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
		'product_qty': fields.float('Quantity', digits_compute= dp.get_precision('Decimal Custom Order Line'), required=True),
		'uom_category_filter_id': fields.related('product_id', 'product_tmpl_id', 'uom_id', 'category_id', relation='product.uom.categ', type='many2one',
			string='UoM Category', readonly=True)
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
			if vals.get('price_type_id', False) and vals.get('product_uom', False):
				self._create_product_current_price_if_none(cr, uid,
					vals['price_type_id'], vals['product_id'], vals['product_uom'], vals['price_unit'])
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
		for po_line in self.browse(cr, uid, ids):
			product_id = po_line.product_id.id
			price_type_id = po_line.price_type_id.id
			product_uom = po_line.product_uom.id
			price_unit = po_line.price_unit
			if vals.get('product_id', False): product_id = vals['product_id']
			if vals.get('price_type_id', False): price_type_id = vals['price_type_id']
			if vals.get('product_uom', False): product_uom = vals['product_uom']
			if vals.get('price_unit', False): price_unit = vals['price_unit']
			self._create_product_current_price_if_none(cr, uid, price_type_id, product_id, product_uom, price_unit)
		return edited_order_line
	
	def unlink(self, cr, uid, ids, context=None):
		result = super(purchase_order_line, self).unlink(cr, uid, ids, context)
		demand_line_obj = self.pool.get('tbvip.demand.line')
		demand_line_ids = demand_line_obj.search(cr, uid, [('purchase_order_line_id','in',ids)])
		demand_line_obj.write(cr, uid, demand_line_ids, {
			'state': 'requested'
		})
		return result
	
	# def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
	# 		partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
	# 		name=False, price_unit=False, state='draft', parent_price_type_id=False, price_type_id=False, context=None):
	# 	product_conversion_obj = self.pool.get('product.conversion')
	# 	uom_id = product_conversion_obj.get_uom_from_auto_uom(cr, uid, uom_id, context).id
	# 	result = cpl.purchase.purchase_order_line.onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
	# 		partner_id, date_order, fiscal_position_id, date_planned,
	# 		name, price_unit, state, parent_price_type_id, price_type_id, context)
	# 	temp = super(purchase_order_line, self).onchange_product_uom(
	# 		cr, uid, ids, pricelist_id, product_id, qty, uom_id, partner_id, date_order, fiscal_position_id,
	# 		date_planned, name, price_unit, state, context={})
	# 	if result.get('domain', False) and temp.get('domain', False):
	# 		result['domain']['product_uom'] = result['domain']['product_uom'] + temp['domain']['product_uom']
	# 	product_obj = self.pool.get('product.product')
	# 	product = product_obj.browse(cr, uid, product_id)
	# 	result['value'].update({
	# 		'product_uom': uom_id if uom_id else product.uom_id.id,
	# 		'uom_category_filter_id': product.product_tmpl_id.uom_id.category_id.id
	# 	})
	# 	return result
	
	def _create_product_current_price_if_none(self, cr, uid, price_type_id, product_id, uom_id, price):
		product_current_price_obj = self.pool.get('product.current.price')
		product_current_price_ids = product_current_price_obj.search(cr, uid, [
			('price_type_id', '=', price_type_id),
			('product_id', '=', product_id)
		])
		if len(product_current_price_ids) == 0:
			product_current_price_obj.create(cr, uid, {
				'price_type_id': price_type_id,
				'product_id': product_id,
				'uom_id_1': uom_id,
				'price_1': price,
			})
		else:
			add = True
			field_uom = False
			field_price = False
			product_current_price = product_current_price_obj.browse(cr, uid, product_current_price_ids)[0]
			if product_current_price['uom_id_1'].id == uom_id or product_current_price['uom_id_2'].id == uom_id or \
				product_current_price['uom_id_3'].id == uom_id or product_current_price['uom_id_4'].id == uom_id or \
				product_current_price['uom_id_5'].id == uom_id:
				add = False
			if add:
				if not product_current_price['uom_id_1']:
					field_uom = 'uom_id_1'
					field_price = 'price_1'
				elif not product_current_price['uom_id_2']:
					field_uom = 'uom_id_2'
					field_price = 'price_2'
				elif not product_current_price['uom_id_3']:
					field_uom = 'uom_id_3'
					field_price = 'price_3'
				elif not product_current_price['uom_id_4']:
					field_uom = 'uom_id_4'
					field_price = 'price_4'
				elif not product_current_price['uom_id_5']:
					field_uom = 'uom_id_5'
					field_price = 'price_5'
				if field_uom and field_price:
					product_current_price_obj.write(cr, uid, [product_current_price.id], {
						'price_type_id': price_type_id,
						'product_id': product_id,
						field_uom: uom_id,
						field_price: price,
					})
				else:
					pass  # penuh field uomnya
	
	def onchange_product_id_tbvip(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
			partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
			name=False, price_unit=False, state='draft', parent_price_type_id=False, price_type_id=False,
			discount_from_subtotal=False, context=None):
		result = self.onchange_product_tbvip(cr, uid, ids, pricelist_id, product_id, qty, uom_id, partner_id, date_order,
			fiscal_position_id, date_planned, name, price_unit, state, parent_price_type_id, price_type_id,
			discount_from_subtotal, context)
		if product_id:
			product_obj = self.pool.get('product.product')
			product = product_obj.browse(cr, uid, product_id)
			result['value']['product_uom'] = product.uom_id.id
		return result
	
	def onchange_product_tbvip(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
			partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
			name=False, price_unit=False, state='draft', parent_price_type_id=False, price_type_id=False,
			discount_from_subtotal=False, context=None):
		product_conversion_obj = self.pool.get('product.conversion')
		uom_id = product_conversion_obj.get_uom_from_auto_uom(cr, uid, uom_id, context).id
		
		result_price_list = imported_price_list.purchase.purchase_order_line.onchange_product_id(
			self, cr, uid, ids, pricelist_id, product_id, qty, uom_id, partner_id, date_order, fiscal_position_id,
			date_planned, name, price_unit, state, parent_price_type_id, price_type_id, context)
		price_unit_current = result_price_list['value']['price_unit'] \
			if result_price_list['value'].get('price_unit', False) else price_unit
		result = result_price_list
		
		result_purchase_sale_discount = \
			imported_purchase_sale_discount.purchase_discount.purchase_order_line.onchange_product_id_purchase_sale_discount(
			self, cr, uid, product_id, partner_id, uom_id, qty, discount_from_subtotal)
		if result_purchase_sale_discount:
			result['value'].update({
				'price_unit': result_purchase_sale_discount['value']['price_unit'] if price_unit_current == False else price_unit_current,
				'discount_string': result_purchase_sale_discount['value']['discount_string'],
				'price_unit_nett': result_purchase_sale_discount['value']['price_unit_nett'],
				'price_subtotal': result_purchase_sale_discount['value']['price_subtotal'],
			})
		
		result_custom_conversion = imported_product_custom_conversion.purchase.purchase_order_line.onchange_product_uom(
			self, cr, uid, ids, pricelist_id, product_id, qty, uom_id, partner_id, date_order, fiscal_position_id,
			date_planned, name, price_unit_current, state, context={})
		if result.get('domain', False) and result_custom_conversion.get('domain', False):
			result['domain']['product_uom'] = result['domain']['product_uom'] + result_custom_conversion['domain']['product_uom']
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		result['value'].update({
			'product_uom': result_custom_conversion['value']['product_uom']
				if result_custom_conversion['value'].get('product_uom', False) else uom_id if uom_id else product.uom_id.id,
			'uom_category_filter_id': product.product_tmpl_id.uom_id.category_id.id
		})
		
		return result
