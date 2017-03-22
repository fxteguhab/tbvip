from openerp.osv import osv, fields


class purchase_needs(osv.Model):
	_inherit = 'purchase.needs'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
	}
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def _pool_generate_po_vals(self, cr, uid, context, need):
		"""
		Override _pool_generate_po_vals to add discount on generated PO
		"""
		po_vals = super(purchase_needs, self)._pool_generate_po_vals(cr, uid, context, need)
		# Get default product discount for each product on need line then append it on vals
		partner_id = po_vals['partner_id']
		for order_line in po_vals['order_line']:
			discount = False
			supplier_ids = self.pool.get('product.product') \
				.browse(cr, uid, order_line[2]['product_id']).seller_ids
			# Search if this need supplier is this product's supplier, if yes then update the default discount
			for supplier_id in supplier_ids:
				if supplier_id.name.id == partner_id:
					discount = supplier_id.default_discount
			order_line[2].update({'discount_string': discount})
		po_vals['branch_id'] = need.branch_id.id
		return po_vals
	
	def _calculate_discount(self, discount_string, price):
		result = [0, 0, 0, 0, 0]
		discounts = discount_string.split("+")
		counter = 0
		for discount in discounts:
			value = 0
			if discount[-1:] == "%":
				value = (price * (float(discount[:-1]))) / 100.00
				price -= value
			else:
				value = float(discount)
				price -= value
			result[counter] = value
			counter += 1
		return result
