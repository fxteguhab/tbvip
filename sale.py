from openerp.osv import osv, fields
import commission_utility
from openerp.tools.translate import _
from datetime import datetime, date, timedelta
import openerp.addons.decimal_precision as dp

# ==========================================================================================================================

class sale_order(osv.osv):
	_inherit = 'sale.order'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission_total': fields.float('Commission Total', readonly=True),
		'bon_number': fields.char('Bon Number'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		'is_cash': fields.boolean('Is Cash'),
		'is_transfer': fields.boolean('Is Transfer'),
		'is_edc': fields.boolean('Is EDC'),
		'cash_amount': fields.float('Cash Amount'),
		'transfer_amount': fields.float('Transfer Amount'),
		'edc_amount': fields.float('EDC Amount'),
		'edc_id': fields.many2one('account.journal.edc', 'EDC'),
		'approval_code': fields.char('Approval Code'),
		'card_fee': fields.float('Card Fee (%)'),
		'card_fee_amount': fields.float(type='float', string='Card Fee Amount', store=True, multi='sums'),
		'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
		'stock_location_id': fields.many2one('stock.location', 'Location'),
	}

	def _default_partner_id(self, cr, uid, context={}):
	# kalau penjualan cash, default customer adalah general customer
		partner_id = None
		if context.get('default_cash_or_receivable') == 'cash':
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
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		if vals.get('bon_number', False):
			self._update_bon_book(cr, uid, vals['bon_number'])
		new_id = super(sale_order, self).create(cr, uid, vals, context)
		self._calculate_commission_total(cr, uid, new_id)
		return new_id
	
	def write(self, cr, uid, ids, vals, context=None):
		if vals.get('bon_number', False):
			self._update_bon_book(cr, uid, vals['bon_number'])
		for sale_order_data in self.browse(cr, uid, ids):
			bon_number = vals['bon_number'] if vals['bon_number'] else sale_order_data.bon_number
			bon_name = ' / ' + bon_number if bon_number else ''
			name = '%s%s' % (datetime.strptime(sale_order_data.date_order, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d'), bon_name)
			vals['name'] = name
		result = super(sale_order, self).write(cr, uid, ids, vals, context)
		if vals.get('order_line', False):
			for sale_id in ids:
				self._calculate_commission_total(cr, uid, sale_id)
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
	
	def onchange_bon_number(self, cr, uid, ids, bon_number, context=None):
		if not bon_number:
			return
		result = {}
		bon_book_same_number_ids = self.search(cr, uid, [
			('bon_number', '=', bon_number),
			('date_order', '>=', date.today().strftime('%Y-%m-%d 00:00:00')),
			('date_order', '<=', date.today().strftime('%Y-%m-%d 23:59:59')),
		])
		if len(bon_book_same_number_ids) > 0:
			raise osv.except_orm(_('Bon book number error'),
				_('There is sale order with the same bon book number.'))
		bon_book_obj = self.pool.get('tbvip.bon.book')
		bon_book_id = bon_book_obj.search(cr, uid, [
			('start_from', '<=', int(bon_number)),
			('end_at', '>=', int(bon_number)),
		], limit=1, order='issue_date DESC')
		bon_book = bon_book_obj.browse(cr, uid, bon_book_id)
		if bon_book:
			if bon_book.total_used >= bon_book.total_sheets:
				raise osv.except_orm(_('Bon book is full'), _('All sheets in bon book have already been used.'))
			else:
				if bon_book.used_numbers:
					used_numbers = bon_book.used_numbers.split(', ')
					for used_number in used_numbers:
						if used_number == bon_number:
							raise osv.except_orm(_('Bon number error'), _('Bon number in the latest bon book has been used.'))
		
				employee_obj = self.pool.get('hr.employee')
				user_id = bon_book.user_id.id
				employee_id = employee_obj.search(cr, uid, [
					('user_id', '=', user_id),
				], limit=1)
				if employee_id:
					result['value'] = {}
					result['value'].update({
						'employee_id': employee_id[0]	,
					})
				else:
					raise osv.except_orm(_('Bon number error'), bon_book.user_id.name + ' ' + _('is not an employee.'))
		else:
			raise osv.except_orm(_('Creating sale order error'),
				_('There is no bon book with the given number.'))
		return result
	
	def _update_bon_book(self, cr, uid, bon_number):
		bon_book_same_number_ids = self.search(cr, uid, [
			('bon_number', '=', bon_number),
			('date_order', '>=', date.today().strftime('%Y-%m-%d 00:00:00')),
			('date_order', '<=', date.today().strftime('%Y-%m-%d 23:59:59')),
		])
		if len(bon_book_same_number_ids) > 0:
			raise osv.except_orm(_('Bon book number error'),
				_('There is sale order with the same bon book number.'))
		bon_book_obj = self.pool.get('tbvip.bon.book')
		bon_book_id = bon_book_obj.search(cr, uid, [
			('start_from', '<=', int(bon_number)),
			('end_at', '>=', int(bon_number)),
		], limit=1, order='issue_date DESC')
		bon_book = bon_book_obj.browse(cr, uid, bon_book_id)
		if bon_book:
			if bon_book.total_used >= bon_book.total_sheets:
				raise osv.except_orm(_('Bon book is full'), _('All sheets in bon book have already been used.'))
			else:
				used_numbers = []
				if bon_book.used_numbers:
					used_numbers = bon_book.used_numbers.split(', ')
					for used_number in used_numbers:
						if used_number == bon_number:
							raise osv.except_orm(_('Bon number error'), _('Bon number in the latest bon book has been used.'))
				bon_book_obj.write(cr, uid, bon_book.id, {
					'total_used': bon_book.total_used + 1,
					'used_numbers': (bon_book.used_numbers + ', ' + bon_number) if (len(used_numbers)>=1) else bon_number,
				})
		else:
			raise osv.except_orm(_('Creating sale order error'),
				_('There is no bon book with the given number.'))

# ==========================================================================================================================

class sale_order_line(osv.osv):
	_inherit = 'sale.order.line'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Decimal Custom Order Line'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
		'commission': fields.char('Commission', help="Commission String"),
		'commission_amount': fields.float('Commission Amount'),
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		product_obj = self.pool.get('product.current.commission')
		current_commission = product_obj.get_current_commission(cr, uid, vals['product_id'])
		vals['commission'] = current_commission
		vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, None)
		return super(sale_order_line, self).create(cr, uid, vals, context)
	
	def write(self, cr, uid, ids, vals, context=None):
		for id in ids:
			vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, id)
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
			
		if order_line.get('product_id', False):
			product_id = order_line['product_id']
		if order_line.get('product_uom', False):
			product_uom = order_line['product_uom']
		if order_line.get('product_uom_qty', False):
			product_uom_qty = order_line['product_uom_qty']
		if order_line.get('price_unit', False):
			price_unit = order_line['price_unit']
		
		commission = commission_obj.get_current_commission(cr, uid, product_id)
			
		product = product_obj.browse(cr, uid, product_id)
		qty = product_uom_obj._compute_qty(cr, uid,
			product_uom, product_uom_qty, product.product_tmpl_id.uom_po_id.id)
	
		price_unit = price_unit / qty * product_uom_qty
		try:
			valid_commission_string = commission_utility.validate_commission_string(commission)
			commission_amount = commission_utility.calculate_commission(valid_commission_string, price_unit, qty)
		except commission_utility.InvalidCommissionException:
			return False
		return commission_amount
	
	def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
		result = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name,
			partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, context)
		product_obj = self.pool.get('product.current.commission')
		current_commission = product_obj.get_current_commission(cr, uid, product)
		result['value']['commission'] = current_commission
		return result
	
	def onchange_product_uom_qty(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, price_unit = False,context=None):
		result = super(sale_order_line, self).product_id_change_with_wh(
			cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id,
			lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id, context=None)
		result['value'].update({
			'price_unit': price_unit,
			'product_uom': uom,
		})
		return result
	
	def onchange_product_id_price_list(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,
			warehouse_id=False, parent_price_type_id=False, price_type_id=False, context=None):
		product_conversion_obj = self.pool.get('product.conversion')
		uom = product_conversion_obj.get_uom_from_auto_uom(cr, uid, uom, context).id
		result = super(sale_order_line, self).onchange_product_id_price_list(cr, uid, ids, pricelist, product, qty,
			uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag,
			warehouse_id, parent_price_type_id, price_type_id, context)
		temp = super(sale_order_line, self).onchange_product_uom(
			cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name, partner_id,
			lang, update_tax, date_order, fiscal_position, context=None)
		if result.get('domain', False) and temp.get('domain', False):
			result['domain']['product_uom'] = result['domain']['product_uom'] + temp['domain']['product_uom']
		result['value'].update({
			'product_uom': self.pool.get('product.product').browse(cr, uid, product).uom_id.id
		})
		
		return result