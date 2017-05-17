from openerp.osv import osv, fields


# ==========================================================================================================================

class product_category(osv.osv):
	_inherit = 'product.category'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
	}


# ORDER --------------------------------------------------------------------------------------------------------------------

# _order = 'parent_id, codex_id'

# ==========================================================================================================================

class product_template(osv.osv):
	_inherit = 'product.template'
	
# FIELD FUNCTION METHODS ------------------------------------------------------------------------------------------------
	
	def _purchase_order_line_ids(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for data in self.browse(cr, uid, ids):
			order_line_obj = self.pool.get('purchase.order.line')
			order_line_ids = order_line_obj.search(cr, uid, [('product_id', '=', data.id)])
			supplier_ids = []
			unique_supplier_order_line_ids = []
			order_lines = order_line_obj.browse(cr, uid, order_line_ids)
			order_lines = order_lines.sorted(key=lambda r: r.date_order, reverse=True)
			for order_line in order_lines:
				if order_line.partner_id.id not in supplier_ids:
					supplier_ids.append(order_line.partner_id.id)
					unique_supplier_order_line_ids.append(order_line.id)
			result[data.id] = unique_supplier_order_line_ids
		return result
	
# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
		'purchase_order_line_ids': fields.function(_purchase_order_line_ids, method=True, type="one2many",
			string="Last Purchase", relation="purchase.order.line"),
		'is_sup_bonus' : fields.boolean('Is Supplier Bonus'),
	}
	
# DEFAULTS ----------------------------------------------------------------------------------------------------------------------
	_defaults = {
		'is_sup_bonus': False,
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	def create(self, cr, uid, vals, context={}):
		new_id = super(product_template, self).create(cr, uid, vals, context)
		# waktu create product baru, samakan variant_codex_id anak-anaknya dengan codex_id parent
		new_data = self.browse(cr, uid, new_id, context=context)
		product_obj = self.pool.get('product.product')
		for variant in new_data.product_variant_ids:
			product_obj.write(cr, uid, [variant.id], {
				'variant_codex_id': new_data.codex_id,
			})
		return new_id
	




# ==========================================================================================================================

class product_product(osv.osv):
	_inherit = 'product.product'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'variant_codex_id': fields.integer('MySQL Variant Product ID'),
		'commission': fields.char('Commission', help="Discount string."),
	}
