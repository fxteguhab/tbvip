from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
import commission_utility
from openerp.tools.translate import _
from datetime import datetime, date
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
	def _default_amount_residual(self, cr, uid, ids, field_name, arg, context):
		result = {}
		for sale_order in self.browse(cr, uid, ids, context):
			result[sale_order.id] = 0
			if len(sale_order.invoice_ids) > 0:
				result[sale_order.id] = sale_order.invoice_ids[0].residual
		return result

	"""
	def _calculate_margin_total(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for order_data in self.browse(cr, uid, ids,context):
			result[order_data.id] = 0
			if (order_data.create_date )
			for order_line in order_data.order_line:
				result[order_data.id] += order_line.margin
			
		return result
	"""
	def _calculate_margin_total(self, cr, uid, sale_order_id):
		order_data = self.browse(cr, uid, sale_order_id)
		margin_total = 0

		for order_line in order_data.order_line:
			margin_total += order_line.margin
		
		self.write(cr, uid, [sale_order_id], {
			'total_margin': margin_total
			})
	

	_columns = {
		'commission_total': fields.float('Commission Total', readonly=True),
		#TEGUH@20180412 : bon book not required
		'bon_number': fields.char('Invoice No', readonly="True", states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
		'bon_book_id': fields.many2one('tbvip.bon.book', 'Invoice No'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		#TEGUH@20180412 : employee id  not required
		'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),
		'stock_location_id': fields.many2one('stock.location', 'Location'),
		'is_paid': fields.boolean('Paid ?'),
		'return_amount' : fields.float('Return Amount'),
		'return_id': fields.many2one('account.invoice', "Return", readonly=True),
		'amount_residual':fields.function(_default_amount_residual,type='float',string='Residual'),
		'total_margin' : fields.float('Margin', readonly=True),
		'date_due': fields.date('Due Date'),
		'kecamatan' : fields.many2one('tbvip.kecamatan', 'Kecamatan'),
		#'total_margin' : fields.function(_calculate_margin_total, type="float", string="Margin", store=True),
	}

	_sql_constraints = [
		('name_uniq', 'unique(name, company_id)', 'This order number already created'),
	]

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

	def _default_payment_cash_journal(self, cr, uid, context={}):
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		branch_id = user_data.branch_id.id
		branch_data = self.pool['tbvip.branch'].browse(cr,uid,branch_id)
		branch_employee = branch_data.employee_list
		default_journal_sales = None
		for employee in branch_employee:
			if employee.user_id.id == uid:
				default_journal_sales =  employee.default_journal_sales_override.id
		return default_journal_sales
				
		'''
		if user_data.default_journal_sales_override:
			return user_data.default_journal_sales_override.id
		else:
			if user_data.branch_id.default_journal_sales:
				return user_data.branch_id.default_journal_sales.id
			else:
				return None
		'''

	def _default_payment_receivable_journal(self, cr, uid, context={}):
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		branch_id = user_data.branch_id.id
		branch_data = self.pool['tbvip.branch'].browse(cr,uid,branch_id)
		journal_id = branch_data.default_journal_sales_bank.id
		return journal_id or None

		#journal_id = self.pool.get('account.journal').search(cr, uid, [('type', 'in', ['bank'])], limit=1)
		#return journal_id and journal_id[0] or None

	_defaults = {
		'partner_id': _default_partner_id,
		'branch_id': _default_branch_id,
		'shipped_or_taken': 'taken',
		'stock_location_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_outgoing_location_id.id,
		'is_paid': True,
		'payment_cash_journal': _default_payment_cash_journal,
		'payment_receivable_journal': _default_payment_receivable_journal,
		'payment_giro_journal' : _default_payment_receivable_journal,
		'payment_transfer_journal' : _default_payment_receivable_journal,
		'date_due' : fields.datetime.now,
		#,'bon_number' : '0'
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def action_ship_create(self, cr, uid, ids, context=None):
		"""
		Add source location_id to context
		"""
		if context is None:
			context = {}
		unfrozen_context = dict(context)
		unfrozen_context.update({
			'sale_location_id': self.browse(cr, uid, ids)[0].stock_location_id.id
		})
		result = super(sale_order, self).action_ship_create(cr, uid, ids, unfrozen_context)
		return result
	
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
		if not (vals.get('price_type_id',False)):
			price_type_ids = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])
			vals.update({
				'price_type_id' : price_type_ids[0]
			})
		new_id = super(sale_order, self).create(cr, uid, vals, context)
		self._calculate_commission_total(cr, uid, new_id)
		self._calculate_margin_total(cr, uid, new_id)
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
			#if not (vals.get('price_type_id',False)):
			#	price_type_ids = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])
			#	vals['price_type_id'] = price_type_ids[0]
			
			#print "vals_write :"+str(vals)	
			result = super(sale_order, self).write(cr, uid, sale_order_data.id, vals, context)
			
		if vals.get('order_line', False):
			for sale_id in ids:
				self._calculate_commission_total(cr, uid, sale_id)
				self._calculate_margin_total(cr, uid, sale_id)
		
		return result
	
	#def create_or_update_sale_history_from_sale_done(self, cr, uid, sale_ids, context={}):
		#sale_history_obj = self.pool.get('sale.history')
		#month_now = datetime.now().month
		#year_now = datetime.now().year
		#dict_product_sale = {}
		#for sale in self.browse(cr, uid, sale_ids):
		#	month_sale = datetime.strptime(sale.date_order, '%Y-%m-%d %H:%M:%S').month
		#	year_sale = datetime.strptime(sale.date_order, '%Y-%m-%d %H:%M:%S').year
		#	if month_sale!=month_now or year_now != year_sale:
		#		dict_product_sale = sale_history_obj.create_dict_for_sale_history(cr, uid, sale_ids, context)
		#	for product_id, dict_branch_id in dict_product_sale.iteritems():
		#		for branch_id, value in dict_branch_id.iteritems():
		#			# cari dahulu apakah sudah terdapat sale_history yang lama, jika ada maka write, jika tidak maka create
		#			history_id =  sale_history_obj.search(cr, uid, [('month', '=', month_sale),
		#				('year', '=', year_sale),
		#				('product_id', '=', product_id),
		#				('branch_id', '=', branch_id)], limit = 1)
		#			if history_id:
		#				sale_history = sale_history_obj.browse(cr, uid, history_id)
		#				sale_history_obj.write(cr, uid, history_id,  {'number_of_sales': sale_history.number_of_sales + value['qty']})
		#			else:
		#				sale_history_obj.create(cr, uid, {
		#					'product_id': product_id,
		#					'number_of_sales': value['qty'],
		#					'year' : year_sale,
		#					'month': month_sale,
		#					'branch_id': branch_id})
	
	# JUNED@20181003: _make_payment yang valid untuk implementasi tbvip adalah yang di 
	#sini, bukan yang di sale_multiple_payment
	def _make_payment(self, cr, uid, partner_id, amount, payment_method, invoice_id, journal_id=None, context={}):
		"""
		Register payment. Return
		"""
		if payment_method not in ['transfer', 'cash', 'receivable', 'giro']: return False
		if amount <= 0: return False
		if not journal_id:
			raise osv.except_osv(_('Payment Error'), _('Please supply journal for payment method %s.') % payment_method)
		
		voucher_obj = self.pool.get('account.voucher')
		journal_obj = self.pool.get('account.journal')
		account_move_line_obj = self.pool.get('account.move.line')
		invoice_obj = self.pool.get('account.invoice')
		#move_obj = self.pool.get('account.move')

	# cari di antara move line terkait invoice ini, nilai piutangnya
	# dicirikan dengan type account receivable
	# diasumsikan per invoice cuman ada 1 line yang piutang
		account_move_ids = account_move_line_obj.search(cr, uid, [
			('invoice','=',invoice_id),
			('account_id.type','=','receivable')
			])
		if len(account_move_ids) == 0:
			raise osv.except_osv(_('Payment Error'),_("There is no receivable account in this invoice's journal."))
		account_move = account_move_line_obj.browse(cr, uid, account_move_ids[0])

		invoice = invoice_obj.browse(cr, uid, invoice_id)
		bon_number = invoice.origin
		journal = journal_obj.browse(cr, uid, journal_id, context)

		# Prepare voucher values for payment
		voucher_vals = {
			'partner_id': partner_id.id,
			'payment_method_type': payment_method,
			'comment': 'Write-Off',
			'payment_option': 'without_writeoff',
			'pre_line': True,
			'amount': amount,
			'type': 'receipt',
			'reference': bon_number,
			'journal_id': journal_id,
			'account_id': journal.default_debit_account_id.id or journal.default_credit_account_id.id,
			'line_cr_ids': [(0, False, {
				'date_due': fields.date.today(),
				'reconcile': True if amount >= account_move.debit - account_move.credit else False,
				'date_original': fields.date.today(),
				'move_line_id': account_move.id,
				'amount_unreconciled': account_move.debit - amount, #account_move.credit,
				'amount': amount,
				'amount_original': account_move.debit,
				'account_id': account_move.account_id.id
			})],
		}

		# Create payment
		voucher_id = voucher_obj.create(cr, uid, voucher_vals, context=context)
		voucher_obj.signal_workflow(cr, uid, [voucher_id], 'proforma_voucher', context=context)
	
	# browse ulang supaya mendapatkan nilai residual terbaru, setelah ada pembayaran
	# di atas
	# kalau sisa invoice sudah 0, langsung tandai Paid
		invoice = invoice_obj.browse(cr, uid, invoice_id)
		#residual = invoice.residual
		if invoice.residual <= 0:
			invoice_obj.write(cr, uid, [invoice_id], {'reconciled': True}, context)

	def action_button_confirm(self, cr, uid, ids, context=None):

		############################################################################################################
		#
		#            ORIGINAL TBVIP SALE PART 
		#
		############################################################################################################
		invoice_obj = self.pool.get('account.invoice')
		picking_obj = self.pool.get('stock.picking')

		##################################################################################################
		#
		#
		#tambahan dari account receivable limit
		partner_obj = self.pool.get('res.partner')

		##################################################################################################
		#
		# 	TAMBAHAN DARI TBVIP POINT PAYROL
		# input points
		employee_point_obj = self.pool.get('hr.point.employee.point')
		employee_obj = self.pool.get('hr.employee')

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
					picking_obj.write(cr, uid,stock_picking_id, {'note': sale.customer_address})
					picking_obj.write(cr, uid,stock_picking_id, {'min_date': sale.delivery_date})
				# Make invoice open
				invoice_obj.signal_workflow(cr, uid, sale.invoice_ids.ids, 'invoice_open', context)
				#order = sale

				#sale_discount = float(order.sale_discount)
				self._make_payment(cr, uid, sale.partner_id, sale.payment_transfer_amount, 'transfer', sale.invoice_ids[0].id, journal_id=sale.payment_transfer_journal.id)
				self._make_payment(cr, uid, sale.partner_id, sale.payment_cash_amount, 'cash', sale.invoice_ids[0].id, journal_id=sale.payment_cash_journal.id)
				self._make_payment(cr, uid, sale.partner_id, sale.payment_receivable_amount, 'receivable', sale.invoice_ids[0].id, journal_id=sale.payment_receivable_journal.id)
				self._make_payment(cr, uid, sale.partner_id, sale.payment_giro_amount, 'giro', sale.invoice_ids[0].id, journal_id=sale.payment_giro_journal.id)
			else:
				raise osv.except_orm(_('Invoice No Empty'), _('You must fill Invoice No.'))
			
			if not sale.employee_id:
				raise osv.except_orm(_('Employee Empty'), _('Employee Name Error'))	

			################################################################################################
			#
			#		TAMBAHAN dari ACCOUNT RECEIVABLE LIMIT
			#
			###############################################################################################
			if partner_obj.is_credit_overlimit(cr, uid, sale.partner_id.id, sale.amount_total, context):
				if sale.partner_id.is_overlimit_enabled:
					self.write(cr, uid, [sale.id], {
						'is_receivable_overlimit': True,
						})
				else:
					raise osv.except_osv(_('Warning!'), _('Credit is / will be over-limit.'))

			################################################################################################
			#
			#		TAMBAHAN dari TBVIP PAINT PAYROLL
			#
			###############################################################################################
			value = sale.amount_total
			row_count = len(sale.order_line)
			qty_sum = 0
			#TEGUH @20180330 : tambah variable branch_id
			branch = sale.branch_id.name
			#TEGUH @20180330 : tambah variable cust_name untuk factor CUSTOMER_NAME, spy bisa add point berdasarkan (nama)customer
			cust_name = sale.partner_id.display_name
			for line in sale.order_line:
				qty_sum += line.product_uom_qty
			
			# sales confirm (who confirm and employee responsible for the sales)
			employee_point_obj.input_point(cr, uid,
				event_date=sale.date_order,
				activity_code='SALES',
				roles={
					'ADM': [employee_obj.get_employee_id_from_user(cr, uid, uid, context=context)],
					'EMP': [sale.employee_id.id],
				},
				required_parameters={
					'BON_VALUE': value,
					'BON_QTY_SUM': qty_sum,
					'BON_ROW_COUNT': row_count,
					'CUSTOMER_NAME' : cust_name,
				},
				reference='Sales Order - {}'.format(sale.name),
				context=context)
			
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
		bon_book = self._get_bon_book(cr, uid, bon_number, context = {})
		'''
		if bon_book.total_used >= bon_book.total_sheets:
			raise osv.except_orm(_('Bon book is full'), _('All sheets in bon book have already been used.'))
		else:
			if bon_book.used_numbers:
				used_numbers = bon_book.used_numbers.split(', ')
				for used_number in used_numbers:
					if used_number == bon_number:
						raise osv.except_orm(_('Bon number error'), _('Bon number in the latest bon book has been used.'))
			return bon_book
		'''
		#if bon_book.used_numbers:
			#used_numbers = bon_book.used_numbers.split(', ')
			#for used_number in used_numbers:
			#	if used_number == bon_number:
			#		raise osv.except_orm(_('Bon number error'), _('Bon number in the latest bon book has been used.'))
		return bon_book

	def _get_bon_book(self, cr, uid, bon_number, context = {}):
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
		
		result['value'].update({
						'date_due': date_order
					})

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

	def _prepare_invoice(self, cr, uid, order, lines, context=None):
	 	result = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context)
		result.update({
					'date_invoice' : order.date_order,
					'reference': order.name,
					'name': order.name,
					'supplier_invoice_number' : order.bon_number,
					})
		return result

	def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,lazy=True):
		hide_total = self.pool.get('ir.config_parameter').get_param(cr, uid, 'sum_total_admin_only','0')
		if (hide_total == '1') and (uid !=SUPERUSER_ID):
			if ('amount_total' in fields):
				fields.remove('amount_total')
			if ('payment_cash_amount' in fields):
				fields.remove('payment_cash_amount')
			if ('payment_transfer_amount' in fields):
				fields.remove('payment_transfer_amount')
			if ('payment_receivable_amount' in fields):
				fields.remove('payment_receivable_amount')	
			if ('payment_giro_amount' in fields):
				fields.remove('payment_giro_amount')
			if ('sale_discount_amount' in fields):
				fields.remove('sale_discount_amount')
			if ('total_discount_amount' in fields):
				fields.remove('total_discount_amount')					
		return super(sale_order, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby, lazy)

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
	
