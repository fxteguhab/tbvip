from openerp.osv import osv, fields
import commission_utility
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

# ==========================================================================================================================

class sale_order(osv.osv):
	_inherit = 'sale.order'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission_total': fields.float('Commission Total', readonly=True),
		'bon_number': fields.char('Bon Number'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		'is_cash': fields.boolean('Is Cash'),
		'cash_amount': fields.float('Cash Amount'),
		# 'is_edc': fields.boolean('Is EDC'),
		'is_transfer': fields.boolean('Is Transfer'),
		'transfer_amount': fields.float('Transfer Amount'),
		'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
		'stock_location_id': fields.many2one('stock.location', 'Location'),
	}
	
	def name_get(self, cr, uid, ids, context={}):
		if isinstance(ids, (list, tuple)) and not len(ids): return []
		if isinstance(ids, (long, int)): ids = [ids]
		res = []
		for record in self.browse(cr, uid, ids):
			name = record.name
			if record.date_order:
				bon_name = ' ' + record.bon_number if record.bon_number else ''
				name = '%s%s' % (datetime.strptime(record.date_order, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d'), bon_name)
			res.append((record.id, name))
		return res

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
		
	def _update_bon_book(self, cr, uid, bon_number):
		bon_book_same_number_ids = self.search(cr, uid, [
			('user_id', '=', uid),
			('bon_number', '=', bon_number),
			('date_order', '>=', date.today().strftime('%Y-%m-%d 00:00:00')),
			('date_order', '<=', date.today().strftime('%Y-%m-%d 23:59:59')),
		])
		if len(bon_book_same_number_ids) > 0:
			raise osv.except_orm(_('Bon book number error'),
				_('There is sale order with the same bon book number for this user.'))
		bon_book_obj = self.pool.get('tbvip.bon.book')
		bon_book_id = bon_book_obj.search(cr, uid, [
			('user_id', '=', uid),
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
				_('There is no bon book with the given number for this user.'))

# ==========================================================================================================================

class sale_order_line(osv.osv):
	_inherit = 'sale.order.line'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission': fields.char('Commission', help="Commission String"),
		'commission_amount': fields.float('Commission Amount'),
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		if vals.get('commission', False):
			vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, None)
		else:
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
			commission = sale_order_line.commission
		
		if order_line.get('product_id', False):
			product_id = order_line['product_id']
		if order_line.get('product_uom', False):
			product_uom = order_line['product_uom']
		if order_line.get('product_uom_qty', False):
			product_uom_qty = order_line['product_uom_qty']
		if order_line.get('price_unit', False):
			price_unit = order_line['price_unit']
		if order_line.get('commission', False):
			commission = order_line['commission']
			
		if not commission:
			commission = commission_obj.get_current_commission(cr, uid, product_id)
	
		price_subtotal = price_unit * product_uom_qty
		try:
			valid_commission_string = commission_utility.validate_commission_string(commission)
			commission_amount = commission_utility.calculate_commission(valid_commission_string, price_subtotal)
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
			'product_uom' : temp['value']['product_uom']
		})
		
		return result