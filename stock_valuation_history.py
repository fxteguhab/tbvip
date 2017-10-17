from openerp.osv import osv, fields
from openerp.tools.translate import _

# ==========================================================================================================================

class stock_history(osv.osv):
	_inherit = 'stock.history'
	
	def _get_inventory_value(self, cr, uid, ids, name, attr, context=None):
		if context is None:
			context = {}
		res = {}
		for line in self.browse(cr, uid, ids, context=context):
			if line.price_unit_on_quant:
				res[line.id] = line.quantity * line.price_unit_on_quant
			else:
				date = context.get('history_date')
				product_tmpl_obj = self.pool.get("product.template")
				res[line.id] = line.quantity * product_tmpl_obj.get_history_price(cr, uid, line.product_id.product_tmpl_id.id, line.company_id.id, date=date, context=context)
		return res
	
	_columns = {
		'inventory_value': fields.function(_get_inventory_value, string="Inventory Value", type='float', readonly=True),
	}
