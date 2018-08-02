from datetime import datetime, timedelta
from openerp import api
from openerp.osv import osv, fields
from openerp.tools.translate import _

# ==========================================================================================================================

class account_journal_edc(osv.osv):
	_inherit = 'account.journal.edc'

# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'current_branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
# ==========================================================================================================================

class account_invoice(osv.osv):
	_inherit = 'account.invoice'
	
	# FIELD FUNCTION METHOD ----------------------------------------------------------------------------------------------------
	
	def _qty_sum(self, cr, uid, ids, field_name, arg, context):
		result = {}
		for invoice_data in self.browse(cr, uid, ids, context):
			result[invoice_data.id] = 0
			for invoice_line_data in invoice_data.invoice_line:
				result[invoice_data.id] += invoice_line_data.quantity
		return result
	
	def _row_count(self, cr, uid, ids, field_name, arg, context):
		result = {}
		for invoice_data in self.browse(cr, uid, ids, context):
			result[invoice_data.id] = len(invoice_data.invoice_line)
		return result
	
# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'qty_sum': fields.function(_qty_sum, type="integer", string="Qty Sum"),
		'row_count': fields.function(_row_count, type="integer", string="Row Count"),
		'related_sales_bon_number': fields.char("Nomor Bon", readonly=True),
	}
	
	def invoice_auto_done(self, cr, uid, ids, context=None):
		for invoice in self.browse(cr, uid, ids):
			invoice.signal_workflow('invoice_open')
	
	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		"""
		Update name_search (like in m2o search) domain to search with sale bon number for today (in infix):
		('number', '=', name)
			OR (('related_sales_bon_number', '=', name)
				AND (date_invoice', '>=', today.strftime('%Y-%m-%d'))
				AND ('date_invoice', '<', tommorow.strftime('%Y-%m-%d'))
			)
		"""
		args = args or []
		recs = self.browse()
		if name:
			today = datetime.today()
			tommorow = datetime.today() + timedelta(1)
			recs = self.search([
					'|',
					('number', '=', name),
					'&', ('related_sales_bon_number', '=', name),
					'&', ('date_invoice', '>=', today.strftime('%Y-%m-%d')),
					('date_invoice', '<', tommorow.strftime('%Y-%m-%d'))] + args, limit=limit)
		if not recs:
			recs = self.search([('name', operator, name)] + args, limit=limit)
		return recs.name_get()

# ==========================================================================================================================

