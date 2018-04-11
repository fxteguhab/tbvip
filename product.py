from openerp.osv import osv, fields
from datetime import datetime, timedelta

# ==========================================================================================================================

class product_category(osv.osv):
	_inherit = 'product.category'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
		'brand_id': fields.many2one('product.brand', 'Brand'),
		'tonnage': fields.float('Tonnage/Weight (kg)'),
		'stock_unit_id': fields.many2one('stock.unit', 'Stock Unit'),
	}
	
	def write(self, cr, uid, ids, data, context=None):
		result = super(product_category, self).write(cr, uid, ids, data, context)
		for category_id in ids:
			product_obj = self.pool.get('product.template')
			product_ids = product_obj.search(cr, uid, [
				('categ_id', '=', category_id),
			])
			if data.get('brand_id', False):
				product_obj.write(cr, uid, product_ids, {
					'brand_id': data['brand_id'],
				})
			if data.get('tonnage', False):
				product_obj.write(cr, uid, product_ids, {
					'tonnage': data['tonnage'],
				})
			if data.get('stock_unit_id', False):
				product_obj.write(cr, uid, product_ids, {
					'stock_unit_id': data['stock_unit_id'],
				})
		return result

# ==========================================================================================================================

class product_brand(osv.osv):
	
	_name = "product.brand"
	
# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'name': fields.char('Name'),
	}

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
			variants = product.product_variant_ids
			if len(variants) > 0:
				variant = variants[0]
				result[product.id] = current_pricelist_obj.search(cr, uid, [('product_id', '=', variant.id), ('price_type_id.type','=', 'sell')])
		return result
	
	#TEGUH@20180411 : _product_current_price output text
	def _product_current_price(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		current_pricelist_obj = self.pool.get('product.current.price')
		for product in self.browse(cr, uid, ids):
			prices = ''
			for variant in product.product_variant_ids:
				map = {}
				price_ids = current_pricelist_obj.search(cr, uid, [('product_id', '=', variant.id), ('price_type_id.type','=', 'sell')])
				for price_id in current_pricelist_obj.browse(cr, uid, price_ids):
					map[price_id.price_type_id.name] = map.get(price_id.price_type_id.name, 0) + price_id.price_1
				
				price = ''
				for key in sorted(map.iterkeys()):
					price += key + ': ' + str("{:,.0f}".format(map[key])) + '\n'
					#price += key + ': ' + str(map[key]) + '\n'
				if len(price) == 0:
					stock = '0'
				prices += price + '\n'
			result[product.id] = prices

		return result


	def set_commission(self,cr,uid,ids, value):
		"""
		product_obj = self.pool.get('product.template')
		product_id = product_obj.search(cr, uid, [('id', '=', ids)])
		for product in product_obj.browse(cr, uid, product_id):
			product.commission = value
		"""
		vals = {}
		metel_id = self.pool.get('product.template').search(cr, uid, [('id', '=', ids)])
		if metel_id:
			vals.update({'commission':value})  
		return 0
		

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
		#TEGUH@20180411 : current_price_ids_text output
		'product_current_price': fields.function(_product_current_price, string="Current Price", type='text', store=False),
		'brand_id': fields.many2one('product.brand', 'Brand'),
		'tonnage': fields.float('Tonnage/Weight (kg)'),
		'stock_unit_id': fields.many2one('stock.unit', 'Stock Unit'),
	}
	
# DEFAULTS ----------------------------------------------------------------------------------------------------------------------
	_defaults = {
		'is_sup_bonus': False,
		'type': 'product',
		'commission' : '0',
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
		'rank': fields.integer('Rank'),
	}
	
	def cron_product_rank(self, cr, uid, context={}):
		sale_order_obj = self.pool.get('sale.order')
		config_param_obj = self.pool.get('ir.config_parameter')
		
		# date
		today = datetime.now()
		purchase_needs_latest_sale_days = int(config_param_obj.get_param(cr, uid, 'purchase_needs_latest_sale', '0'))
		last_sale_date = today + timedelta(days=-purchase_needs_latest_sale_days)
		
		# product sales
		product_array = []
		all_product_ids = self.search(cr, uid, [], context=context)
		for product_id in all_product_ids:
			product_sale_order_ids = sale_order_obj.search(cr, uid, [
				('product_id', '=', product_id),
				('state', '=', 'done'),
				('date_order', '>=', last_sale_date.strftime("%Y-%m-%d 00:00:00")),
				('date_order', '<=', today.strftime("%Y-%m-%d %H:%M:%S")),
			], context=context)
			product_sales_count = len(product_sale_order_ids) if product_sale_order_ids else 0
			product_array.append({
				'product_id': product_id,
				'sales': product_sales_count,
			})
			
		# ranking
		product_array_sorted = sorted(product_array, key=lambda r: r['sales'], reverse=True)
		rank = 1
		for product in product_array_sorted:
			self.write(cr, uid, product['product_id'], {
				'rank': rank,
			}, context=context)
			rank += 1
		return True

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