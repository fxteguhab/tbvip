from openerp.osv import osv, fields
import commission_utility
from openerp.tools.translate import _
from datetime import datetime, date, timedelta
import openerp.addons.decimal_precision as dp


import openerp.addons.sale as imported_sale
import openerp.addons.portal_sale as imported_portal_sale
import openerp.addons.sale_stock as imported_sale_stock
import openerp.addons.purchase_sale_discount as imported_purchase_sale_discount
import openerp.addons.sale_multiple_payment as imported_sale_multiple_payment
import openerp.addons.product_custom_conversion as imported_product_custom_conversion
import openerp.addons.chjs_price_list as imported_price_list






# ==========================================================================================================================

class sale_order(osv.osv):
	_inherit = 'sale.order'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission_total': fields.float('Commission Total', readonly=True),
		'bon_number': fields.char('Bon Number', required=True),
		'bon_book_id': fields.many2one('tbvip.bon.book', 'Bon Number', required=True),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True),
		'stock_location_id': fields.many2one('stock.location', 'Location'),
		'is_complex_payment': fields.boolean('Is Complex Payment'),
		'return_amount' : fields.float('Return Amount'),
		'return_id': fields.many2one('account.invoice', "Return", readonly=True),
	}

	def _default_partner_id(self, cr, uid, context={}):
	# kalau penjualan cash, default customer adalah general customer
		partner_id = None
		if context.get('default_is_payment_cash', False):
			model, general_customer_id = self.pool['ir.model.data'].get_object_reference(
				cr, uid, 'tbvip', 'tbvip_customer_general')
			partner_id = general_customer_id or None
		return partner_id

	def _default_branch_id(self, cr, uid, context={}):
	# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.id or None

	_defaults = {
		'partner_id': _default_partner_id,
		'branch_id': _default_branch_id,
		'shipped_or_taken': 'taken',
		'stock_location_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_outgoing_location_id.id,
		'is_complex_payment': False
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		if vals.get('bon_number', False) and vals.get('date_order', False):
			bon_number = vals['bon_number']
			date_order = vals['date_order']
			bon_book = self.check_and_get_bon_number(cr, uid, bon_number, date_order)
			if bon_book:
				vals.update({
					'bon_book_id': bon_book.id,
					'employee_id': bon_book.employee_id.id
				})
		new_id = super(sale_order, self).create(cr, uid, vals, context)
		self._calculate_commission_total(cr, uid, new_id)
		return new_id
	
	def write(self, cr, uid, ids, vals, context=None):
		for sale_order_data in self.browse(cr, uid, ids):
			if vals.get('name', False):
				pass
			else:
				bon_number = vals['bon_number'] if vals.get('bon_number', False) else sale_order_data.bon_number
				bon_name = ' / ' + bon_number if bon_number else ' / ' + datetime.strptime(sale_order_data.date_order, '%Y-%m-%d %H:%M:%S').strftime('%H:%M:%S')
				name = '%s%s' % (datetime.strptime(sale_order_data.date_order, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d'), bon_name)
				if 'Koreksi' not in sale_order_data.name:
					vals['name'] = name
			
			# Kalau SO di cancel, hapus used number tersebut dari bon book nya
			if vals.get('state', False) == 'cancel':
				bon_book_obj = self.pool.get('tbvip.bon.book')
				bon_book = bon_book_obj.browse(cr, uid, [sale_order_data.bon_book_id.id])
				if bon_book.used_numbers:
					used_numbers = bon_book.used_numbers.split(', ')
					new_used_numbers = ''
					for used_number in used_numbers:
						if used_number != bon_number:
							new_used_numbers += used_number + ', '
					bon_book_obj.write(cr, uid, bon_book.id, {
						'used_numbers': new_used_numbers
					})
			
			if vals.get('bon_number', False) or vals.get('date_order', False):
				bon_number = sale_order_data.bon_number
				date_order = sale_order_data.date_order
				if vals.get('bon_number', False):
					bon_number = vals['bon_number']
				if vals.get('date_order', False):
					date_order = vals['date_order']
				bon_book = self.check_and_get_bon_number(cr, uid, bon_number, date_order)
				if bon_book:
					vals.update({
						'bon_book_id': bon_book.id,
						'employee_id': bon_book.employee_id.id
					})
			result = super(sale_order, self).write(cr, uid, sale_order_data.id, vals, context)
			
		if vals.get('order_line', False):
			for sale_id in ids:
				self._calculate_commission_total(cr, uid, sale_id)
		
		return result
	
	def create_or_update_sale_history_from_sale_done(self, cr, uid, sale_ids, context={}):
		sale_history_obj = self.pool.get('sale.history')
		month_now = datetime.now().month
		year_now = datetime.now().year
		dict_product_sale = {}
		for sale in self.browse(cr, uid, sale_ids):
			month_sale = datetime.strptime(sale.date_order, '%Y-%m-%d %H:%M:%S').month
			year_sale = datetime.strptime(sale.date_order, '%Y-%m-%d %H:%M:%S').year
			if month_sale!=month_now or year_now != year_sale:
				dict_product_sale = sale_history_obj.create_dict_for_sale_history(cr, uid, sale_ids, context)
			for product_id, dict_branch_id in dict_product_sale.iteritems():
				for branch_id, value in dict_branch_id.iteritems():
					# cari dahulu apakah sudah terdapat sale_history yang lama, jika ada maka write, jika tidak maka create
					history_id =  sale_history_obj.search(cr, uid, [('month', '=', month_sale),
						('year', '=', year_sale),
						('product_id', '=', product_id),
						('branch_id', '=', branch_id)], limit = 1)
					if history_id:
						sale_history = sale_history_obj.browse(cr, uid, history_id)
						sale_history_obj.write(cr, uid, history_id,  {'number_of_sales': sale_history.number_of_sales + value['qty']})
					else:
						sale_history_obj.create(cr, uid, {
							'product_id': product_id,
							'number_of_sales': value['qty'],
							'year' : year_sale,
							'month': month_sale,
							'branch_id': branch_id})
	
	def _make_payment(self, cr, uid, partner_id, amount, payment_method, invoice_id, context=None):
		"""
		Register payment. Return
		"""
		if payment_method not in ['transfer', 'cash', 'receivable', 'giro']:
			return False
		
		voucher_obj = self.pool.get('account.voucher')
		journal_obj = self.pool.get('account.journal')
		account_move_line_obj = self.pool.get('account.move.line')
		invoice_obj = self.pool.get('account.invoice')
		
		account_move_id = account_move_line_obj.search(cr, uid, [('invoice', '=', invoice_id)])[0]
		account_move = account_move_line_obj.browse(cr, uid, [account_move_id])
		
		# Prepare voucher values for payment
		voucher_vals = {
			'partner_id': partner_id.id,
			# 'company_id': 1,
			# 'period_id': 11,
			# 'payment_rate_currency_id': 38,
			# 'date': '2017-10-16',
			# 'payment_rate': 1,
			# 'reference': False,
			# 'writeoff_acc_id': False,
			# 'analytic_id': False,
			# 'is_multi_currency': False,
			# 'narration': False,
			# 'name': False
			'payment_method_type': payment_method,
			'comment': 'Write-Off',
			'payment_option': 'without_writeoff',
			# 'journal_id': 8,
			# 'account_id': 172,
			'pre_line': True,
			'amount': amount,
			'type': 'receipt',
			'line_cr_ids': [(0, False, {
				'date_due': fields.date.today(),
				'reconcile': True if amount >= account_move.debit - account_move.credit else False,
				'date_original': fields.date.today(),
				'move_line_id': account_move.id,
				'amount_unreconciled': account_move.debit - account_move.credit,
				'amount': amount,
				'amount_original': account_move.debit,
				'account_id': account_move.account_id.id
			})],
		}
		
		if payment_method == 'transfer':
			journal_id = journal_obj.search(cr, uid, [('type', 'in', ['bank'])], limit=1)
			pass
		elif payment_method == 'cash':
			journal_id = journal_obj.search(cr, uid, [('type', 'in', ['cash'])], limit=1)
			pass
		elif payment_method == 'receivable':
			journal_id = journal_obj.search(cr, uid, [('type', 'in', ['bank'])], limit=1)
			pass
		elif payment_method == 'giro':
			journal_id = journal_obj.search(cr, uid, [('type', 'in', ['bank'])], limit=1)
			pass
		
		journal = journal_obj.browse(cr, uid, journal_id, context)
		voucher_vals.update({
			'account_id': journal.default_debit_account_id.id or journal.default_credit_account_id.id}
		)
		
		# Create payment
		voucher_id = voucher_obj.create(cr, uid, voucher_vals, context)
		voucher_obj.signal_workflow(cr, uid, [voucher_id], 'proforma_voucher', context)
		
		# if residual==0, paid
		for invoice in invoice_obj.browse(cr, uid, invoice_id):
			if invoice.residual == 0:
				invoice_obj.write(cr, uid, [invoice_id], {'reconciled': True}, context)
				pass

	def action_button_confirm(self, cr, uid, ids, context=None):
		invoice_obj = self.pool.get('account.invoice')
		picking_obj = self.pool.get('stock.picking')
		result = super(sale_order, self).action_button_confirm(cr, uid, ids, context)
		for sale in self.browse(cr, uid, ids):
			if sale.bon_number and sale.date_order:
				self._update_bon_book(cr, uid, sale.bon_number, sale.date_order)
			# make invoice and make its state to open
			self.signal_workflow(cr, uid, [sale.id], 'manual_invoice', context)
			# append bon number to invoice
			invoice_obj.write(cr, uid, sale.invoice_ids.ids, {'related_sales_bon_number': sale.bon_number})
			# append bon number to picking
			delivery = self.action_view_delivery(cr, uid, sale.id, context=context)
			stock_picking_id = delivery['res_id']
			if stock_picking_id:
				picking_obj.write(cr, uid,stock_picking_id, {'related_sales_bon_number': sale.bon_number})
			# Make invoice open
			invoice_obj.signal_workflow(cr, uid, sale.invoice_ids.ids, 'invoice_open', context)
			
			order = sale
			if order.payment_transfer_amount > 0:
				self._make_payment(cr, uid, order.partner_id, order.payment_transfer_amount, order.invoice_ids[0].id, 'transfer', context=None)
			if order.payment_cash_amount > 0:
				self._make_payment(cr, uid, order.partner_id, order.payment_cash_amount, 'cash', order.invoice_ids[0].id, context=None)
			if order.payment_receivable_amount > 0:
				self._make_payment(cr, uid, order.partner_id, order.payment_receivable_amount, order.invoice_ids[0].id, 'receivable', context=None)
			if order.payment_giro_amount > 0:
				self._make_payment(cr, uid, order.partner_id, order.payment_giro_amount, order.invoice_ids[0].id, 'giro', context=None)
			
		return result
	
	def _calculate_commission_total(self, cr, uid, sale_order_id):
		order_data = self.browse(cr, uid, sale_order_id)
		commission_total = 0
		for order_line in order_data.order_line:
			commission_total += order_line.commission_amount
			"""
			if order_line[2].get('product_uom_qty', False) or order_line[2].get('commission_amount', False):
				product = product_obj.browse(cr, uid, order_line[2]['product_id'])
				qty = product_uom_obj._compute_qty(cr, uid,
					order_line[2]['product_uom'], order_line[2]['product_uom_qty'], product.product_tmpl_id.uom_id.id)
				commission_total += (qty * order_line[2]['commission_amount'])
			"""
		self.write(cr, uid, [sale_order_id], {
			'commission_total': commission_total
			})
	
	def check_and_get_bon_number(self, cr, uid, bon_number, date_order):
		user_data = self.pool.get('res.users').browse(cr, uid, uid)
		branch_id = user_data.branch_id.id or None
		bon_book_same_number_ids = self.search(cr, uid, [
			('branch_id', '=', branch_id),
			('state', '!=', 'cancel'),
			('bon_number', '=', bon_number),
			('date_order', '>=', datetime.strptime(date_order,'%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d 00:00:00")),
			('date_order', '<=', datetime.strptime(date_order,'%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%d 23:59:59")),
		])
		if len(bon_book_same_number_ids) > 1:
			raise osv.except_orm(_('Bon book number error'),
				_('There is sale order with the same bon book number in your branch for that date.'))
		bon_book = self._get_bon_book(cr, uid, bon_number, context = None)
		if bon_book.total_used >= bon_book.total_sheets:
			raise osv.except_orm(_('Bon book is full'), _('All sheets in bon book have already been used.'))
		else:
			if bon_book.used_numbers:
				used_numbers = bon_book.used_numbers.split(', ')
				for used_number in used_numbers:
					if used_number == bon_number:
						raise osv.except_orm(_('Bon number error'), _('Bon number in the latest bon book has been used.'))
			return bon_book
	
	def _get_bon_book(self, cr, uid, bon_number, context = None):
		bon_book_obj = self.pool.get('tbvip.bon.book')
		user_data = self.pool.get('res.users').browse(cr, uid, uid)
		branch_id = user_data.branch_id.id or None
		bon_book_id = bon_book_obj.search(cr, uid, [
			('branch_id', '=', branch_id),
			('start_from', '<=', int(bon_number)),
			('end_at', '>=', int(bon_number)),
		], limit=1, order='issue_date DESC')
		bon_book = bon_book_obj.browse(cr, uid, bon_book_id)
		if not bon_book:
			raise osv.except_orm(_('Creating sale order error'),
				_('There is no bon book with the given number in your branch.'))
		return bon_book
	
	def onchange_bon_number(self, cr, uid, ids, bon_number, date_order, context=None):
		result = {}
		result['value'] = {}
		if bon_number and date_order:
			try:
				bon_book = self.check_and_get_bon_number(cr, uid, bon_number, date_order)
				if bon_book:
					result['value'].update({
						'employee_id': bon_book.employee_id.id
					})
			except Exception, e:
				result['value'].update({
					'employee_id': '',
					'bon_number': '',
				})
				result['warning'] = {
					'title': e.name,
					'message': e.value,
				}
			finally:
				return result
		return result
		
	def _update_bon_book(self, cr, uid, bon_number, date_order):
		bon_book_obj = self.pool.get('tbvip.bon.book')
		if bon_number and date_order:
			bon_book = self.check_and_get_bon_number(cr, uid, bon_number, date_order)
			if bon_book:
				temp_book_number = bon_book.used_numbers
				if not temp_book_number:
					temp_book_number = ""
				bon_book_obj.write(cr, uid, bon_book.id, {
					'total_used': bon_book.total_used + 1,
					'used_numbers': (temp_book_number + ', ' + bon_number) if (len(temp_book_number)>=1) else bon_number,
				})
		return
	
	def action_return(self, cr, uid, ids, context=None):
		for id in ids:
			delivery = self.action_view_delivery(cr, uid, [id], context=context)
			invoice = self.action_view_invoice(cr, uid, [id], context=context)
			stock_picking_id = delivery['res_id']
			invoice_id = invoice['res_id']
			if stock_picking_id:
				# stock_return_picking_obj = self.pool.get('stock.return.picking')
				return {
					"type": "ir.actions.act_window",
					"res_model": "sale.order.return",
					"src_model": "stock.picking",
					# "views": [[False, "form"]],
					# "res_id": stock_picking_id,
					"view_mode": "form",
					"target": "new",
					"key2": "client_action_multi",
					"multi": "True",
					'context': {
						'stock_picking_id': stock_picking_id,
						'stock_picking_ids': [stock_picking_id],
						'invoice_id' : invoice_id,
						'invoice_ids' : [invoice_id],
						'so_id' : id,
					}
				}


# PRINTS -------------------------------------------------------------------------------------------------------------------
	
	def print_sale_order(self, cr, uid, ids, context):
		if self.browse(cr,uid,ids)[0].order_line:
			return {
				'type' : 'ir.actions.act_url',
				'url': '/tbvip/print/sale.order/' + str(ids[0]),
				'target': 'self',
			}
		else:
			raise osv.except_osv(_('Print SO Error'),_('SO must have at least one line to be printed.'))

# ==========================================================================================================================

class sale_order_line(osv.osv):
	_inherit = 'sale.order.line'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Decimal Custom Order Line'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
		'commission': fields.char('Commission', help="Commission String"),
		'commission_amount': fields.float('Commission Amount'),
		'uom_category_filter_id': fields.related('product_id', 'product_tmpl_id', 'uom_id', 'category_id', relation='product.uom.categ', type='many2one',
			string='UoM Category', readonly=True)
	}
	
	_sql_constraints = [
		('so_quantity_less_than_zero', 'CHECK(product_uom_qty > 0)', 'Quantity should be more than zero.'),
		('so_price_unit_less_than_zero', 'CHECK(price_unit >= 0)', 'Price should be more than zero.'),
		('so_price_subtotal_less_than_zero', 'CHECK(price_subtotal >= 0)', 'Price subtotal should be more than zero.'),
	]
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		product_obj = self.pool.get('product.current.commission')
		current_commission = product_obj.get_current_commission(cr, uid, vals['product_id'])
		vals['commission'] = current_commission
		vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, None)
		if vals.get('product_id', False) and vals.get('price_unit', False) and \
			vals.get('price_type_id', False) and vals.get('product_uom', False):
			self.pool.get('price.list')._create_product_current_price_if_none(cr, uid,
				vals['price_type_id'], vals['product_id'], vals['product_uom'], vals['price_unit'])
		return super(sale_order_line, self).create(cr, uid, vals, context)
	
	def write(self, cr, uid, ids, vals, context=None):
		for id in ids:
			vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, id)
		for so_line in self.browse(cr, uid, ids):
			product_id = so_line.product_id.id
			price_type_id = so_line.price_type_id.id
			product_uom = so_line.product_uom.id
			price_unit = so_line.price_unit
			if vals.get('product_id', False): product_id = vals['product_id']
			if vals.get('price_type_id', False): price_type_id = vals['price_type_id']
			if vals.get('product_uom', False): product_uom = vals['product_uom']
			if vals.get('price_unit', False): price_unit = vals['price_unit']
			self.pool.get('price.list')._create_product_current_price_if_none(
				cr, uid, price_type_id, product_id, product_uom, price_unit)
		return super(sale_order_line, self).write(cr, uid, ids, vals, context)
	
	def unlink(self, cr, uid, ids, context=None):
		result = super(sale_order_line, self).unlink(cr, uid, ids, context)
		demand_line_obj = self.pool.get('tbvip.demand.line')
		demand_line_ids = demand_line_obj.search(cr, uid, [('sale_order_line_id','in',ids)])
		demand_line_obj.write(cr, uid, demand_line_ids, {
			'state': 'requested'
		})
		return result
	
	def _calculate_commission_amount(self, cr, uid, order_line, sale_order_line_id):
		product_uom_obj = self.pool.get('product.uom')
		product_obj = self.pool.get('product.product')
		commission_obj = self.pool.get('product.current.commission')
	
		if sale_order_line_id:
			sale_order_line = self.browse(cr, uid, sale_order_line_id)
			product_id = sale_order_line.product_id.id
			product_uom = sale_order_line.product_uom.id
			product_uom_qty = sale_order_line.product_uom_qty
			price_unit = sale_order_line.price_unit
			price_type_id = sale_order_line.price_type_id.id
	
		if order_line.get('product_id', False):
			product_id = order_line['product_id']
		if order_line.get('product_uom', False):
			product_uom = order_line['product_uom']
		if order_line.get('product_uom_qty', False):
			product_uom_qty = order_line['product_uom_qty']
		elif not sale_order_line_id:
			product_uom_qty = 0
		if order_line.get('price_unit', False):
			price_unit = order_line['price_unit']
		elif not sale_order_line_id:
			price_unit = 0
		if order_line.get('price_type_id', False):
			price_type_id = order_line['price_type_id']
	
		commission = commission_obj.get_current_commission(cr, uid, product_id)
			
		product = product_obj.browse(cr, uid, product_id)
		qty = product_uom_obj._compute_qty(cr, uid,
			product_uom, product_uom_qty, product.product_tmpl_id.uom_po_id.id)
		
		# ambil harga uom unit untuk perhitungan commission
		ir_model_data = self.pool.get('ir.model.data')
		uom_unit_id = ir_model_data.get_object(cr, uid, 'product', 'product_uom_unit').id
		product_current_price_obj = self.pool.get('product.current.price')
		price_unit_commission = product_current_price_obj.get_current_price(cr, uid, product.id, price_type_id, uom_unit_id)
		
		if not price_unit_commission:
			price_unit_commission = price_unit / qty * product_uom_qty
		try:
			valid_commission_string = commission_utility.validate_commission_string(commission)
			commission_amount = commission_utility.calculate_commission(valid_commission_string, price_unit_commission, qty)
		except commission_utility.InvalidCommissionException:
			return False
		return commission_amount
	
	# def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
	# 		uom=False, qty_uos=0, uos=False, name='', partner_id=False,
	# 		lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
	# 	result = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name,
	# 		partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, context)
	# 	product_obj = self.pool.get('product.current.commission')
	# 	current_commission = product_obj.get_current_commission(cr, uid, product)
	# 	result['value']['commission'] = current_commission
	# 	return result
	
	# def onchange_product_uom_qty(self, cr, uid, ids, pricelist, product, qty=0,
	# 		uom=False, qty_uos=0, uos=False, name='', partner_id=False,
	# 		lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, price_unit = False,context=None):
	# 	result = super(sale_order_line, self).product_id_change_with_wh(
	# 		cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id,
	# 		lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id, context=None)
	# 	result['value'].update({
	# 		'price_unit': price_unit,
	# 		'product_uom': uom,
	# 	})
	# 	return result
	
	# def onchange_product_id_price_list(self, cr, uid, ids, pricelist, product, qty=0,
	# 		uom=False, qty_uos=0, uos=False, name='', partner_id=False,
	# 		lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,
	# 		warehouse_id=False, parent_price_type_id=False, price_type_id=False, context=None):
	# 	product_conversion_obj = self.pool.get('product.conversion')
	# 	uom = product_conversion_obj.get_uom_from_auto_uom(cr, uid, uom, context).id
	# 	result = super(sale_order_line, self).onchange_product_id_price_list(cr, uid, ids, pricelist, product, qty,
	# 		uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag,
	# 		warehouse_id, parent_price_type_id, price_type_id, context)
	# 	temp = super(sale_order_line, self).onchange_product_uom(
	# 		cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id,
	# 		lang, update_tax, date_order, fiscal_position, context=None)
	# 	if result.get('domain', False) and temp.get('domain', False):
	# 		result['domain']['product_uom'] = result['domain']['product_uom'] + temp['domain']['product_uom']
	# 	product_obj = self.pool.get('product.product')
	# 	product_browsed = product_obj.browse(cr, uid, product)
	# 	result['value'].update({
	# 		'product_uom': uom if uom else product_browsed.uom_id.id,
	# 		'uom_category_filter_id': product_browsed.product_tmpl_id.uom_id.category_id.id
	# 	})
	#
	# 	return result
	def onchange_product_id_tbvip(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,
			warehouse_id=False, parent_price_type_id=False, price_type_id=False, sale_order_id=None, context=None):
		result = self.onchange_product_tbvip(cr, uid, ids, pricelist, product, qty,
			uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag,
			warehouse_id, parent_price_type_id, price_type_id, context)
		if product:
			product_obj = self.pool.get('product.product')
			product_browsed = product_obj.browse(cr, uid, product)
			result['value']['product_uom'] = product_browsed.uom_id.id
		
		# koreksi bon
		if sale_order_id:
			result['value']['order_id'] = sale_order_id
		return result
	
	def onchange_product_tbvip(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,
			warehouse_id=False, parent_price_type_id=False, price_type_id=False, context=None):
		product_conversion_obj = self.pool.get('product.conversion')
		uom = product_conversion_obj.get_uom_from_auto_uom(cr, uid, uom, context).id
		
		# dari sale tidak perlu karena di tempat lain di panggil menggunakan super
		# dari modul portal_sale dan sale_stock dan sale_multiple_payment tidak ada override onchange product id
		result_price_list = imported_price_list.sale.sale_order_line.onchange_product_id_price_list(self, cr, uid, ids, pricelist, product, qty,
			uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag,
			warehouse_id, parent_price_type_id, price_type_id, context)
		# hide warning dari price_list ketika tidak menemukan harga untuk uom dan product id yang dipilih
		result_price_list['warning'] = {}
		result = result_price_list
		temp = imported_product_custom_conversion.sale.sale_order_line.onchange_product_uom(self,
			cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id,
			lang, update_tax, date_order, fiscal_position, context=None)
		if result.get('domain', False) and temp.get('domain', False):
			result['domain']['product_uom'] = result['domain']['product_uom'] + temp['domain']['product_uom']
		
		custom_product_uom = False
		if temp['value'].get('product_uom', False):
			custom_product_uom = temp['value']['product_uom']
			# cari current price untuk product uom ini
			product_conversion_obj = self.pool.get('product.conversion')
			uom_record = product_conversion_obj.get_conversion_auto_uom(cr, uid, product, custom_product_uom)
			if uom_record:
				product_current_price_obj = self.pool.get('product.current.price')
				current_price = product_current_price_obj.get_current_price(cr, uid, product, price_type_id, uom_record.id)
				if current_price:
					result['value'].update({
						'price_unit': current_price
					})
			
		product_obj = self.pool.get('product.product')
		product_browsed = product_obj.browse(cr, uid, product)
		result['value'].update({
			'product_uom': custom_product_uom if custom_product_uom else uom if uom else product_browsed.uom_id.id,
			'uom_category_filter_id': product_browsed.product_tmpl_id.uom_id.category_id.id
		})
		
		product_obj = self.pool.get('product.current.commission')
		current_commission = product_obj.get_current_commission(cr, uid, product)
		result['value']['commission'] = current_commission
		
		return result
	
	def onchange_product_uom_qty_tbvip(self, cr, uid, ids, pricelist, product, qty=0, uom=False, qty_uos=0, uos=False,
			name='', partner_id=False, lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False,
			flag=False, warehouse_id=False, price_unit=False, discount_string=False, context=None):
		result = super(sale_order_line, self).onchange_product_uom_qty(
			cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id,
			lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id, price_unit, context=None)
		result['value'].pop('price_unit', None)
		result['value'].pop('product_uom', None)
		
		result_purchase_sale_discount = imported_purchase_sale_discount.sale_discount.sale_order_line.onchange_order_line(
			self, cr, uid, ids, qty, price_unit, uom, product, discount_string, context=None)
		if result_purchase_sale_discount and result_purchase_sale_discount['value'].get('price_subtotal', False):
			result['value'].update({
				'price_subtotal': result_purchase_sale_discount['value']['price_subtotal']
			})
		
		return result