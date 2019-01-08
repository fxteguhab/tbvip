from openerp.osv import osv, fields


# ==========================================================================================================================

class res_users(osv.osv):
	_inherit = 'res.users'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	'''
	'default_journal_purchase_override': fields.many2one('account.journal', 'Default Purchase Cash Journal',
		help="Overrides default purchase cash journal from branch."),
	'default_journal_sales_override': fields.many2one('account.journal', 'Default Sale Cash Journal',
		help="Overrides default purchase cash journal from branch."),
	'default_journal_sales_retur_override': fields.many2one('account.journal', 'Default Sale Retur Cash Journal',
		help="Overrides default purchase cash journal from branch."),
	'''

