# coding=utf-8
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import discount_utility

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
				invoice.signal_workflow('from_po')
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
	
	def _amount_line_discount(self, cr, uid, ids, prop, arg, context=None):
		res = super(purchase_order_line, self)._amount_line(cr, uid, ids, prop, arg, context)
		cur_obj=self.pool.get('res.currency')
		tax_obj = self.pool.get('account.tax')
		for line in self.browse(cr, uid, ids, context=context):
			line_price = line.price_unit if line.discount_algorithm else self._calc_line_base_price(cr, uid, line,
				context=context)
			line_qty = self._count_qty_with_uom(cr, uid, line.product_id.id, line.product_uom.id, line.product_qty)
			taxes = tax_obj.compute_all(cr, uid, line.taxes_id, line_price,
				line_qty, line.product_id,
				line.order_id.partner_id)
			cur = line.order_id.pricelist_id.currency_id
			# taxes['total'] = (line.line_qty * line.price_unit) - total_discount if line.discount_algorithm else
			discounts = discount_utility.calculate_discount(line.discount_string, line_price, self._max_discount)
			total_discount = discounts[0] + discounts[1] + discounts[2] + discounts[3] + discounts[4] + discounts[5] + \
							discounts[6] + discounts[7]
			if line.discount_algorithm:
				taxes['total'] = taxes['total'] - total_discount
			res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
		return res
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'source': fields.selection(SOURCE, 'Source'),
		'discount_algorithm': fields.boolean('Discount from Subtotal'),
		'price_subtotal': fields.function(_amount_line_discount, string='Subtotal', digits_compute= dp.get_precision('Account')),
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
	
	def _count_qty_with_uom(self, cr, uid, product_id, product_uom, product_qty):
		product_uom_obj = self.pool.get('product.uom')
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		product_qty = product_uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.product_tmpl_id.uom_po_id.id)
		return product_qty
	
	def write(self, cr, uid, ids, vals, context=None):
		for id in ids:
			self._message_line_changes(cr, uid, vals, id, context=None)
		edited_order_line = super(purchase_order_line, self).write(cr, uid, ids, vals, context)
		if vals.get('price_unit', False):
			for purchase_line in self.browse(cr, uid, ids):
				self._message_cost_price_changed(cr, uid, vals, purchase_line.product_id, purchase_line.order_id.id, context)
		return edited_order_line
	
	def onchange_order_line(self, cr, uid, ids, product_qty, price_unit, discount_string, product_uom, product_id,context={}):
		try:
			valid_discount_string = discount_utility.validate_discount_string(
				discount_string, price_unit, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		discounts = discount_utility.calculate_discount(valid_discount_string, price_unit, self._max_discount)
		total_discount = discounts[0] + discounts[1] + discounts[2] + discounts[3] + discounts[4] + discounts[5] + \
						 discounts[6] + discounts[7]
		qty = self._count_qty_with_uom(cr, uid, product_id, product_uom, product_qty)
		return {
			'value': {
				'price_unit_nett': price_unit - total_discount,
				'price_subtotal': qty * (price_unit - total_discount)
			}
		}
	
	def onchange_order_line_count_discount(self, cr, uid, ids, product_qty, price_unit, discount_string, product_uom,
			product_id, discount_from_subtotal, context={}):
		result = self.onchange_order_line(cr, uid, ids, product_qty, price_unit,
			discount_string, product_uom, product_id, context=context)
	# Recount qty
		product_qty = self._count_qty_with_uom(cr, uid, product_id, product_uom, product_qty)
	# Recount discount
		discounts = discount_utility.calculate_discount(discount_string, price_unit, self._max_discount)
		total_discount = discounts[0] + discounts[1] + discounts[2] + discounts[3] + discounts[4] + discounts[5] + \
						 discounts[6] + discounts[7]
	# Tentuin cara perhitungan diskon mau dikurangi dari price_unit_nett atau dari subtotal
		price_unit_nett = result['value']['price_unit_nett']
		price_subtotal = result['value']['price_subtotal']
		order_lines = self.browse(cr, uid, ids)
		for order_line in order_lines:
			discount_from_subtotal = order_line.discount_algorithm
		# Count subtotal
		if discount_from_subtotal:
			price_unit_nett = price_unit
			price_subtotal = (product_qty * price_unit) - total_discount
		else:
			price_unit_nett = price_unit - total_discount
			price_subtotal = product_qty * (price_unit - total_discount)
		result['value'].update({
			'price_unit_nett': price_unit_nett,
			'price_subtotal': price_subtotal
		})
		return result
	
	def onchange_product_uom_purchases_sale_discount(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
			partner_id, discount_string,date_order=False, fiscal_position_id=False, date_planned=False,
			name=False, price_unit=False, state='draft', discount_algorithm=False, context=None):
		result = super(purchase_order_line, self).onchange_product_uom(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
			partner_id, date_order, fiscal_position_id, date_planned,
			name, price_unit, state, context)
		result['value'].update(self.onchange_order_line_count_discount(cr, uid, ids, qty, price_unit, discount_string, uom_id, product_id, discount_algorithm))
		result = self.onchange_order_line_count_discount(cr, uid, ids, qty, price_unit, discount_string, uom_id, product_id, discount_algorithm)
		return result