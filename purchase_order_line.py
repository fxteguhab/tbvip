from openerp.osv import osv, fields
from datetime import datetime


# ==========================================================================================================================

class purchase_order_line(osv.osv):
	_inherit = 'purchase.order.line'
	
	# FIELD FUNCTION METHODS ------------------------------------------------------------------------------------------------
	def _purchase_hour(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		lines = self.browse(cr, uid, ids)
		for line in lines:
			purchase_date = datetime.strptime(line.date_order, '%Y-%m-%d %H:%M:%S')
			result[line.id] = purchase_date.hour * 3600 + purchase_date.minute * 60
		return result
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_purchase_det_id': fields.integer('MySQL Purchase Detail ID'),
		'purchase_hour': fields.function(_purchase_hour, method=True, string='Purchase Hour', type='float'),
		'alert': fields.integer('Alert'),
	}
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def unlink(self, cr, uid, ids, context=None):
		result = super(purchase_order_line, self).write(cr, uid, ids, context)
		demand_line_obj = self.pool.get('tbvip.demand.line')
		demand_line_ids = demand_line_obj.search(cr, uid, [('sale_order_line_id','in',ids)])
		demand_line_obj.write(cr, uid, demand_line_ids, {
			'state': 'requested'
		})
		return result
