from datetime import datetime, timedelta

from openerp.osv import osv, fields
from openerp.tools.translate import _
import math

from dateutil.relativedelta import relativedelta

class sale_history(osv.Model):
	_inherit = 'sale.history'
	
# COLUMNS -------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
# OVERRIDES -----------------------------------------------------------------------------------------------------------------
	
	def count_uom_qty(self,cr, uid, product_id, qty, uom_id, context={}):
		"""
		Override function untuk menghitung qty, karena di tbvip terdapat modul product_custom_conversion. Dengan demikian gunakan
		function dari modul product_custom_conversion untuk menghitung uom qty
		"""
		product_conversion_obj = self.pool.get('product.conversion')
		uom_record = product_conversion_obj.get_conversion_auto_uom(cr, uid, product_id, uom_id)
		return super(sale_history, self).count_uom_qty(cr, uid, product_id, qty, uom_record.id, context=context)
		
	def cron_calculate_product_qty_sold(self, cr, uid, context={}):
		"""
		Function ini dioverride dengan mengcopas aslinya. Alasan tidak dapat dengan cara override manggil super() dan nambahin
		dapat dilihat di comment bawah dengan text prefix 'REASON'
		"""
		sale_order_obj = self.pool.get('sale.order')
		now = datetime.now()
		# Cari penjualan untuk bulan ini
		start_date = (now + relativedelta(months=-1)).strftime('%Y-%m-%d 00:00:00')
		end_date = now.strftime("%Y-%m-1 00:00:00")
		sale_ids =  sale_order_obj.search(cr, uid, [('date_order', '>=', start_date),
			('date_order', '<', end_date),
			('state', '=', 'done')])
		
		# Di titik ini kita juga harus ganti dictionary yang asalnya {'product_id': qty} menjadi {'product_id' : {branch_id: {qty:x}}}
		# Karena itu override juga function create_dict_for_sale_history
		dict_product_sale = self.create_dict_for_sale_history(cr, uid, sale_ids, context)
		
		# REASON, di titik ini harus dimasukkan branchnya. Di titik ini create sale history, jika menggunakan cara manggil super(),
		# kita tidak tahu sale_history mana yang harus dimasukkan branch_id sesuai dengan branch SO
		for product_id, dict_branch_id in dict_product_sale.iteritems():
			for branch_id, value in dict_branch_id.iteritems():
				self.create(cr, uid, {
					'product_id': product_id,
					'number_of_sales': value['qty'],
					'branch_id' : branch_id})
	
	def create_dict_for_sale_history(self, cr, uid, sale_ids, context={}):
		dict_product_sale = {}
		sale_order_obj = self.pool.get('sale.order')
		for sale in sale_order_obj.browse(cr, uid, sale_ids):
			for line in sale.order_line:
				if dict_product_sale.get(line.product_id.id, False):
					dict_product_sale[line.product_id.id][sale.branch_id.id]['qty'] += self.count_uom_qty(cr, uid, line.product_id.id, line.product_uom_qty, line.product_uom.id, context=context)
				else:
					dict_product_sale[line.product_id.id] = {sale.branch_id.id: {'qty' : self.count_uom_qty(cr, uid, line.product_id.id, line.product_uom_qty, line.product_uom.id, context=context)}}
		
		return dict_product_sale
	
	def get_sale_history_ids(self, cr, uid, product_id, start_year, end_year, start_month, end_month, branch_id=False, context=None):
		""" override """
		if not branch_id:
			return super(sale_history, self).get_sale_history_ids(cr, uid, product_id, start_year, end_year, start_month, end_month, context=context)
		else:
			sale_history_ids = []
			if start_year == end_year:
				# if start and end year are the same, then search by all parameters
				sale_history_ids.extend(self.search(cr, uid, [
					('branch_id', '=', branch_id),
					('product_id', '=', product_id),
					('year', '>=', start_year),
					('year', '<=', end_year),
					('month', '>=', start_month),
					('month', '<=', end_month),
				], context=context))
			else:
				# if start and end year are different,
				# then it must be only 1 year difference, because month_before_after are at most 11 month
				# find history from start month and start year to last month that start year
				sale_history_ids.extend(self.search(cr, uid, [
					('branch_id', '=', branch_id),
					('product_id', '=', product_id),
					('year', '=', start_year),
					('month', '>=', start_month),
					('month', '<=', 12),
				], context=context))
				# merge with history from first month that end year to end month that end year
				sale_history_ids.extend(self.search(cr, uid, [
					('branch_id', '=', branch_id),
					('product_id', '=', product_id),
					('year', '=', end_year),
					('month', '>=', 1),
					('month', '<=', end_month),
				], context=context))
		return sale_history_ids


