from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from datetime import datetime, timedelta

class stock_opname_memory_line(osv.osv_memory):
	_inherit = "stock.opname.memory.line"
	
	_columns = {
		'sublocation': fields.text('Sublocations'),
	}
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		context = {} if context is None else None
		product_obj = self.pool.get('product.product')
		result = ''
		for product in product_obj.browse(cr, uid, [product_id], context):
			for product_sublocation_id in product.product_sublocation_ids:
				sublocation = product_sublocation_id.sublocation_id
				result += product_sublocation_id.branch_id.name + ' / ' + sublocation.full_name + '\r\n'
		return {'value': {'sublocation': result}}
