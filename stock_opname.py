from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from datetime import datetime, timedelta

class stock_opname_memory(osv.osv_memory):
	_inherit = 'stock.opname.memory'

	def action_generate_stock_opname(self, cr, uid, ids, context=None):
	# karena di tbvip location stock opname per barang pasti idem Inventoried Location,
	# maka di form field/kolom location di Inventories (stock_opname_memory_line.location_id) dihide
	# akhirnya kita harus ngisi satu2 field tsb berdasarkan stock_opname_memory.location_id
		memory_line_obj = self.pool.get('stock.opname.memory.line')
		for memory in self.browse(cr, uid, ids):
			for line in memory.line_ids:
				memory_line_obj.write(cr, uid, [line.id], {
					'location_id': memory.location_id.id,
					})
		return super(stock_opname_memory, self).action_generate_stock_opname(cr, uid, ids, context=context)


class stock_opname_memory_line(osv.osv_memory):
	_inherit = "stock.opname.memory.line"
	
	_columns = {
		'sublocation': fields.text('Sublocations'),
		'location_id': fields.many2one('stock.location', 'Location', required=False),
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