# ===========================================================================================================================

class purchase_needs_draft_memory(osv.TransientModel):
	_inherit = 'purchase.needs.draft.memory'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}


# ===========================================================================================================================

class purchase_needs_draft(osv.Model):
	_inherit = 'purchase.needs.draft'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}


# ===========================================================================================================================

class purchase_needs(osv.TransientModel):
	_inherit = 'purchase.needs'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
	_defaults = {
		'branch_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.id,
	}
	
	def _create_value_purchase_order(self, cr, uid, purchase_need, context = {}):
		value_po = super(purchase_needs, self)._create_value_purchase_order(cr, uid, purchase_need, context = context)
		data_obj = self.pool.get('ir.model.data')
		price_type_id = data_obj.get_object(cr, uid, 'tbvip', 'tbvip_normal_price_buy').id
		value_po['price_type_id'] = price_type_id
		
		return value_po
	
	def _create_value_purchase_order_line(self, cr, uid, draft_need, partner, context = {}):
		po_line = super(purchase_needs, self)._create_value_purchase_order_line(cr, uid, draft_need, partner,context = context)
		data_obj = self.pool.get('ir.model.data')
		price_type_id = data_obj.get_object(cr, uid, 'tbvip', 'tbvip_normal_price_buy').id
		unit_id = data_obj.get_object(cr, uid, 'product', 'product_uom_unit').id
		product_current_price_obj = self.pool.get('product.current.price')
		
		product = draft_need.product_id
		current_price = product_current_price_obj.get_current_price(cr, uid, product.id, price_type_id, unit_id)
		po_line['price_unit'] = current_price
		return po_line
	
	def onchange_supplier_id(self, cr, uid, ids, supplier_id, context=None):
		""" override """
		result = {'value': {
			'draft_po_line_ids': [],
			'draft_needs_ids': [],
			'purchase_needs_line_ids': [],
		}}
		branch_obj = self.pool.get('tbvip.branch')
		user_branch_id = self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id
		all_branch_ids = branch_obj.search(cr, uid, [], context=context)
		
		# get all draft purchase order line from supplier
		purchase_order_obj = self.pool.get('purchase.order')
		draft_purchase_order_ids = purchase_order_obj.search(cr, uid, [
			('branch_id', '=', user_branch_id),
			('state', '=', 'draft'),
			('partner_id', '=', supplier_id),
		], context=context)
		for po in purchase_order_obj.browse(cr, uid, draft_purchase_order_ids, context=context):
			for po_line in po.order_line:
				result['value']['draft_po_line_ids'].append((0, False, {
					'date_order': po.date_order,
					'product_id': po_line.product_id.id,
					'product_qty': po_line.product_qty,
				}))
		
		# get all draft needs
		purchase_needs_draft_obj = self.pool.get('purchase.needs.draft')
		purchase_needs_draft_ids = purchase_needs_draft_obj.search(cr, uid, [
			('branch_id', '=', user_branch_id),
			('supplier_id', '=', supplier_id),
		], context=context)
		for needs_draft in purchase_needs_draft_obj.browse(cr, uid, purchase_needs_draft_ids, context=context):
			result['value']['draft_needs_ids'].append((0, False, {
				'branch_id': user_branch_id,
				'product_id': needs_draft.product_id.id,
				'product_qty': needs_draft.product_qty,
			}))
		
		# get all products from supplier
		product_supplierinfo_obj = self.pool.get('product.supplierinfo')
		purchase_needs_line_obj = self.pool.get('purchase.needs.line')
		purchase_needs_line_line_obj = self.pool.get('purchase.needs.line.line')
		product_supplierinfo_ids = product_supplierinfo_obj.search(cr, uid, [('name', '=', supplier_id)], context=context)
		product_ids = []
		for product_supplierinfo in product_supplierinfo_obj.browse(cr, uid, product_supplierinfo_ids, context=context):
			product_ids.extend(product_supplierinfo.product_tmpl_id.product_variant_ids.ids)
		for product_id in product_ids:
			# line line
			line_line_arr = []
			for branch_id in all_branch_ids:
				year_ids, min_stock, max_stock, weight, data_count, order = \
					purchase_needs_line_line_obj.get_purchase_needs_line_line_required_fields(cr, uid, product_id, branch_id, context=context)
				line_line_arr.append((0, False, {
					'branch_id':	branch_id,
					'year_ids': 	year_ids,
					'min_stock': 	min_stock,
					'max_stock': 	max_stock,
					'weight': 		weight,
					'data_count': 	data_count,
					'order': 		order,
				}))
			# line
			qty_string, last_sale_date, min_string, max_string, order_string = \
				purchase_needs_line_obj.get_purchase_needs_line_required_fields(cr, uid, product_id, line_line_arr, context=context)
			result['value']['purchase_needs_line_ids'].append((0, False, {
				'product_id': 		product_id,
				'line_ids': 		line_line_arr,
				'qty_string': 		qty_string,
				'last_sale_date': 	last_sale_date,
				'min_string': 		min_string,
				'max_string': 		max_string,
				'order_string': 	order_string,
			}))
		return result
	
	def onchange_purchase_needs_line_ids(self, cr, uid, ids, supplier_id, purchase_needs_line_ids, draft_needs_ids, context=None):
		""" override """
		result = {
			'value': {
				'selected_product_id': 0,
				'purchase_needs_line_ids': purchase_needs_line_ids,
				'draft_needs_ids': draft_needs_ids
			}
		}
		# draft needs
		user_branch_id = self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id
		purchase_needs_draft_obj = self.pool.get('purchase.needs.draft')
		for purchase_needs_line in purchase_needs_line_ids:
			if 'add_to_draft' in purchase_needs_line[2] and purchase_needs_line[2]['add_to_draft']:
				if 'line_ids' in purchase_needs_line[2]:
					product_qty = 0
					for line_line in purchase_needs_line[2]['line_ids']:
						if 'branch_id' in line_line[2] and line_line[2]['branch_id'] == user_branch_id:
							product_qty += line_line[2]['order'] if 'order' in line_line[2] else 0
					if product_qty > 0:
						same_draft_ids = purchase_needs_draft_obj.search(cr, uid, [
							('branch_id', '=', user_branch_id),
							('supplier_id', '=', supplier_id),
							('product_id', '=', purchase_needs_line[2]['product_id']),
						], context=context)
						if same_draft_ids and len(same_draft_ids) == 0:
							new_needs_draft_id = purchase_needs_draft_obj.create(cr, uid, {
								'branch_id': user_branch_id,
								'supplier_id': supplier_id,
								'product_id': purchase_needs_line[2]['product_id'],
								'product_qty': product_qty,
							}, context=context)
							if new_needs_draft_id:
								result['value']['draft_needs_ids'].append((0, False, {
									'branch_id': user_branch_id,
									'needs_draft_id': new_needs_draft_id,
									'supplier_id': supplier_id,
									'product_id': purchase_needs_line[2]['product_id'],
									'product_qty': product_qty,
								}))
		# last purchase
		for purchase_needs_line in purchase_needs_line_ids:
			if 'last_purchase' in purchase_needs_line[2] and purchase_needs_line[2]['last_purchase']:
				purchase_needs_line[2]['last_purchase'] = False
				result['value']['selected_product_id'] = purchase_needs_line[2]['product_id']
				break
		return result