class account_invoice_line(osv.osv):
	_inherit = 'account.invoice.line'

	_columns = {
		'price_type_id': fields.many2one('price.type', 'Price Type', ondelete='restrict'),
		'price_unit_old': fields.float(string = 'Price Old'),
		'price_unit_nett_old': fields.float(string = 'Nett Old'),
		'discount_string_old': fields.char(string = 'Disc Old'),
		'sell_price_unit': fields.float('Sales Price'),
	}
	
	def _cost_price_watcher(self, cr, uid, vals, context):
		price_unit_nett_old = vals['price_unit_nett_old'] if 'price_unit_nett_old' in vals else 0
		price_unit_nett = vals['price_unit_nett'] if 'price_unit_nett' in vals else 0

		if ((price_unit_nett_old > 0) and (price_unit_nett_old != price_unit_nett)):
			account_invoice_obj = self.pool.get('account.invoice')
			message="There is a change on cost price for %s in Invoice %s. From: %s to %s." % (vals['name'],vals['invoice_id'],price_unit_nett_old,price_unit_nett)		
			account_invoice_obj.message_post(cr, uid, vals['invoice_id'], body=message)				

	
	def create(self, cr, uid, vals, context={}):		
		new_id = super(account_invoice_line, self).create(cr, uid, vals, context=context)		
		# otomatis create current price kalo belum ada 
		if vals.get('price_type_id', False) and vals.get('uos_id', False):
			new_data = self.browse(cr, uid, new_id)
			discount_string = vals['discount_string'] if 'discount_string' in vals else "0"
			self.pool.get('price.list')._create_product_current_price_if_none(cr, uid,
				vals['price_type_id'], vals['product_id'], vals['uos_id'], vals['price_unit'],
				discount_string, partner_id=new_data.invoice_id.partner_id.id)
			
			#check for changes and send notif
			self._cost_price_watcher(cr, uid, vals,  context)

			#force create new price	
			price_unit_nett_old = vals['price_unit_nett_old'] if 'price_unit_nett_old' in vals else 0
			price_unit_nett = vals['price_unit_nett'] if 'price_unit_nett' in vals else 0
			if ((price_unit_nett_old > 0) and (price_unit_nett_old != price_unit_nett)):
				product_current_price_obj = self.pool.get('product.current.price')
				now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
				domain = [
					('price_type_id', '=', vals['price_type_id']),
					('product_id', '=', vals['product_id']),
					('start_date','<=',now),
					('partner_id','=',new_data.invoice_id.partner_id.id),
				]
				product_current_price_ids = product_current_price_obj.search(cr, uid, domain, order='start_date DESC', limit=1)
				if len(product_current_price_ids) == 0:
					product_current_price_obj.create(cr, uid, {
					'price_type_id': vals['price_type_id'],
					'product_id': vals['product_id'],
					'start_date': now,
					'partner_id': new_data.invoice_id.partner_id.id,
					'uom_id_1': vals['uos_id'],
					'price_1': vals['price_unit'],
					'disc_1' : discount_string,	
					})
				else:
					product_current_price = product_current_price_obj.browse(cr, uid, product_current_price_ids)[0]
					product_current_price_obj.write(cr, uid, [product_current_price.id], {
						'product_id': vals['product_id'],
						'price_1': vals['price_unit'],
						'disc_1' : discount_string,	
					})

		return new_id

	def write(self, cr, uid, ids, vals, context={}):
		result = super(account_invoice_line, self).write(cr, uid, ids, vals, context=context)	
		# bila user mengubah salah satu dari empat field di bawah ini, cek dan update
		# current price bila perlu
		if any(field in vals.keys() for field in ['product_id','price_type_id','uos_id','price_unit','discount_string']):		
			for invoice_line in self.browse(cr, uid, ids):
			# gunakan price_type_id yang di line
				price_type_id = invoice_line.price_type_id.id
			# kalau ngga ada, pakai yang di vals
				if not price_type_id:
					price_type_id = vals.get('price_type_id', None)
			# kalau price_type_id masih kosong, pakai default sesuai type invoice ybs
				if not price_type_id:
					if invoice_line.invoice_id.type in ['in_invoice']:
						price_type = 'buy'
					else:
						price_type = 'sell'
					
					price_type_ids = self.pool.get('price.type').search(cr, uid, [
						('type','=',price_type),
						('is_default','=',True),
						])
				# give up, next record please!
					if len(price_type_ids) == 0: continue
					price_type_id = price_type_ids[0]
			# bikin product current price baru bila belum ada 
				product_id = invoice_line.product_id.id
				product_uom = invoice_line.uos_id.id
				price_unit = invoice_line.price_unit
				discount_string = invoice_line.discount_string
				if vals.get('product_id', False): product_id = vals['product_id']
				if vals.get('uos_id', False): product_uom = vals['product_uom']
				if vals.get('price_unit', False): price_unit = vals['price_unit']
				if vals.get('discount_string', False): discount_string = vals['discount_string']	
				self.pool.get('price.list')._create_product_current_price_if_none(
					cr, uid, price_type_id, product_id, product_uom, price_unit, discount_string,
					partner_id=invoice_line.invoice_id.partner_id.id)
				
				#check for changes and send notif
				vals['price_unit_old'] = invoice_line.price_unit_old
				vals['discount_string_old'] = invoice_line.discount_string_old
				vals['price_unit_nett_old'] = invoice_line.price_unit_nett_old
				vals['invoice_id'] = invoice_line.invoice_id.id
				vals['name'] = invoice_line.name
				vals['discount_string'] = invoice_line.discount_string
				vals['sell_price_unit'] = invoice_line.sell_price_unit
				
				#check for changes and send notif
				self._cost_price_watcher(cr, uid, vals,  context)
				#force create new price	
				price_unit_nett_old = vals['price_unit_nett_old'] if 'price_unit_nett_old' in vals else 0
				price_unit_nett = vals['price_unit_nett'] if 'price_unit_nett' in vals else 0
				#force create new price	
				if ((price_unit_nett_old > 0) and (price_unit_nett_old != price_unit_nett)):
					product_current_price_obj = self.pool.get('product.current.price')
					now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
					domain = [
						('price_type_id', '=', price_type_id),
						('product_id', '=', product_id),
						('start_date','<=',now),
						('partner_id','=',invoice_line.invoice_id.partner_id.id),
					]
					product_current_price_ids = product_current_price_obj.search(cr, uid, domain, order='start_date DESC', limit=1)
					if len(product_current_price_ids) == 0:
						product_current_price_obj.create(cr, uid, {
						'price_type_id': price_type_id,
						'product_id': product_id,
						'start_date': now,
						'partner_id': invoice_line.invoice_id.partner_id.id,
						'uom_id_1': product_uom,
						'price_1': price_unit,
						'disc_1' : discount_string,	
						})	
					else:
						product_current_price = product_current_price_obj.browse(cr, uid, product_current_price_ids)[0]
						product_current_price_obj.write(cr, uid, [product_current_price.id], {
						'product_id': product_id,
						'price_1': price_unit,
						'disc_1' : discount_string,	
					})

		return result

