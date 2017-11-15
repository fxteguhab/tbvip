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

# ==========================================================================================================================

class tbvip_day_end(osv.osv):
	_name = 'tbvip.day.end'
	_description = 'Ending Day'
	
	def calculate_omzet_cash(self, cr, uid, day_end_date, context={}):
		# day_end_date's sale orders
		sale_order_obj = self.pool.get('sale.order')
		day_end_date_datetime = datetime.strptime(day_end_date, '%Y-%m-%d %H:%M:%S')
		sale_order_done_ids = sale_order_obj.search(cr, uid, [
			('state', 'in', ['done','progress']),
			('date_order', '>=', day_end_date_datetime.strftime("%Y-%m-%d 00:00:00")),
			('date_order', '<', (day_end_date_datetime + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")),
		], context=context)
		omzet_cash_total = 0
		for sale_order in sale_order_obj.browse(cr, uid, sale_order_done_ids, context=context):
			omzet_cash_total += sale_order.payment_cash_amount
		return omzet_cash_total
	
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
		'day_end_date': datetime.now(),
		'branch_id': _default_branch_id,
		'modal_cash': _default_modal_cash
	}
	
	def create(self, cr, uid, vals, context=None):
		vals['branch_id'] = self._default_branch_id(cr, uid, context=context)
		day_end_date = vals['day_end_date']
		day_end_date_datetime = datetime.strptime(day_end_date, '%Y-%m-%d %H:%M:%S')
		day_end_ids = self.search(cr, uid, [
			('branch_id', '=', vals['branch_id']),
			('day_end_date', '>=', day_end_date_datetime.strftime("%Y-%m-%d 00:00:00")),
			('day_end_date', '<', (day_end_date_datetime + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")),
		], context=context)
		vals.update({
			'amend_number': len(day_end_ids),
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
		vals['omzet_cash'] = self.calculate_omzet_cash(cr, uid, day_end_date, context=context)
		vals['modal_cash'] = self._default_modal_cash(cr, uid, context=context)
		vals['total_cash'] = vals['subtotal_cash'] + vals['extra_amount_1'] + vals['extra_amount_2'] + vals['extra_amount_3']
		vals['balance'] = vals['total_cash'] - vals['omzet_cash'] - vals['modal_cash']
		return super(tbvip_day_end, self).create(cr, uid, vals, context)
	
	def onchange_day_end_date(self, cr, uid, ids, day_end_date, context=None):
		return {
			'value': {
				'omzet_cash': self.calculate_omzet_cash(cr, uid, day_end_date, context=context)
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