# FIELD FUNCTION ------------------------------------------------------------------------------------------------------------------
	def _calc_margin(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		product_uom_obj		 = self.pool.get('product.uom')
		price_type_id_buys   = self.pool.get('price.type').search(cr, uid, [('type','=','buy'),('is_default','=',True),])
		price_type_id_buy    = price_type_id_buys[0]
		
		for line in self.browse(cr, uid, ids, context=context):
			sell_price_unit_nett = line.price_unit_nett
			buy_price_unit_nett = line.product_id.standard_price
			if buy_price_unit_nett > 0:
				buy_price_unit = buy_price_unit_nett
			else:
				#ambil dari current price buy
				buy_price_unit_price_list = self.pool.get('product.current.price').get_current(cr, uid, line.product_id.id,price_type_id_buy, line.product_uom.id,field="nett", context=context)
				if buy_price_unit_price_list > 0:
					buy_price_unit = buy_price_unit_price_list 
					self.pool.get('product.product')._set_price(cr,uid,line.product_id.id,buy_price_unit,'standard_price')
				else:
					buy_price_unit = 0

			if line.product_id.uom_id != line.product_id.uom_po_id :
				uom_po_factor = product_uom_obj.browse(cr, uid, line.product_id.uom_po_id.id)
				uom_factor = product_uom_obj.browse(cr, uid, line.product_id.uom_id.id)
				factor = 1.0
				if uom_po_factor.uom_type == 'reference':
					if uom_factor.uom_type == 'smaller':
						factor =  uom_po_factor.factor / uom_factor.factor
					else:
						factor =  uom_po_factor.factor * uom_factor.factor
				else:
					if uom_po_factor.uom_type == 'smaller':
						factor =  uom_factor.factor / uom_po_factor.factor
					else:
						factor =  uom_factor.factor * uom_po_factor.factor

				buy_price_unit = buy_price_unit * factor

			result[line.id] = (sell_price_unit_nett - buy_price_unit) * line.product_uom_qty

		"""
		for line in self.browse(cr, uid, ids, context=context):
			if line.price_unit_nett > 0:
				sell_price_unit_nett = line.price_unit_nett
				buy_price_unit_nett = line.product_id.standard_price
				
				if buy_price_unit_nett > 5:
					buy_price_unit = buy_price_unit_nett
				else:
					#ambil dari current price buy
					buy_price_unit_price_list = self.pool.get('product.current.price').get_current(cr, uid, line.product_id.id,price_type_id_buy, line.product_uom.id,field="nett", context=context)
					if buy_price_unit_price_list > 0:
						buy_price_unit = buy_price_unit_price_list 
						self.pool.get('product.product')._set_price(cr,uid,line.product_id.id,buy_price_unit,'standard_price')
					else:
						buy_price_unit = 0

				result[line.id] = (sell_price_unit_nett - buy_price_unit) * line.product_uom_qty
			else:
				result[line.id] = 0
		"""

		return result

# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Decimal Custom Order Line'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
		'commission': fields.char('Commission', help="Commission String"),
		'commission_amount': fields.float('Commission Amount'),
		'uom_category_filter_id': fields.related('product_id', 'product_tmpl_id', 'uom_id', 'category_id', relation='product.uom.categ', type='many2one',
			string='UoM Category', readonly=True),

		'stock_location_id': fields.related('order_id','stock_location_id',type='many2one', relation='stock.location', store=True, string='Location'),
		'margin' : fields.function(_calc_margin, type="float", string="Margin"),
		#overide
		#'salesman_id':fields.related('order_id', 'employee_id',type='many2one', relation='hr.employee', store=True, string='Salesperson'),
		
	}
	
	_sql_constraints = [
		('so_quantity_less_than_zero', 'CHECK(product_uom_qty > 0)', 'Quantity should be more than zero.'),
		('so_price_unit_less_than_zero', 'CHECK(price_unit >= 0)', 'Price should be more than zero.'),
	]
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		new_store_mode = self.pool.get('ir.config_parameter').get_param(cr, uid, 'new_store_mode','0')
		if (new_store_mode == '1') and not vals.get('product_id',False):		
			#product_obj = self.pool.get('product.current.commission')
			#current_commission = product_obj.get_current_commission(cr, uid, vals['product_id'])
			#vals['commission'] = current_commission
			#vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, None)
			#TEGUH@20180502 : tambah field disc

			#create new product
			product_name = vals.get('name','')
			template_id = self.pool.get('product.template').create(cr, uid, {'name' : product_name },context = context)
			print"template_id:"+str(template_id)
			product_id = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id','=',template_id)],limit = 1,context=context)[0]
			
			if (product_id):
				print "product_id:"+str(product_id)
				vals.update({
					'product_id' : product_id,
					})
				
				print "vals:"+str(vals)

				new_id = super(sale_order_line, self).create(cr, uid, vals, context)
				new_data = self.browse(cr, uid, new_id)
				
				#new price
				disc = ''
				if vals.get('product_id', False) and vals.get('price_unit', False) and \
					vals.get('price_type_id', False) and vals.get('product_uom', False):
					self.pool.get('price.list')._create_product_current_price_if_none(cr, uid,
						vals['price_type_id'], product_id, vals['product_uom'], vals['price_unit'], disc,
						partner_id=new_data.order_id.partner_id.id)
			return new_id
		else: 
			return super(sale_order_line, self).create(cr, uid, vals, context)
	'''
	def write(self, cr, uid, ids, vals, context=None):
		new_store_mode = self.pool.get('ir.config_parameter').get_param(cr, uid, 'new_store_mode','0')
		if (new_store_mode == '1') and not vals.get('product_id',False):	
		#	for id in ids:
		#		vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, id)
			for so_line in self.browse(cr, uid, ids):
				product_id = so_line.product_id.id
				price_type_id = so_line.price_type_id.id
				product_uom = so_line.product_uom.id
				price_unit = so_line.price_unit
				#TEGUH@20180502 : tambah field disc
				disc = ''
				if vals.get('product_id', False): product_id = vals['product_id']
				if vals.get('price_type_id', False): price_type_id = vals['price_type_id']
				if vals.get('product_uom', False): product_uom = vals['product_uom']
				if vals.get('price_unit', False): price_unit = vals['price_unit']
				self.pool.get('price.list')._create_product_current_price_if_none(
					cr, uid, price_type_id, product_id, product_uom, price_unit, disc,
					partner_id=so_line.order_id.partner_id.id)
		
		return super(sale_order_line, self).write(cr, uid, ids, vals, context)
	'''
	
	def unlink(self, cr, uid, ids, context=None):
		result = super(sale_order_line, self).unlink(cr, uid, ids, context)
		demand_line_obj = self.pool.get('tbvip.demand.line')
		demand_line_ids = demand_line_obj.search(cr, uid, [('sale_order_line_id','in',ids)])
		demand_line_obj.write(cr, uid, demand_line_ids, {
			'state': 'requested'
		})
		return result
	'''
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
		#price_unit_commission = product_current_price_obj.get_current(cr, uid, product.id, price_type_id, uom_unit_id)
		#if not price_unit_commission:
		#	price_unit_commission = price_unit / qty * product_uom_qty
		price_unit_commission = price_unit / qty * product_uom_qty
		try:
			valid_commission_string = commission_utility.validate_commission_string(commission)
			commission_amount = commission_utility.calculate_commission(valid_commission_string, price_unit_commission, qty)
		except commission_utility.InvalidCommissionException:
			return False
		return commission_amount
	'''
	def _calculate_commission_amount2(self, cr, uid, product_id,product_uom_qty,product_uom, price_unit_nett):		
		commission_obj = self.pool.get('product.current.commission')
		commission = commission_obj.get_current_commission(cr, uid, product_id)
		try:
			valid_commission_string = commission_utility.validate_commission_string(commission)
			commission_amount = commission_utility.calculate_commission(valid_commission_string, price_unit_nett, product_uom_qty)
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
		general_customer_id  = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')

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
		commission_amount = 0
		custom_product_uom = False
		if temp['value'].get('product_uom', False):
			custom_product_uom = temp['value']['product_uom']
			# cari current price untuk product uom ini
			product_conversion_obj = self.pool.get('product.conversion')
			uom_record = product_conversion_obj.get_conversion_auto_uom(cr, uid, product, custom_product_uom)
			if uom_record:
				product_current_price_obj = self.pool.get('product.current.price')
				current_price = product_current_price_obj.get_current(cr, uid, product, price_type_id, uom_record.id, partner_id=partner_id)
				if (current_price == 0):
					current_price = product_current_price_obj.get_current(cr, uid, product, price_type_id, uom_record.id, partner_id=general_customer_id[1])

				if current_price:
					result['value'].update({
						'price_unit': current_price
					})
					commission_amount = self._calculate_commission_amount2(cr,uid,product,qty,uom,current_price)
			
		product_obj = self.pool.get('product.product')
		product_browsed = product_obj.browse(cr, uid, product)
		result['value'].update({
			'product_uom': custom_product_uom if custom_product_uom else uom if uom else product_browsed.uom_id.id,
			'uom_category_filter_id': product_browsed.product_tmpl_id.uom_id.category_id.id
		})
		
		product_obj = self.pool.get('product.current.commission')
		current_commission = product_obj.get_current_commission(cr, uid, product)
		result['value']['commission'] = current_commission
		
		
		result['value']['commission_amount'] = commission_amount
		return result
	
	def onchange_product_uom_qty_tbvip(self, cr, uid, ids, pricelist, product, qty=0, uom=False, qty_uos=0, uos=False,
			name='', partner_id=False, lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False,
			flag=False, warehouse_id=False, price_unit=False, discount_string=False, commission = False,context=None):
		result = super(sale_order_line, self).onchange_product_uom_qty(
			cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id,
			lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id, price_unit, context=None)
		result['value'].pop('price_unit', None)
		result['value'].pop('product_uom', None)
		
		result_purchase_sale_discount = imported_purchase_sale_discount.sale_discount.sale_order_line.onchange_order_line(
			self, cr, uid, ids, qty, price_unit, uom, product, discount_string, context=None)
		
		commission_amount = self._calculate_commission_amount2(cr,uid,product,qty,uom,result_purchase_sale_discount['value']['price_unit_nett'])

		if result_purchase_sale_discount and result_purchase_sale_discount['value'].get('price_subtotal', False):
			result['value'].update({
				'price_subtotal': result_purchase_sale_discount['value']['price_subtotal'],
				'commission_amount' : commission_amount,
			}) 
		
		return result

	def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
		result = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
		price_type_id_buys   = self.pool.get('price.type').search(cr, uid, [('type','=','buy'),('is_default','=',True),])
		price_type_id_buy    = price_type_id_buys[0]
		price_type_id_sells  = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])
		price_type_id_sell   = price_type_id_sells[0]
		general_customer_id  = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')
		sell_price_unit 	 = self.pool.get('product.current.price').get_current(cr, uid, line.product_id.id,price_type_id_sell, line.product_uom.id, partner_id = general_customer_id[1], context=context)
		sell_price_disc		 = self.pool.get('product.current.price').get_current(cr, uid, line.product_id.id,price_type_id_sell, line.product_uom.id, partner_id = general_customer_id[1],field="disc", context=context)
		sell_price_unit_nett = self.pool.get('product.current.price').get_current(cr, uid, line.product_id.id,price_type_id_sell, line.product_uom.id, partner_id = general_customer_id[1],field="nett", context=context)
		
		#ambil harga beli dari last invoice if null then ambil dari price list
		nett_price = 0
		invoice_obj = self.pool.get('account.invoice.line')
		invoice_line_id = invoice_obj.search(cr, uid, [('product_id','=',line.product_id.id),('purchase_line_id','!=',False)],order='create_date DESC')
		if invoice_line_id:
			idx = 0
			invoice_line = invoice_obj.browse(cr, uid, invoice_line_id[idx])
			while ((invoice_line.price_subtotal <= 0) or (invoice_line.quantity <= 0)) and (idx < len(invoice_line_id)-1):
				idx += 1
				invoice_line = invoice_obj.browse(cr, uid, invoice_line_id[idx])

			price_subtotal = invoice_line.price_subtotal
			product_qty = invoice_line.quantity #if invoice_line.quantity > 0 else 1
			nett_price = price_subtotal / product_qty
			if nett_price > 0:
				buy_price_unit = nett_price
			else:
				buy_price_unit = self.pool.get('product.current.price').get_current(cr, uid, line.product_id.id,price_type_id_buy, line.product_uom.id, field="nett", context=context)
		else:
			buy_price_unit = self.pool.get('product.current.price').get_current(cr, uid, line.product_id.id,price_type_id_buy, line.product_uom.id, field="nett", context=context)

		result.update({
			'price_type_id': line.price_type_id.id,
			'buy_price_unit' : buy_price_unit,
			'price_unit_old' : sell_price_unit,
			'price_unit_nett_old' : sell_price_unit_nett,
			'discount_string_old' : sell_price_disc,
			'sale_line_id':line.id,
			})

		return result

