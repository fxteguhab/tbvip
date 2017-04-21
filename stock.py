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
		'request_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'usage_by': lambda self, cr, uid, ctx: uid,
		'state': 'draft',
	}
	
	# CONSTRAINT ---------------------------------------------------------------------------------------------------------------
	
	def _usage_line_min(self, cr, uid, ids, context=None):
		# Cek bonus usage line harus ada minimal 1 baris
		# for replace_vehicles in self.browse(cr, uid, ids, context):
		# 	for replace_vehicle in replace_vehicles:
		# 		if replace_vehicle.replaced_vehicle_id.model_id.id != replace_vehicle.replacement_vehicle_id.model_id.id:
		# 			return False
		return True
	
	# JUNED: tambahkan constraint di mana replacement vehicle tidak boleh sedang dipakai di kontrak aktif lainnya
	_constraints = [
		(_usage_line_min, _('You must have at least one usage line.'), ['bonus_usage_line']),
	]
	
	# ACTION ----------------------------------------------------------------------------------------------------------------
	
	def action_approve (self, cr, uid, ids, context=None):
		return
	
	def action_reject (self, cr, uid, ids, context=None):
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

# ==========================================================================================================================