from datetime import datetime, timedelta

from openerp.osv import osv, fields
from openerp.tools.translate import _
import math

from dateutil.relativedelta import relativedelta

class sale_history(osv.Model):
	_inherit = 'sale.history'
	
# OVERRIDES -----------------------------------------------------------------------------------------------------------------
	
	def count_uom_qty(self,cr, uid, product_id, qty, uom_id, context={}):
		"""
		Override function untuk menghitung qty, karena di tbvip terdapat modul product_custom_conversion. Dengan demikian gunakan
		function dari modul product_custom_conversion untuk menghitung uom qty
		"""
		product_conversion_obj = self.pool.get('product.conversion')
		uom_record = product_conversion_obj.get_conversion_auto_uom(cr, uid, product_id, uom_id)
		return super(sale_history, self).count_uom_qty(cr, uid, product_id, qty, uom_record.id, context=context)
		
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
