from openerp.osv import osv, fields


# ==========================================================================================================================

class res_users(osv.osv):
	_inherit = 'res.users'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'default_account_purchase_override': fields.many2one('account.account', 'Default Account Purchase Override',
			help="Overrides default account purchase from branch."),
		'default_account_sales_override': fields.many2one('account.account', 'Default Account Sales Override',
			help="Overrides default account sales from branch."),
	}