class sale_report(osv.osv):
	_inherit = "sale.report"

	_columns = {
		#TEGUH@20180401 : tambah field employee_id & branch
		'user_id': fields.many2one('res.users', 'Kasir', readonly=True),
		'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', readonly=True),

		#'cost_total': fields.float('Total Cost', readonly=True),
		#'margin_total': fields.float('Total Margin', readonly=True),
	}


	def _select(self):
		select_str = """
			WITH currency_rate (currency_id, rate, date_start, date_end) AS (
					SELECT r.currency_id, r.rate, r.name AS date_start,
						(SELECT name FROM res_currency_rate r2
						WHERE r2.name > r.name AND
							r2.currency_id = r.currency_id
						 ORDER BY r2.name ASC
						 LIMIT 1) AS date_end
					FROM res_currency_rate r
				)
			 SELECT min(l.id) as id,
					l.product_id as product_id,
					t.uom_id as product_uom,
					sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
					sum((l.product_uom_qty / u.factor * u2.factor) * ((l.price_unit - l.discount1) / u2.factor)) as price_total,
					count(*) as nbr,
					s.date_order as date,
					s.date_confirm as date_confirm,
					s.partner_id as partner_id,
					s.user_id as user_id,
					s.employee_id as employee_id,
					s.branch_id as branch_id,
					s.company_id as company_id,
					extract(epoch from avg(date_trunc('day',s.date_confirm)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
					l.state,
					t.categ_id as categ_id,
					s.pricelist_id as pricelist_id,
					s.project_id as analytic_account_id,
					s.section_id as section_id
		"""
		return select_str

	def _group_by(self):
		group_by_str = """
			GROUP BY l.product_id,
					l.order_id,
					t.uom_id,
					t.categ_id,
					s.date_order,
					s.date_confirm,
					s.partner_id,
					s.user_id,
					s.employee_id,
					s.branch_id,
					s.company_id,
					l.state,
					s.pricelist_id,
					s.project_id,
					s.section_id
		"""
		return group_by_str