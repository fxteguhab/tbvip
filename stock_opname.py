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
		result = ''
		for line in self.browse(cr, uid, ids. context):
			product_sublocation = ''
			for product_sublocation_id in line.product_id.product_sublocation_ids:
				sublocation = product_sublocation_id.sublocation_id
				product_sublocation += '\r\n' + sublocation.branch_id + ' / ' + sublocation.full_name
			result += '\r\n' + product_sublocation
		return {'value': {'sublocation': result}}
		
	