from openerp.osv import osv, fields


# ==========================================================================================================================


class account_voucher(osv.osv):
	_inherit = 'account.voucher'
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
		result = super(account_voucher, self).onchange_partner_id(
			cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context)
		
		partner_obj = self.pool.get('res.partner')
		partner = partner_obj.browse(cr, uid, [partner_id])
		# if not result.get('domain', False):
		# 	result['domain'] = {}
		# result['domain'].update({
		# 	'bank_id': [('id', 'in', partner.bank_ids.ids)],
		# })
		
		return result
	
	# FIELD FUNCTION METHODS ------------------------------------------------------------------------------------------------
	
	def _bank_ids(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for account_voucher_data in self.browse(cr, uid, ids, context=context):
			res_partner_obj = self.pool.get('res.partner')
			for partner_data in res_partner_obj.browse(cr, uid, account_voucher_data.partner_id.id):
				if len(partner_data.bank_ids) > 0:
					result[account_voucher_data.id] = partner_data.bank_ids[0].id
				else:
					result[account_voucher_data.id] = None
		return result
				
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'check_maturity_date': fields.date(string='Check Maturity Date',
			readonly=True, states={'draft': [('readonly', False)]}),
		# 'bank_id': fields.function(_bank_ids, string="Bank Account", type='many2one', relation="res.partner.bank", readonly=False),
		'bank_id': fields.many2one('res.partner.bank', 'Bank Account'),
	}