# ===========================================================================================================================

class purchase_needs_line(osv.TransientModel):
	_inherit = 'purchase.needs.line'
	
	def get_purchase_needs_line_required_fields(self, cr, uid, product_id, line_line_arr=[], context=None):
		""" override """
		if len(line_line_arr) == 0:
			return super(purchase_needs_line_line, self).get_purchase_needs_line_required_fields(cr, uid, product_id, context=context)
		else:
			branch_obj = self.pool.get('tbvip.branch')
			qty_string = ""
			last_sale_date = False
			min_string = ""
			max_string = ""
			order_string = ""
			
			# last sale date
			cr.execute("""
				SELECT
					max(so.date_order)
				FROM sale_order_line so_line
					LEFT JOIN sale_order so
						ON so_line.order_id = so.id
				WHERE so_line.product_id = {};
			""".format(product_id))
			records = cr.fetchall()
			for record in records:
				last_sale_date = record[0]
				break
			
			for line_line in line_line_arr:
				# qty
				branch = self.pool.get('tbvip.branch').browse(cr, uid, line_line[2]['branch_id'], context=context)
				quant_obj = self.pool.get('stock.quant')
				quant_ids = quant_obj.search(cr, uid, [
					('product_id', '=', product_id),
					('location_id.usage', '=', 'internal'),
					('location_id', '=', branch.default_stock_location_id.id)
				])
				qty_total = 0
				for quant in quant_obj.browse(cr, uid, quant_ids):
					qty_total += quant.qty
				qty_string += branch.name + ": " + str(qty_total) + "\n"
				
				# min
				min_string += branch.name + ": " + str(line_line[2]['min_stock']) + "\n"
				
				# max
				max_string += branch.name + ": " + str(line_line[2]['max_stock']) + "\n"
				
				# order
				order_string += branch.name + ": " + str(line_line[2]['order']) + "\n"
			
			return (qty_string, last_sale_date, min_string, max_string, order_string)


