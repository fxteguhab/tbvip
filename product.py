from openerp import api
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
					map[quant.location_id.name] = map.get(quant.location_id.name, 0) + quant.qty
					#map[quant.location_id.display_name] = map.get(quant.location_id.display_name, 0) + quant.qty
				# stocks += variant.name + '\n'
				stock = ''
				for key in sorted(map.iterkeys()):
					stock += key + ': ' + str(map[key]) + ' ' + default_uom + '\n'
				if len(stock) == 0:
					stock = 'Stock : 0'
				stocks += stock + '\n'
			result[product.id] = stocks
		return result
		
	#TEGUH@20180414 : _product_commission output text
	def _product_commission(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		current_commission_obj = self.pool.get('product.current.commission')
		for product in self.browse(cr, uid, ids):
			commissions = ''
			for variant in product.product_variant_ids:
				commission = current_commission_obj.get_current_commission(cr, uid, variant.id,context)
				#if len(commission) == 0:
				#	commission = '0'
				commissions += str(commission)
			result[product.id] = commissions

		'''
		for product in self.browse(cr, uid, ids):
			commissions = ''
			for variant in product.product_variant_ids:
				map = {}
				commission_ids = current_commission_obj.search(cr, uid, [('product_id', '=', variant.id)])
				for commission_id in current_commission_obj.browse(cr, uid, commission_ids):
					map[commission_id.product_id] = map.get(commission_id.product_id, 0) + commission_id.commission
				
				commission = ''
				for key in sorted(map.iterkeys()):
					commission += key + ': ' + str("{:,.0f}".format(map[key])) + '\n'
					#price += key + ': ' + str(map[key]) + '\n'
				if len(commission) == 0:
					commission = '0'
				commissions += commission + '\n'
			result[product.id] = commissions
		'''
		return result
		
	def _invoice_count(self, cr, uid, ids, field_name, arg, context=None):
		res = dict.fromkeys(ids, 0)
		for template in self.browse(cr, uid, ids, context=context):
			res[template.id] = sum([p.invoice_count for p in template.product_variant_ids])
		return res

	
	def action_view_invoices(self, cr, uid, ids, context=None):
		products = self._get_products(cr, uid, ids, context=context)
		result = self._get_act_window_dict(cr, uid, 'tbvip.action_invoice_line_product_tree', context=context)
		#result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "]),('account_id','=','220000 Expenses')]" #TEGUH@20180729 : terpaksa hardcode , ga tau cara ambil nya scr logic :D
		result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "]),('partner_id.supplier','=','True')]" #TEGUH@20180729 : terpaksa hardcode , ga tau cara ambil nya scr logic :D
		return result
	

	def _stock_opname_count(self, cr, uid, ids, field_name, arg, context=None):
		res = dict.fromkeys(ids, 0)
		for template in self.browse(cr, uid, ids, context=context):
			res[template.id] = sum([p.stock_opname_count for p in template.product_variant_ids])
		return res

	def action_view_stock_opname(self, cr, uid, ids, context=None):
		products = self._get_products(cr, uid, ids, context=context)
		result = self._get_act_window_dict(cr, uid, 'tbvip.action_stock_opname_product_tree', context=context)
		result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
		return result

	def _get_last_sale(self, cr, uid, ids, name, args, context=None):
		result = {}
		last_sale = ''
		for id in ids:
			cr.execute("""
			SELECT DISTINCT ON (sl.name)
			sl.name, so_line.write_date, hr.name_related
			FROM sale_order_line so_line
			LEFT JOIN hr_employee hr ON hr.id = so_line.salesman_id
			LEFT JOIN stock_location sl ON sl.id = so_line.stock_location_id
			LEFT JOIN product_product pp ON pp.product_tmpl_id = %d
			WHERE so_line.product_id = pp.id
			ORDER BY sl.name,so_line.write_date DESC
			""" % id)
			for row in cr.dictfetchall():
				last_sale = last_sale +'\n' +str(row['name'])+' || '+str(row['write_date'])+' || '+str(row['name_related'])
			result[id] =last_sale
		
		return result
			
	def _get_last_sale_delta(self, cr, uid, ids, name, args, context=None):
		result = {}
		fmt = '%Y-%m-%d %H:%M:%S'
		now = datetime.today().strftime(fmt)
		

		for id in ids:
			last_sale = str(self.browse(cr,uid,id,context=context).create_date)
			sale = False
			cr.execute("""
			SELECT DISTINCT ON (sl.name)
			sl.name, so_line.write_date, hr.name_related
			FROM sale_order_line so_line
			LEFT JOIN hr_employee hr ON hr.id = so_line.salesman_id
			LEFT JOIN stock_location sl ON sl.id = so_line.stock_location_id
			LEFT JOIN product_product pp ON pp.product_tmpl_id = %d
			WHERE so_line.product_id = pp.id
			ORDER BY sl.name,so_line.write_date DESC
			""" % id)
			for row in cr.dictfetchall():
				last_sale =  str(row['write_date'])

			last_sale_date =  datetime.strptime(last_sale.split("+")[0].split(".")[0],fmt)
			delta = (datetime.today() - last_sale_date).days
			result[id] =delta
			
		return result

	@api.multi
	@api.depends('qty_available','min_qty')
	def _get_is_stock_exhausted(self):		
		for product in self:
			product.is_stock_exhausted = product.qty_available < product.min_qty

	@api.multi
	@api.depends('qty_available','max_qty')
	def _get_is_stock_overstock(self):
		result = {}
		for product in self:
			product.is_stock_overstock = product.qty_available > product.max_qty

# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
		'purchase_order_line_ids': fields.function(_purchase_order_line_ids, method=True, type="one2many",
			string="Last Purchase", relation="purchase.order.line"),
		'is_sup_bonus' : fields.boolean('Is Supplier Bonus'),
		#TEGUH@20180414 : ganti jenis field commision
		'commission': fields.function(_product_commission, string="Commission", type='text', store=False),
		#'commission': fields.char('Commission'),
		'product_sublocation_ids': fields.one2many('product.product.branch.sublocation', 'product_id', 'Sublocations'),
		'product_current_stock': fields.function(_product_current_stock, string="Current Stock", type='text', store=False),
		#TEGUH@20180411 : current_price_ids_text output
		'brand_id': fields.many2one('product.brand', 'Brand'),
		'tonnage': fields.float('Tonnage/Weight (kg)'),
		'stock_unit_id': fields.many2one('stock.unit', 'Stock Unit'),
		'invoice_count': fields.function(_invoice_count, string='# Invoices', type='integer'),
		'stock_opname_count': fields.function(_stock_opname_count, string='# Stock Opname', type='integer'),
		'last_sale': fields.function(_get_last_sale, string="Last Sale", type='text', readonly=True, store=False),
		'last_sale_delta': fields.function(_get_last_sale_delta, string="Last Sale Delta", type='float', readonly=True),
		'latest_inventory_adjustment_date': fields.datetime('Latest Inventory Adjustment Date', readonly=True),
		'latest_inventory_adjustment_employee_id': fields.many2one('hr.employee', 'Latest Inventory Adjustment Employee', readonly=True),
		'min_qty': fields.float("Min Qty", group_operator="avg"),
		'max_qty': fields.float("Max Qty", group_operator="avg"),
		'is_stock_exhausted' : fields.boolean(compute = '_get_is_stock_exhausted', string="Stock Exhausted", store=True),
		'is_stock_overstock' : fields.boolean(compute = '_get_is_stock_overstock', string="Over Stock", store=True),
	}

	_sql_constraints = [
		('name_uniq', 'unique(name)', 'This product already created'),
	]

	
