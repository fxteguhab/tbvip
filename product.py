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
	
	def _product_current_stock(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		quant_obj = self.pool.get('stock.quant')
		for product in self.browse(cr, uid, ids, context=context):
			stocks = ''
			for variant in product.product_variant_ids:
				map = {}
				quant_ids = quant_obj.search(cr, uid, [('product_id', '=', variant.id), ('location_id.usage', '=', 'internal')])
				for quant in quant_obj.browse(cr, uid, quant_ids):
					default_uom = quant.product_id.uom_id.name
					map[quant.location_id.display_name] = map.get(quant.location_id.display_name, 0) + quant.qty
				# stocks += variant.name + '\n'
				stock = ''
				for key in sorted(map.iterkeys()):
					stock += key + ': ' + str(map[key]) + ' ' + default_uom + '\n'
				if len(stock) == 0:
					stock = 'None'
				stocks += stock + '\n'
			result[product.id] = stocks
		return result
		
	def _current_price_ids(self, cr, uid, ids, field_name, arg, context={}):
		current_pricelist_obj = self.pool.get('product.current.price')
		result = {}
		for product in self.browse(cr, uid, ids):
			price = 0
			variants = product.product_variant_ids
			if len(variants) > 0:
				variant = variants[0]
				result[product.id] = current_pricelist_obj.search(cr, uid, [('product_id', '=', variant.id)], limit=1)
		return result
	
# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
		'purchase_order_line_ids': fields.function(_purchase_order_line_ids, method=True, type="one2many",
			string="Last Purchase", relation="purchase.order.line"),
		'is_sup_bonus' : fields.boolean('Is Supplier Bonus'),
		'commission': fields.char('Commission'),
		'product_sublocation_ids': fields.one2many('product.product.branch.sublocation', 'product_id', 'Sublocations'),
		'product_current_stock': fields.function(_product_current_stock, string="Current Stock", type='text', store=False),
		'current_price_ids': fields.function(_current_price_ids, string="Current Prices", type='one2many', relation='product.current.price'),
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
	}

# ==========================================================================================================================

class product_product_branch_sublocation(osv.osv):
	_name = 'product.product.branch.sublocation'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'product_id': fields.many2one('product.product', 'Product'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'sublocation_id': fields.many2one('stock.sublocation', 'Sublocation'),
	}

# ==========================================================================================================================

class product_uom(osv.osv):
	_inherit = 'product.uom'
	
	_defaults = {
		'category_id': lambda self, cr, uid, ctx:
			self.pool.get('ir.model.data').get_object_reference(cr, uid, 'product', 'product_uom_categ_unit')[1],
	}