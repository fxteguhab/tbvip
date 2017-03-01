from openerp.osv import osv, fields


# ==========================================================================================================================

class res_partner(osv.osv):
	_inherit = 'res.partner'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_partner_id': fields.integer('MySQL Partner ID'),
		'phone': fields.char('Phone', size=100),
	}