# DEFAULTS ----------------------------------------------------------------------------------------------------------------------
	_defaults = {
		'is_sup_bonus': False,
		'type': 'product',
		'sale_delay' : 0,
		'last_sale_delta' : 0,
		'min_qty' : 0,
		'max_qty' : 1,
		#'commission' : '0',
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
	
	#TEGUH@20180817 : buat ganti list_price/standard_price di product_Template
	def _set_price(self,cr,uid,product_id,price_unit_nett,field):
			self.write(cr, uid, [product_id], {
				field: price_unit_nett,
			})	

	def cron_product_rank(self, cr, uid, context={}):
		sale_order_obj = self.pool.get('sale.order')
		config_param_obj = self.pool.get('ir.config_parameter')
		
		# date
		today = datetime.now() 
		#today = datetime.now() + timedelta(hours = 7)
		purchase_needs_latest_sale_days = int(config_param_obj.get_param(cr, uid, 'product_rank_days', '30'))
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

	def _invoice_count(self, cr, uid, ids, field_name, arg, context=None):
		Invoice = self.pool['account.invoice']
		return {
			#product_id: Invoice.search_count(cr,uid, [('invoice_line.product_id', '=', product_id),('invoice_line.account_id','=','220000 Expenses')], context=context)  #TEGUH@20180729 : terpaksa hardcode , ga tau cara ambil nya scr logic :D
			product_id: Invoice.search_count(cr,uid, [('invoice_line.product_id', '=', product_id),('invoice_line.partner_id.supplier','=','True')], context=context)  #TEGUH@20180729 : terpaksa hardcode , ga tau cara ambil nya scr logic :D
			for product_id in ids
		}

	def action_view_invoices(self, cr, uid, ids, context=None):
		if isinstance(ids, (int, long)):
			ids = [ids]
		result = self.pool['product.template']._get_act_window_dict(cr, uid, 'tbvip.action_invoice_line_product_tree', context=context)
		#result['domain'] = "[('product_id','in',[" + ','.join(map(str, ids)) + "]),('account_id','=','220000 Expenses')]" #TEGUH@20180729 : terpaksa hardcode , ga tau cara ambil nya scr logic :D
		result['domain'] = "[('product_id','in',[" + ','.join(map(str, ids)) + "]),('invoice_line.partner_id.supplier','=','True')]" #TEGUH@20180729 : terpaksa hardcode , ga tau cara ambil nya scr logic :D
		return result
	
	def _stock_opname_count(self, cr, uid, ids, field_name, arg, context=None):
		Invoice = self.pool['stock.inventory']
		return {
			product_id: Invoice.search_count(cr,uid, [('line_ids.product_id', '=', product_id)], context=context) 
			for product_id in ids
		}

	def action_view_stock_opname(self, cr, uid, ids, context=None):
		if isinstance(ids, (int, long)):
			ids = [ids]
		result = self.pool['product.template']._get_act_window_dict(cr, uid, 'tbvip.action_stock_opname_product_tree', context=context)
		result['domain'] = "[('product_id','in',[" + ','.join(map(str, ids)) + "])]"
		return result
	# COLUMNS ------------------------------------------------------------------------------------------------------------------

	_columns = {
		'variant_codex_id': fields.integer('MySQL Variant Product ID'),
		'rank': fields.integer('Rank'),
		'invoice_count': fields.function(_invoice_count, string='# Invoices', type='integer'),
		'stock_opname_count': fields.function(_stock_opname_count, string='# Stock Opname', type='integer'),
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

class ProductSupplierinfo(osv.osv):
	_inherit = 'product.supplierinfo'

	_columns = {
			'rank' : fields.integer(related = "product_tmpl_id.product_variant_ids.rank", string ="Rank", store= True),
			'product_current_stock' : fields.text(related = "product_tmpl_id.product_current_stock", string ="Stock", store= True),
			#'sales_count' : fields.integer(related = "product_tmpl_id.product_current_stock", string ="Stock", store= True),
		}

#class make_procurement(osv.osv_memory):
#	_inherit = 'make.procurement'
#
#	def make_procurement(self, cr, uid, ids, context=None):