# ===========================================================================================================================

class purchase_needs_line_line(osv.TransientModel):
	_inherit = 'purchase.needs.line.line'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
	def get_year_ids(self, cr, uid, product_id, branch_id=False, context={}):
		""" override """
		purchase_needs_config_settings_obj = self.pool.get('purchase.needs.config.settings')
		purchase_needs_line_line_year_obj = self.pool.get('purchase.needs.line.line.year')
		start_year, end_year, start_month, end_month, leap_year_before, leap_year_after = \
			purchase_needs_config_settings_obj.get_start_end_information(cr, uid, context=context)
		year_arr = []
		while start_year <= end_year:
			month_count, average, weekly = purchase_needs_line_line_year_obj.get_month_count_average_weekly(cr, uid, start_year, product_id, branch_id, context=context)
			year_arr.append((0, False, {
				'year': start_year,
				'month_count': month_count,
				'average': average,
				'weekly': weekly,
			}))
			start_year += 1
		return year_arr
	
	def get_year_min_max_weight_count(self, cr, uid, product_id, branch_id=False, context=None):
		""" override """
		if not branch_id:
			return super(purchase_needs_line_line, self).get_year_min_max_weight_count(cr, uid, product_id, context=context)
		else:
			sale_history_obj = self.pool.get('sale.history')
			purchase_needs_config_settings_obj = self.pool.get('purchase.needs.config.settings')
			
			coef_min = float(self.pool.get('ir.config_parameter').get_param(cr, uid, 'purchase_needs.coef_min', '').strip())
			coef_max = float(self.pool.get('ir.config_parameter').get_param(cr, uid, 'purchase_needs.coef_max', '').strip())
			
			start_year, end_year, start_month, end_month, leap_year_before, leap_year_after = \
				purchase_needs_config_settings_obj.get_start_end_information(cr, uid, context=context)
			year_ids = self.get_year_ids(cr, uid, product_id, branch_id, context=context)
			weekly_total = 0
			weekly_count = len(year_ids)
			min_stock = 0
			max_weekly = 0
			weight = 0
			data_count = 0
			for year in year_ids:
				if 'weekly' in year[2]:
					# min stock
					weekly_total += year[2]['weekly']
					if year[2]['weekly'] > max_weekly:
						# max stock
						max_weekly = year[2]['weekly']
				# weight
				if start_year <= end_year:
					cur_year = start_year
					while cur_year <= end_year:
						cur_start_year = cur_year - leap_year_before
						cur_end_year = cur_year + leap_year_after
						sale_history_ids = sale_history_obj.get_sale_history_ids(
							cr, uid, product_id, cur_start_year, cur_end_year, start_month, end_month, branch_id, context=context)
						for sale_hist in sale_history_obj.browse(cr, uid, sale_history_ids, context=context):
							if 'average' in year[2] and sale_hist.number_of_sales > year[2]['average']:
								weight += 1
						cur_year += 1
				# data count
				data_count += year[2]['month_count'] if 'month_count' in year[2] else 0
			if weekly_count != 0:
				min_stock = math.floor(float(weekly_total)/weekly_count) * coef_min
			max_stock = max_weekly * coef_max
			return (year_ids, min_stock, max_stock, weight, data_count)
	
	def get_purchase_needs_line_line_required_fields(self, cr, uid, product_id, branch_id=False, context=None):
		""" override """
		if not branch_id:
			return super(purchase_needs_line_line, self).get_purchase_needs_line_line_required_fields(cr, uid, product_id, context=context)
		else:
			coef_order = float(self.pool.get('ir.config_parameter').get_param(cr, uid, 'purchase_needs.coef_order', '').strip())
			year_ids, min_stock, max_stock, weight, data_count = self.get_year_min_max_weight_count(cr, uid, product_id, branch_id, context=context)
			if data_count == 0:
				return (year_ids, min_stock, max_stock, weight, data_count, 0)
			return (year_ids, min_stock, max_stock, weight, data_count, ((float(weight)/data_count) * coef_order) + min_stock)

