from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

# ==========================================================================================================================

class product_category(osv.osv):
	
	_inherit = 'product.category'

# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
	}
	
# ORDER --------------------------------------------------------------------------------------------------------------------
	
	#_order = 'parent_id, codex_id'

# ==========================================================================================================================

class product_template(osv.osv):
	
	_inherit = 'product.template'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
	}