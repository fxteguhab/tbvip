# coding=utf-8
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _


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
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_purchase_id': fields.integer('MySQL Purchase ID'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True,
									 states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)],
											 'done': [('readonly', True)]}),
		'cashier': fields.char('Cashier'),
		# TIMTBVIP: tidak perlu ada di sini lagi, sudah ada module purchase_sales_discount
		# Tadinya ada 'general_discount': fields.float('Discount'), 
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
			# invoice_obj.signal_workflow(cr, uid, [invoice.id], 'invoice_open', context)
		return new_id
	
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
	
# JUNED: setelah saya pikirin lebih baik kalau _prepare_inv_line dan _prepare_invoice dipindah ke puchase_sales_discount
# gimana menurut kalian? pertimbangan saya kedua method ini masih terkait diskon, jadi dipindah supaya module 
# purchase_sales_discount lebih independen dan tetap akurat.
	def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
		"""
		Overrides _prepare_inv_line to include discount in invoice lines
		"""
		result = super(purchase_order, self)._prepare_inv_line(cr, uid, account_id, order_line, context)
		result[
			'discount_amount'] = order_line.discount1 + order_line.discount2 + order_line.discount3 + order_line.discount4 + \
								 order_line.discount5 + order_line.discount6 + order_line.discount7 + order_line.discount8
		return result
	
	def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
		"""
		Overrides _prepare_invoice to include discount in invoice
		"""
		result = super(purchase_order, self)._prepare_invoice(cr, uid, order, line_ids, context)
		result['discount_amount'] = order.purchase_discount_amount
		return result


# ==========================================================================================================================


class purchase_order_line(osv.osv):
	_inherit = 'purchase.order.line'
	
	WATCHED_FIELDS_FROM_PO = ['product_id', 'product_qty', 'price_unit', 'discount_string']
	
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
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context=None):
		new_order_line = super(purchase_order_line, self).create(cr, uid, vals, context)
		if vals.get('product_id', False) and vals.get('price_unit', False):
			product_obj = self.pool.get('product.product')
			product = product_obj.browse(cr, uid, vals['product_id'])
			self._message_cost_price_changed(cr, uid, vals, product, vals['order_id'], context)
			self._message_line_changes(cr, uid, vals, new_order_line, create=True, context=None)
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
	
	# TIMTBVIP: versi yang lebih baik, tolong yang di atas diganti setelah memahami berikut ini:
	"""
		product_obj = self.pool.get('product.product')
		if vals.get('price_unit', False):
			for purchase_line in self.browse(cr, uid, ids):
				self._message_cost_price_changed(cr, uid, vals, purchase_line.product_id, purchase_line.order_id.id, context)
		ngga banyak browse, ngga bolak balik query database
		ingat browse itu mengambil semua vals m2o dan o2m, menggurita sampai ke model paling atas/paling bawah
	"""
	# Tadinya...
	# """
	# def write(self, cr, uid, ids, vals, context=None):
	# 	edited_order_line = super(purchase_order_line, self).write(cr, uid, ids, vals, context)
	# 	for id in ids:
	# 		if vals.get('price_unit', False):
	# 			product_obj = self.pool.get('product.product')
	# 			product = product_obj.browse(cr, uid, self.browse(cr, uid, id).product_id.id)
	# 			self._message_cost_price_changed(cr, uid, vals, product, self.browse(cr, uid, id).order_id.id, context)
	# 	return edited_order_line
	# """
