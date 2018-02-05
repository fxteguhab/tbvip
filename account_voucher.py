from openerp.osv import osv, fields
from openerp import _
from datetime import datetime, date, timedelta





# ==========================================================================================================================


class account_voucher(osv.osv):
	_inherit = 'account.voucher'
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------

	def onchange_partner_id_tbvip(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
		"""
		ATTENTION!!!!
		This method stops all future overrides that's loaded after it.
		This method does not override onchange_partner_id (instead use _tbvip in the method name)
		because overriding partner_id with additional 'domain' key in the result will cause an error.
		It will trigger buggy odoo code on account_voucher/account_voucher.py:917 because
		res['domain'] is not expected via Register Additional Payment button on Sales Order.
		"""
		result = super(account_voucher, self).onchange_partner_id(
			cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context)
		
		partner_obj = self.pool.get('res.partner')
		partner = partner_obj.browse(cr, uid, [partner_id])
		if not result.get('domain', False):
			result['domain'] = {}
		result['domain'].update({
			'bank_id': [('id', 'in', partner.bank_ids.ids)],
		})
		if not result.get('value', False):
			result['value'] = {}
		cash_account_id, bank_account_id = self._get_account_id(cr, uid, ttype, uid, context)
		account_id = False
		acc_journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
		if acc_journal.type == 'cash':
			account_id = cash_account_id
		elif acc_journal.type == 'bank':
			account_id = bank_account_id
		result['value']['account_id'] = account_id
		return result
	
	def _get_account_id(self, cr, uid, ttype, user_id, context=None):
		# Get Default account on branch and change account_id with it
		user_data = self.pool['res.users'].browse(cr, uid, user_id)
		default_account_purchase = user_data.default_account_purchase_override or user_data.branch_id.default_account_purchase
		default_account_sales = user_data.default_account_sales_override or user_data.branch_id.default_account_sales
		cash_account_id = False
		if ttype in ('sale', 'receipt') and default_account_sales:
			cash_account_id = default_account_sales.id
		elif ttype in ('purchase', 'payment'):
			cash_account_id = default_account_purchase.id
		
		bank_account_id = False
		bank_account_ids = self.pool.get('account.account').search(cr, uid, [('type', 'not in', ['view']), ('user_type.code', '=', 'bank')], context=context, limit=1)
		if len(bank_account_ids) > 0:
			bank_account_id = bank_account_ids[0]
		return cash_account_id, bank_account_id
	
	def basic_onchange_partner(self, cr, uid, ids, partner_id, journal_id, ttype, context=None):
		res = super(account_voucher,self).basic_onchange_partner(cr, uid, ids, partner_id, journal_id, ttype, context=context)
		res['value']['account_id'] = self._get_account_id(cr, uid, ttype, uid, context)[0]
		return res
	
	def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
		result = super(account_voucher, self).onchange_journal(
			cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context)
		
		if journal_id:
			cash_account_id, bank_account_id = self._get_account_id(cr, uid, ttype, uid, context)
			account_id = False
			acc_journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
			if acc_journal.type == 'cash':
				account_id = cash_account_id
			elif acc_journal.type == 'bank':
				account_id = bank_account_id
				
			if result:
				if 'value' in result:
					result['value']['account_id'] = account_id
				else:
					result['value'] = {'account_id': account_id}
			else:
				result = {'value': {'account_id': account_id}}
				
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
	
	def _is_ready(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for account_voucher_data in self.browse(cr, uid, ids, context=context):
			result[account_voucher_data.id] = True if account_voucher_data.reference and account_voucher_data.reference != '' else False
		return result
				
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'check_maturity_date': fields.date(string='Check Maturity Date',
			readonly=True, states={'draft': [('readonly', False)]}),
		# 'bank_id': fields.function(_bank_ids, string="Bank Account", type='many2one', relation="res.partner.bank", readonly=False),
		'bank_id': fields.many2one('res.partner.bank', 'Bank Account'),
		'is_ready': fields.function(_is_ready, type="boolean", string="Is Ready", store=True),
	}
	
	# PRINTS ----------------------------------------------------------------------------------------------------------------
	
	def print_kontra_bon(self, cr, uid, ids, context):
		if self.browse(cr,uid,ids)[0].line_dr_ids:
			return {
				'type' : 'ir.actions.act_url',
				'url': '/tbvip/print/account.voucher/' + str(ids[0]),
				'target': 'self',
			}
		else:
			raise osv.except_osv(_('Print Kontra Bon Error'),_('Kontra Bon must have at least one line to be printed.'))

	# REFRESH ----------------------------------------------------------------------------------------------------------------

	def action_refresh(self, cr, uid, ids, context=None):
		voucher_line_obj = self.pool.get('account.voucher.line')
		for voucher in self.browse(cr, uid, ids):
			res = self.onchange_amount(cr, uid, [voucher.id], voucher.amount, voucher.payment_rate, voucher.partner_id.id, voucher.journal_id.id, voucher.currency_id.id,
									   voucher.type, voucher.date, voucher.payment_rate_currency_id.id, voucher.company_id.id, context)
			if res['value'].get('line_cr_ids', False):
				for line_cr in res['value']['line_cr_ids']:
					if isinstance(line_cr, tuple):
						self.write(cr, uid, voucher.id, {'line_cr_ids': [line_cr]})
					elif isinstance(line_cr, dict):
						self.write(cr, uid, voucher.id, {'line_cr_ids': [(0, False, line_cr)]})
			if res['value'].get('line_dr_ids', False):
				for line_dr in res['value']['line_dr_ids']:
					if isinstance(line_dr, tuple):
						self.write(cr, uid, voucher.id, {'line_dr_ids': [line_dr]})
					elif isinstance(line_dr, dict):
						self.write(cr, uid, voucher.id, {'line_dr_ids': [(0, False, line_dr)]})

# ==========================================================================================================================


class account_voucher_line(osv.osv):
	_inherit = 'account.voucher.line'
	
	def _purchase_order_id(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for line in self.browse(cr, uid, ids, context=context):
			invoice_id = line.move_line_id.invoice.id
			if invoice_id:
				cr.execute("""
					SELECT purchase_id
					FROM purchase_invoice_rel
					WHERE invoice_id = {}
				""".format(invoice_id))
				res = cr.fetchone()
				if res and len(res) > 0:
					result[line.id] = res[0]
		return result

	_columns = {
		'purchase_order_id': fields.function(_purchase_order_id, type='many2one', relation='purchase.order',
			store=True, string='Purchase Order'),
	}
