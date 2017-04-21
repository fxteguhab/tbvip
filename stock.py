from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime

# ==========================================================================================================================

class stock_location(osv.osv):
	
	_inherit = 'stock.location'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'is_branch': fields.boolean('Is Branch?'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
	}

# ==========================================================================================================================

class stock_bonus_usage(osv.osv):
	
	_name = 'stock.bonus.usage'
	_description = 'Stock Bonus Usage'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'usage_date': fields.datetime('Usage Date', required=True),
		'name': fields.char('Name', required=True),
		'usage_by': fields.many2one('res.users', 'Usage By', required=True),
		'move_from': fields.many2one('stock.location', 'Move From', required=True),
		'bonus_usage_line': fields.one2many('stock.bonus.usage.line', 'bonus_usage_id', 'Usage'),
		'state': fields.selection([
			('draft','Draft'),
			('approved','Approved'),
			('rejected','Rejected')], 'State', required=True),
	}
	
	# DEFAULTS --------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'usage_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'usage_by': lambda self, cr, uid, ctx: uid,
		'state': 'draft',
	}
	
	# CONSTRAINT ---------------------------------------------------------------------------------------------------------------
	
	def _usage_line_min(self, cr, uid, ids, context=None):
		# Cek bonus usage line harus ada minimal 1 baris
		for bonus_usage in self.browse(cr, uid, ids, context):
			if len(bonus_usage.bonus_usage_line) == 0:
				return False
		return True
	
	def _move_from_min_qty(self, cr, uid, ids, context=None):
		# Cek bahwa setiap product di line harus punya minimal sejumlah qty yang diminta di stock location move_from
		quant_obj = self.pool["stock.quant"]
		uom_obj = self.pool["product.uom"]
		for bonus_usage in self.browse(cr, uid, ids, context):
			for line in bonus_usage.bonus_usage_line:
				domain = [('location_id', '=', bonus_usage.move_from.id), ('product_id','=', line.product_id.id)]
				quant_ids = quant_obj.search(cr, uid, domain, context=context)
				quants = quant_obj.browse(cr, uid, quant_ids, context=context)
				tot_qty = sum([x.qty for x in quants])
				if line.unit_of_measure and line.product_id.uom_id.id != line.unit_of_measure.id:
					tot_qty = uom_obj._compute_qty_obj(cr, uid, line.product_id.uom_id, tot_qty, line.unit_of_measure, context=context)
				if tot_qty < line.qty:
					return False
		return True
	
	_constraints = [
		(_usage_line_min, _('You must have at least one usage line.'), ['bonus_usage_line']),
		(_move_from_min_qty, _('The location does not have that many product.'), ['move_from', 'bonus_usage_line']),
	]
	
	# ACTION ----------------------------------------------------------------------------------------------------------------
	
	def action_approve (self, cr, uid, ids, context=None):
		return
	
	def action_reject (self, cr, uid, ids, context=None):
		for bonus_usages in self.browse(cr, uid, ids, context):
			for bonus_usage in bonus_usages:
				bonus_usage.state = 'rejected'
		return

# ==========================================================================================================================

class stock_bonus_usage_line(osv.osv):
	
	_name = 'stock.bonus.usage.line'
	_description = 'Stock Bonus Usage Line'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'bonus_usage_id': fields.many2one('stock.bonus.usage', 'Bonus Usage'),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'qty': fields.float('Qty', required=True),
		'unit_of_measure': fields.many2one('product.uom', 'Unit of Measure', required=True),
	}
	
	# ONCHANGE -----------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		# unit_of_measure hanya bisa uom_id product ybs
		if not product_id: return {}
		product_obj = self.pool.get('product.product')
		res = {}
		res['value'] = {'unit_of_measure': ''}
		for product_data in product_obj.browse(cr, uid, product_id):
			res['domain'] = {'unit_of_measure': [('category_id','=', product_data.product_tmpl_id.uom_id.category_id.id)]}
		return res
	
	def onchange_unit_of_measure(self, cr, uid, ids, unit_of_measure, product_id, context=None):
		# unit_of_measure hanya bisa uom_id product ybs
		if not product_id: return {}
		product_obj = self.pool.get('product.product')
		uom_obj = self.pool.get('product.uom')
		res = {}
		for product_data in product_obj.browse(cr, uid, product_id):
			for uom_data in uom_obj.browse(cr, uid, unit_of_measure):
				if product_data.product_tmpl_id.uom_id.category_id.id != uom_data.category_id.id:
					res = self.onchange_product_id(cr, uid, ids, product_id, context)
					res['warning'] = {'title': _('Warning!'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure.')}
		return res

# ==========================================================================================================================