# ==========================================================================================================================

class account_move_line(osv.osv):
	_inherit = 'account.move.line'
	_description = 'Modifikasi untuk menambah amount di SO'
	
	def create(self, cr, uid, vals, context={}):
		new_id = super(account_move_line, self).create(cr, uid, vals, context=context)
		if context.get('payment_method_type', False) and context.get('sale_order_id', False):
			sale_order_obj = self.pool.get('sale.order')
			payment_method_type = context['payment_method_type']
			sale_order_id = context['sale_order_id']
			sale_order_data = sale_order_obj.browse(cr, uid, sale_order_id)
			if payment_method_type and vals.get('debit', False):
				if payment_method_type == 'transfer' or payment_method_type == 'receivable':
					sale_order_obj.write(cr, uid, sale_order_id, {
						'is_complex_payment': True
					})
		return new_id

	def name_get(self, cr, uid, ids, context=None):
		if not ids: return []
		result = []
	# name invoice line mengacu ke supplier invoice number (disimpan di name)
	# note: supplier invoice number harus diisi sebelum invoice divalidate, kalau tidak 
	# maka yang terismpan di name ini adalah nomor invoice (EXJ/....)
		for line in self.browse(cr, uid, ids, context=context):
			if line.ref:
				result.append((line.id, line.name or line.move_id.name))
			else:
				result.append((line.id, line.move_id.name))
		return result


# ==========================================================================================================================