# ===========================================================================================================================

class purchase_needs_line_line_year(osv.TransientModel):
	_inherit = 'purchase.needs.line.line.year'
	
	def get_month_count_average_weekly(self, cr, uid, year, product_id, branch_id=False, context=None):
		""" override """
		if not branch_id:
			return super(purchase_needs_line_line_year, self).get_month_count_average_weekly(cr, uid, product_id, context=context)
		else:
			sale_history_obj = self.pool.get('sale.history')
			purchase_needs_config_settings_obj = self.pool.get('purchase.needs.config.settings')
			start_year, end_year, start_month, end_month, leap_year_before, leap_year_after = \
				purchase_needs_config_settings_obj.get_start_end_information(cr, uid, context=context)
			if start_year > end_year:
				return (0, 0.0, 0.0)
			else:
				total_sales = 0
				month_count = 0
				cur_start_year = year - leap_year_before
				cur_end_year = year + leap_year_after
				sale_history_ids = sale_history_obj.get_sale_history_ids(
					cr, uid, product_id, cur_start_year, cur_end_year, start_month, end_month, branch_id, context=context)
				month_count += len(sale_history_ids)
				for sale_hist in sale_history_obj.browse(cr, uid, sale_history_ids, context=context):
					total_sales += sale_hist.number_of_sales
				if month_count == 0:
					return (0, 0.0, 0.0)
				else:
					average = float(total_sales) / month_count
					weekly = math.floor(average / 4)
					return (month_count, average, weekly)

