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
		
# ===========================================================================================================================

class purchase_needs_line(osv.TransientModel):
	_inherit = 'purchase.needs.line'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------

	def _get_last_sale_date(self, cr, uid, product_id, branch_id=False, context=None):
		"""
		Get the latest date of a sale.order.line with the given product_id and branch_id
		:param product_id: int id of product.product
		:param branch_id: int id of tbvip.branch; if not given or equals to False, omit branch_id filter
		:return: string date or False if not exist
		"""
		latest_date = False
		if not branch_id:
			latest_date = super(purchase_needs_line, self)._get_last_sale_date(cr, uid, product_id, context=context)
		else:
			cr.execute("""
				SELECT
					max(so.date_order)
				FROM sale_order_line so_line
					LEFT JOIN sale_order so
						ON so_line.order_id = so.id
				WHERE so_line.product_id = {} and so.branch_id = {};
			""".format(product_id, branch_id))
			records = cr.fetchall()
			for record in records:
				latest_date = record[0]
				break
		return latest_date

class purchase_needs(osv.TransientModel):
	_inherit = 'purchase.needs'
	
# OVERRIDES -----------------------------------------------------------------------------------------------------------------
	
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