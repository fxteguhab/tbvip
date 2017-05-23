from openerp.osv import osv, fields


# ==========================================================================================================================

class res_users(osv.osv):
	_inherit = 'res.users'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
