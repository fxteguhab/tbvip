from openerp.osv import osv, fields


# ==========================================================================================================================

class account_voucher(osv.osv):
	_inherit = 'account.voucher'

	# FIELD FUNCTION METHODS ------------------------------------------------------------------------------------------------

	def _total_amount_unreconciled(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		account_voucher_line_obj = self.pool.get('account.voucher.line')
		for record in self.browse(cr, uid, ids, context=context):
			total_amount_unreconciled = 0
			account_voucher_line_ids = account_voucher_line_obj.search(cr, uid, [('voucher_id', '=', record.id)])
			for account_voucher_id in account_voucher_line_ids:
				account_voucher_line = account_voucher_line_obj.browse(cr, uid, [account_voucher_id])
				total_amount_unreconciled += account_voucher_line.amount_unreconciled
			result[record.id] = total_amount_unreconciled
		return result
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'total_amount_unreconciled': fields.function(_total_amount_unreconciled, string="Total Amount Reconciled", type='float', store=True),
	}
