from openerp.osv import osv, fields
import commission_utility
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

# ==========================================================================================================================

class sale_order(osv.osv):
	_inherit = 'sale.order'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission_total': fields.float('Commission Total'),
		'bon_number': fields.char('Bon Number'),
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		if vals.get('order_line', False):
			vals['commission_total'] = self._calculate_commission_total(cr, uid, vals['order_line'])
		if vals.get('bon_number', False):
			self._update_bon_book(cr, uid, vals['bon_number'])
		return super(sale_order, self).create(cr, uid, vals, context)
	
	def write(self, cr, uid, ids, vals, context=None):
		if vals.get('order_line', False):
			vals['commission_total'] = self._calculate_commission_total(cr, uid, vals['order_line'])
		if vals.get('bon_number', False):
			self._update_bon_book(cr, uid, vals['bon_number'])
		return super(sale_order, self).write(cr, uid, ids, vals, context)
	
	def _calculate_commission_total(self, cr, uid, order_lines):
		commission_total = 0
		product_uom_obj = self.pool.get('product.uom')
		product_obj = self.pool.get('product.product')
		for order_line in order_lines:
			if order_line[2].get('product_uom_qty', False) and order_line[2].get('commission_amount', False):
				product = product_obj.browse(cr, uid, order_line[2]['product_id'])
				qty = product_uom_obj._compute_qty(cr, uid,
					order_line[2]['product_uom'], order_line[2]['product_uom_qty'], product.product_tmpl_id.uom_po_id.id)
				commission_total += (qty * order_line[2]['commission_amount'])
		return commission_total
		
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
					used_numbers = bon_book.used_numbers.split(',')
					for used_number in used_numbers:
						if used_number == vals['bon_number']:
							raise osv.except_orm(_('Bon number error'), _('Bon number in the latest bon book has been used.'))
				bon_book_obj.write(cr, uid, bon_book.id, {
					'total_used': bon_book.total_used + 1,
					'used_numbers': (bon_book.used_numbers + ',' + bon_number)
					if (len(used_numbers)>1) else bon_number
				})
		else:
			raise osv.except_orm(_('Creating sale order error'),
				_('There is no bon book with the given number for this user.'))

# ==========================================================================================================================

class sale_order_line(osv.osv):
	_inherit = 'sale.order.line'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission': fields.char('Commission', help="Discount string."),
		'commission_amount': fields.float('Commission Amount'),
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		if vals.get('commission', False):
			vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, None)
		return super(sale_order_line, self).create(cr, uid, vals, context)
	
	def write(self, cr, uid, ids, vals, context=None):
		for id in ids:
			if vals.get('commission', False):
				vals['commission_amount'] = self._calculate_commission_amount(cr, uid, vals, id)
		return super(sale_order_line, self).write(cr, uid, ids, vals, context)
	
	def _calculate_commission_amount(self, cr, uid, order_line, sale_order_line_id):
		product_uom_obj = self.pool.get('product.uom')
		product_obj = self.pool.get('product.product')
		
		commission = order_line['commission']
		if sale_order_line_id:
			sale_order_line = self.browse(cr, uid, sale_order_line_id)
			product_id = sale_order_line['product_id'].id
			product_uom = sale_order_line['product_uom'].id
			product_uom_qty = sale_order_line['product_uom_qty']
			price_unit = sale_order_line['price_unit']
		else:
			product_id = order_line['product_id']
			product_uom = order_line['product_uom']
			product_uom_qty = order_line['product_uom_qty']
			price_unit = order_line['price_unit']
		
		product = product_obj.browse(cr, uid, product_id)
		qty = product_uom_obj._compute_qty(cr, uid,
			product_uom, product_uom_qty, product.product_tmpl_id.uom_po_id.id)
		price_unit_one_qty = price_unit * 1.0 / qty
		try:
			valid_commission_string = \
				commission_utility.validate_commission_string(commission, price_unit_one_qty)
			commission_amount = commission_utility.calculate_commission(valid_commission_string, price_unit_one_qty)
		except commission_utility.InvalidCommissionException:
			return False
		return commission_amount
	
	def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
		result = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, qty_uos, uos, name,
			partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, context)
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product)
		result['value']['commission'] = product.commission
		return result