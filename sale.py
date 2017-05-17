from openerp.osv import osv, fields
import commission_utility

# ==========================================================================================================================

class sale_order(osv.osv):
	_inherit = 'sale.order'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission_total': fields.float('Commission Total'),
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		if vals.get('order_line', False):
			vals['commission_total'] = self._calculate_commission_total(cr, uid, vals['order_line'])
		return super(sale_order, self).create(cr, uid, vals, context)
	
	def write(self, cr, uid, ids, vals, context=None):
		if vals.get('order_line', False):
			vals['commission_total'] = self._calculate_commission_total(cr, uid, vals['order_line'])
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