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
	
	def _bank_ids(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for account_voucher_data in self.browse(cr, uid, ids, context=context):
			res_partner_obj = self.pool.get('res.partner')
			for partner_data in res_partner_obj.browse(cr, uid, account_voucher_data.partner_id.id):
				if len(partner_data.bank_ids) > 0:
					result[account_voucher_data.id] = partner_data.bank_ids[0].id
		return result
				
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'total_amount_unreconciled': fields.function(_total_amount_unreconciled, string="Total Amount Reconciled",
			type='float', store=True),
		'check_maturity_date': fields.date(string='Check Maturity Date',
			readonly=True, states={'draft': [('readonly', False)]}),
		'bank_id': fields.function(_bank_ids, string="Bank Account", type='many2one', relation="res.partner.bank", store=True),
	}
