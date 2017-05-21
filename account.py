from openerp.osv import osv, fields


class account_journal_edc(osv.osv):
	_inherit = 'account.journal.edc'

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'current_branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
