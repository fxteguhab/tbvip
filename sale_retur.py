from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import models, api, _
from datetime import datetime, date, timedelta

_RETUR_STATE = [
	('draft', 'Draft'),
	('done', 'Done'),
]

class sale_retur(osv.osv):

	_name = 'sale.retur'
	_description = 'Sale Retur'

	def calc_amount(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for sale_retur in self.browse(cr, uid, ids, context=context):
			total = 0
			for line in sale_retur.retur_line_ids:
				total += line.price_unit_nett * line.qty
			result[sale_retur.id] = total
		return result


	_columns = {
		'journal_date': fields.datetime('Transaction Date', required=True),
		#'amount': fields.float('Amount', required=True),
		'amount': fields.function(calc_amount, type="float", string="Total Amount"),
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'employee_id': fields.many2one('hr.employee', 'Employee'),
		'retur_line_ids': fields.one2many('sale.retur.line', 'sale_retur_id', 'Product Retur:',  required=True, readonly=True, states={'draft':[('readonly',False)]}),
		'payment_sale_retur_journal': fields.many2one('account.journal', 'Journal for Cash Retur', domain=[('type','in',['cash','bank'])]),
		'partner_id': fields.many2one('res.partner', 'Customer'),
		'desc': fields.char('Description'),
		'state': fields.selection(_RETUR_STATE, 'State', required=True),
		'period' : fields.many2one('account.period', 'Force period'),
		'refund_journal_id' : fields.many2one('account.journal', 'Refund Journal'),
		'bon_number': fields.char('Bon Number Return '),
		'bon_book_id': fields.many2one('tbvip.bon.book', 'Bon Number Return'),

		'employee_id_old_sales': fields.many2one('hr.employee', 'Sell by'),
		'bon_number_old_sales': fields.char('Bon Number Sales'),
	}

	def onchange_old_bon_number(self, cr, uid, ids, bon_number, date_order, context=None):
		result = {}
		result['value'] = {}
		if bon_number and date_order:
			try:
				bon_book = self.check_and_get_old_bon_number(cr, uid, bon_number, date_order)
				if bon_book:
					result['value'].update({
						'employee_id_old_sales': bon_book.employee_id.id
					})
			except Exception, e:
				result['value'].update({
					'employee_id_old_sales': '',
					'bon_number_old_sales': '',
				})
				result['warning'] = {
					'title': e.name,
					'message': e.value,
				}
			finally:
				return result
		return result

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

	def check_and_get_old_bon_number(self, cr, uid, bon_number, date_order):
		user_data = self.pool.get('res.users').browse(cr, uid, uid)
		branch_id = user_data.branch_id.id or None
		bon_book = self._get_bon_book(cr, uid, bon_number, context = {})
		if bon_book.used_numbers:
			used_numbers = bon_book.used_numbers.split(', ')
			for used_number in used_numbers:
				if used_number == bon_number:
					return bon_book

	def check_and_get_bon_number(self, cr, uid, bon_number, date_order):
		user_data = self.pool.get('res.users').browse(cr, uid, uid)
		branch_id = user_data.branch_id.id or None
		bon_book = self._get_bon_book(cr, uid, bon_number, context = {})
		if bon_book.total_used >= bon_book.total_sheets:
			raise osv.except_orm(_('Bon book is full'), _('All sheets in bon book have already been used.'))
		else:
			if bon_book.used_numbers:
				used_numbers = bon_book.used_numbers.split(', ')
				for used_number in used_numbers:
					if used_number == bon_number:
						raise osv.except_orm(_('Bon number error'), _('Bon number in the latest bon book has been used.'))
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
			raise osv.except_orm(_('Creating sale return error'),
				_('There is no bon book with the given number in your branch.'))
		return bon_book

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
				default_journal_sales =  employee.default_journal_sales_retur_override.id
		return default_journal_sales
		'''
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		if user_data.default_journal_sales_retur_override:
			return user_data.default_journal_sales_retur_override.id
		else:
			if user_data.branch_id.default_journal_sales_retur:
				return user_data.branch_id.default_journal_sales_retur.id
			else:
				return None
		'''
		
	def _default_partner_id(self, cr, uid, context={}):
	# kalau penjualan cash, default customer adalah general customer
		model, general_customer_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')
		partner_id = general_customer_id
		return partner_id

	def _get_journal(self, cr, uid, context=None):
		"""
		Fungsi ini didapat dari account_invoice_refund tanpa ada perubahan fungsi
		"""
		obj_journal = self.pool.get('account.journal')
		user_obj = self.pool.get('res.users')
		if context is None:
			context = {}
		inv_type = context.get('type', 'out_invoice')
		company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
		type = (inv_type == 'out_invoice') and 'sale_refund' or \
			   (inv_type == 'out_refund') and 'sale' or \
			   (inv_type == 'in_invoice') and 'purchase_refund' or \
			   (inv_type == 'in_refund') and 'purchase'
		journal = obj_journal.search(cr, uid, [('type', '=', type), ('company_id','=',company_id)], limit=1, context=context)
		return journal and journal[0] or False

	_defaults = {
		'journal_date': lambda self, cr, uid, context: datetime.now(),
		'branch_id': _default_branch_id,
		'payment_sale_retur_journal': _default_payment_cash_journal,
		'partner_id': _default_partner_id,
		'state': 'draft',
		'refund_journal_id': _get_journal,
	}

	def button_retur(self, cr, uid, ids, context=None):		
		journal_obj = self.pool.get('account.journal')
		journal_entry_obj = self.pool.get('account.move')
		user_obj = self.pool.get('res.users')
		cashier = user_obj.browse(cr, uid, uid)
		company = cashier.company_id

		retur = self.browse(cr,uid,ids)
		journal_retur = retur.payment_sale_retur_journal
		partner_id = retur.partner_id
		name = str(journal_retur.name) 
		date = retur.journal_date
		amount = retur.amount
		refund_journal_id = retur.refund_journal_id

		period = retur.period.id
		if not retur.period.id:
			cr.execute("select name from ir_model_fields \
									where model = 'account.period' \
									and name = 'company_id'")
			result_query = cr.fetchone()
			if result_query:
				cr.execute("""select p.id from account_fiscalyear y, account_period p where y.id=p.fiscalyear_id \
							and date(%s) between p.date_start AND p.date_stop and y.company_id = %s limit 1""", (date, company.id,))
			else:
				cr.execute("""SELECT id
								from account_period where date(%s)
								between date_start AND  date_stop  \
								limit 1 """, (date,))
			res = cr.fetchone()
			if res:
				period = res[0]

		#print "refund_journal_id:"+str(retur.refund_journal_id)
		#print "branch:"+str(vals.get('branch_id'))
		#print "journal_retur_id: "+str(journal_retur.id)
		#print "default_debit_account_id: "+str(journal_retur.default_debit_account_id)

		entry_data = journal_entry_obj.account_move_prepare(cr, uid, journal_retur.id, date=date, ref=name)
		entry_data['line_id'] = [
			[0,False,{
				'name': name, 
				'account_id': journal_retur.default_credit_account_id.id, 
				'credit': amount, #vals.get('amount', 0),
				'debit': 0,
				'partner_id' : cashier.partner_id.id,
			}],
			[0,False,{
				'name': name, 
				'account_id': journal_retur.default_debit_account_id.id, 
				'debit': amount, #vals.get('amount', 0),
				'credit': 0,
				'partner_id' : partner_id.id,
			}],
		]

		new_entry_id = journal_entry_obj.create(cr, uid, entry_data, context=context)
		journal_entry_obj.post(cr, uid, [new_entry_id], context=context)

		inv_obj = self.pool.get('account.invoice')
		account_m_line_obj = self.pool.get('account.move.line')
		picking_obj = self.pool.get('stock.picking')
		model_obj = self.pool.get('ir.model.data')
		location_obj = self.pool.get('stock.location')
		stock_move_obj = self.pool.get('stock.move')
		warehouse_obj = self.pool.get('stock.warehouse')
		
		location_src = location_obj.browse(cr, uid, model_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')[1])
		location_dest = retur.branch_id.default_incoming_location_id
		warehouse_id = warehouse_obj.search(cr, uid, [('lot_stock_id', '=', location_src.id)], limit=1)
		warehouse = warehouse_obj.browse(cr, uid, warehouse_id, context)
		max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
		max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
		
		picking_id = picking_obj.create(cr, uid, {
			'picking_type_id': model_obj.get_object_reference(cr, uid, 'stock', 'picking_type_internal')[1],
			'move_type': 'direct',
			'note': 'Cash Transaction ' + location_src.name + '/' + location_dest.name,
			'location_id': location_src.id,
			'location_dest_id': location_dest.id,
			'origin': 'Retur - ' + str(name),
		}, context=context)
		#untuk setiap product, bikin stock movenya
		for line in retur.retur_line_ids:
			stock_move = stock_move_obj.create(cr, uid, vals={
				'name' : line.product_id.name_template,
				'warehouse_id': warehouse.id,
				'location_id': location_src.id,
				'location_dest_id': location_dest.id,
				#'sequence': max_sequence + 1,
				'product_id': line.product_id.id,
				'product_uom': line.product_id.uom_id.id,
				'picking_id': picking_id,
				'product_uom_qty': line.qty,
				'price_unit' : line.price_unit_nett,
				'origin': 'Retur - ' + str(name),
			}, context=context)
		# Transfer created picking
		picking_obj.do_transfer(cr, uid, picking_id, context)


		###################################################################################################################################################################
		price_type_ids = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])
		default_price_type_id = price_type_ids[0]

		retur_lines = []	
		for return_line in retur.retur_line_ids:
			values = {}
			values['quantity'] = return_line.qty
			values['price_subtotal']= return_line.qty * return_line.price_unit_nett
			values['price_unit'] = return_line.price_unit_nett
			values['origin'] = name
			values['product_id'] = return_line.product_id.id
			values['name'] = return_line.product_id.name_template
			values['partner_id'] = partner_id.id
			values['account_id'] = return_line.product_id.categ_id.property_account_income_categ.id #journal_retur.default_debit_account_id.id
			values['price_type_id'] = default_price_type_id
			if values:
				retur_lines.append((0, 0, values))
		
		#  Bikin Invoice refund
		refund_invoice = inv_obj.create(cr, uid, {
			'reference' : name,
			'date_due' : date,
			'number'  : False,
			'company_id' : cashier.company_id.id,
			'partner_id' : partner_id.id,
			'journal_id' : refund_journal_id.id,
 			'date_invoice': date,
 			'type' : 'out_refund',
 			'state' : 'draft',
 			'origin': name,
 			'invoice_line' : retur_lines,
 			'account_id' : journal_retur.default_debit_account_id.id,
 			'period_id': period,
		}, context=context)
		
		inv_obj.button_compute(cr, uid, refund_invoice)

		to_reconcile_ids = {}
		
		refund = inv_obj.browse(cr, uid, refund_invoice, context=context)
		refund.signal_workflow('invoice_open')
		
		for tmpline in refund.move_id.line_id:
			if tmpline.account_id.id == journal_retur.default_debit_account_id.id:
				if not to_reconcile_ids.get(tmpline.account_id.id, False):
					to_reconcile_ids.setdefault(tmpline.account_id.id, []).append(tmpline.id)
				else:
					to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)

		for account in to_reconcile_ids:
			account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
				writeoff_period_id=period,
				writeoff_journal_id = refund_journal_id.id,
				writeoff_acc_id=journal_retur.default_debit_account_id.id,
			)

		#self._update_bon_book(cr, uid, retur.bon_number, retur.journal_date)

		self.write(cr, uid, ids, {
			'state': 'done',
			'period':period,
		}, context=context)


class sale_retur_line(osv.osv):
	_name = 'sale.retur.line'
	
	_columns = {
		'sale_retur_id': fields.many2one('sale.retur', 'Sale Retur'),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'qty': fields.float('Qty', required=True),
		'price_unit_nett' : fields.float(related = "product_id.product_tmpl_id.list_price",string="Price Nett"),
	}
	
	_defaults = {
		'qty': lambda self, cr, uid, context: 1,
	}