class tbvip_day_end(osv.osv):
	_name = 'tbvip.day.end'
	_description = 'Ending Day'
	
	def calculate_omzet_cash(self, cr, uid, kas_id, context={}):
		# kas balance
		if kas_id:
			account_account_obj = self.pool.get('account.account')
			if isinstance(kas_id, int):
				return account_account_obj.browse(cr, uid, kas_id, context).balance
			else:
				return kas_id.balance
		else:
			return 0
	
	def calculate_amend_number(self, cr, uid, kas_id, day_end_date, context={}):
		day_end_date_datetime = datetime.strptime(day_end_date, '%Y-%m-%d %H:%M:%S')
		day_end_ids = self.search(cr, uid, [
			('kas_id', '=', kas_id),
			('day_end_date', '>=', day_end_date_datetime.strftime("%Y-%m-%d 00:00:00")),
			('day_end_date', '<', (day_end_date_datetime + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")),
		], context=context)
		return len(day_end_ids)
	
	def _default_modal_cash(self, cr, uid, context={}):
		# default from employee setting
		employee_obj = self.pool.get('hr.employee')
		employee_ids = employee_obj.search(cr, uid, [
			('user_id', '=', uid),
		], limit=1, context=context)
		if employee_ids and len(employee_ids) == 1:
			return employee_obj.browse(cr, uid, employee_ids[0], context=context).default_modal_cash
		else:
			return 0
	
	def _default_branch_id(self, cr, uid, context={}):
		# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.id or None
	
	_columns = {
		'day_end_date': fields.datetime('Day End Date', required=True),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		'amend_number': fields.integer('Amend Number'),
		'kas_id': fields.many2one('account.account', 'Kas', required=True, domain=[('is_tbvip_kas', '=', True)]),

		'qty_100': fields.integer('100', help='A Hundred Quantity'),
		'qty_200': fields.integer('200', help='Two Hundred Quantity'),
		'qty_500': fields.integer('500', help='Five Hundred Quantity'),
		'qty_1000': fields.integer('1000', help='A Thousand Quantity'),
		'qty_2000': fields.integer('2000', help='Two Thousand Quantity'),
		'qty_5000': fields.integer('5000', help='Five Thousand Quantity'),
		'qty_10000': fields.integer('10000', help='Ten Thousand Quantity'),
		'qty_20000': fields.integer('20000', help='Twenty Thousand Quantity'),
		'qty_50000': fields.integer('50000', help='Fifty Thousand Quantity'),
		'qty_100000': fields.integer('100000', help='A Hundred Thousand Quantity'),
		'amount_100': fields.integer('A Hundred Amount', help='A Hundred Amount'),
		'amount_200': fields.integer('Two Hundred Amount', help='Two Hundred Amount'),
		'amount_500': fields.integer('Five Hundred Amount', help='Five Hundred Amount'),
		'amount_1000': fields.integer('A Thousand Amount', help='A Thousand Amount'),
		'amount_2000': fields.integer('Two Thousand Amount', help='Two Thousand Amount'),
		'amount_5000': fields.integer('Five Thousand Amount', help='Five Thousand Amount'),
		'amount_10000': fields.integer('Ten Thousand Amount', help='Ten Thousand Amount'),
		'amount_20000': fields.integer('Twenty Thousand Amount', help='Twenty Thousand Amount'),
		'amount_50000': fields.integer('Fifty Thousand Amount', help='Fifty Thousand Amount'),
		'amount_100000': fields.integer('A Hundred Thousand Amount', help='A Hundred Thousand Amount'),
		'subtotal_cash': fields.float('Subtotal Cash'),
		
		'extra_desc_1': fields.char('Extra Desc 1'),
		'extra_amount_1': fields.integer('Extra Amount 1', help='Can be positive or negative'),
		'extra_desc_2': fields.char('Extra Desc 2'),
		'extra_amount_2': fields.integer('Extra Amount 2', help='Can be positive or negative'),
		'extra_desc_3': fields.char('Extra Desc 3'),
		'extra_amount_3': fields.integer('Extra Amount 3', help='Can be positive or negative'),
		
		'total_cash': fields.float('Total Cash'),
		'omzet_cash': fields.float('Omzet Cash (-)', help='Input in positive, but calculated as negative.'),
		'modal_cash': fields.float('Modal Cash (-)', help='Input in positive, but calculated as negative.'),
		
		'balance': fields.float('Balance'),
		'desc': fields.text('Description'),
	}
	
	_defaults = {
		'day_end_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'branch_id': _default_branch_id,
		'modal_cash': _default_modal_cash,
	}
	
	def create(self, cr, uid, vals, context=None):
		vals['branch_id'] = self._default_branch_id(cr, uid, context=context)
		
		account_account_obj = self.pool.get('account.account')
		kas_id = vals['kas_id']
		kas = account_account_obj.browse(cr, uid, kas_id, context=context)
		
		vals.update({
			'amend_number': self.calculate_amend_number(cr, uid, kas_id, vals['day_end_date'], context=context),
			'amount_100': vals['qty_100'] * 100,
			'amount_200': vals['qty_200'] * 200,
			'amount_500': vals['qty_500'] * 500,
			'amount_1000': vals['qty_1000'] * 1000,
			'amount_2000': vals['qty_2000'] * 2000,
			'amount_5000': vals['qty_5000'] * 5000,
			'amount_10000': vals['qty_10000'] * 10000,
			'amount_20000': vals['qty_20000'] * 20000,
			'amount_50000': vals['qty_50000'] * 50000,
			'amount_100000': vals['qty_100000'] * 100000,
		})
		vals['subtotal_cash'] = \
			vals['amount_100'] + vals['amount_200'] + vals['amount_500'] + \
			vals['amount_1000'] + vals['amount_2000'] + vals['amount_5000'] + \
			vals['amount_10000'] + vals['amount_20000'] + vals['amount_50000'] + vals['amount_100000']
		vals['omzet_cash'] = self.calculate_omzet_cash(cr, uid, kas, context=context)
		vals['modal_cash'] = self._default_modal_cash(cr, uid, context=context)
		vals['total_cash'] = vals['subtotal_cash'] + vals['extra_amount_1'] + vals['extra_amount_2'] + vals['extra_amount_3']
		vals['balance'] = vals['total_cash'] - vals['omzet_cash'] - vals['modal_cash']
		
		# update to kas if not balanced
		if vals['balance'] != 0:
			kas_id = vals['kas_id']
			journal_entry_obj = self.pool.get('account.move')
			now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
			name = 'DAY END ' + now,
			acount_from = self.pool.get('account.account').search(cr, uid, [('code', '=', '122000')], limit=1)[0]
			entry_data = journal_entry_obj.account_move_prepare(cr, uid, self.pool.get('account.journal').search(cr, uid, [('type', 'in', ['cash'])], limit=1)[0], date=vals.get('journal_date'), ref=name)
			entry_data['line_id'] = [
				[0, False, {
					'name': name,
					'account_id': vals['kas_id'],
					'debit': vals['balance'] if vals['balance'] > 0 else 0,
					'credit': -vals['balance'] if vals['balance'] < 0 else 0,
				}],
				[0, False, {
					'name': name,
					'account_id': acount_from,
					'debit': -vals['balance'] if vals['balance'] < 0 else 0,
					'credit': vals['balance'] if vals['balance'] > 0 else 0,
				}],
			]
			new_entry_id = journal_entry_obj.create(cr, uid, entry_data, context=context)
			journal_entry_obj.post(cr, uid, [new_entry_id], context=context)
		
		return super(tbvip_day_end, self).create(cr, uid, vals, context)
	
	def onchange_day_end_kas_date(self, cr, uid, ids, kas_id, day_end_date, context=None):
		return {
			'value': {
				'omzet_cash': self.calculate_omzet_cash(cr, uid, kas_id, context=context),
				'amend_number': self.calculate_amend_number(cr, uid, kas_id, day_end_date, context=context)
			}
		}
	
	def onchange_qty(self, cr, uid, ids, qty_100, qty_200, qty_500, qty_1000, qty_2000, qty_5000, qty_10000,
			qty_20000, qty_50000, qty_100000, context=None):
		result = {'value': {
			'amount_100': qty_100 * 100,
			'amount_200': qty_200 * 200,
			'amount_500': qty_500 * 500,
			'amount_1000': qty_1000 * 1000,
			'amount_2000': qty_2000 * 2000,
			'amount_5000': qty_5000 * 5000,
			'amount_10000': qty_10000 * 10000,
			'amount_20000': qty_20000 * 20000,
			'amount_50000': qty_50000 * 50000,
			'amount_100000': qty_100000 * 100000,
		}}
		result['value']['subtotal_cash'] = \
			result['value']['amount_100'] + result['value']['amount_200'] + \
			result['value']['amount_500'] + result['value']['amount_1000'] + \
			result['value']['amount_2000'] + result['value']['amount_5000'] + \
			result['value']['amount_10000'] + result['value']['amount_20000'] + \
			result['value']['amount_50000'] + result['value']['amount_100000']
		return result
	
	def onchange_cash(self, cr, uid, ids, subtotal_cash, extra_amount_1, extra_amount_2, extra_amount_3, context=None):
		return {'value': {
			'total_cash': subtotal_cash + extra_amount_1 + extra_amount_2 + extra_amount_3,
		}}
	
	def onchange_balance_cash(self, cr, uid, ids, total_cash, omzet_cash, modal_cash, context=None):
		return {'value': {
			'balance': total_cash - omzet_cash - modal_cash,
		}}


# ==========================================================================================================================

class account_account(osv.osv):
	_inherit = 'account.account'
	
	_columns = {
		'is_tbvip_kas': fields.boolean('Kas'),
	}
	

# ==========================================================================================================================
