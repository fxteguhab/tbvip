from openerp.osv import osv, fields


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
		if vals.get('order_line', False):
			for order_line in vals['order_line']:
				order_line[2]['commission_amount'] = self._calculate_commission_amount(cr, uid, order_line)
		return super(sale_order, self).create(cr, uid, vals, context)
	
	def write(self, cr, uid, ids, vals, context=None):
		if vals.get('order_line', False):
			for order_line in vals['order_line']:
				order_line[2]['commission_amount'] = self._calculate_commission_amount(cr, uid, order_line)
		return super(sale_order, self).write(cr, uid, ids, vals, context)
	
	def _calculate_commission_amount(self, cr, uid, order_line):
		commission_amount = 0
		product_uom_obj = self.pool.get('product.uom')
		product_obj = self.pool.get('product.product')
		
		product = product_obj.browse(cr, uid, order_line[2]['product_id'])
		qty = product_uom_obj._compute_qty(cr, uid,
			order_line[2]['product_uom'], order_line[2]['product_uom_qty'], product.product_tmpl_id.uom_po_id.id)
		price_unit_one_qty = order_line[2]['price_unit'] * 1.0 / qty
		
		
		
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