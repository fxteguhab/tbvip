from openerp.osv import osv, fields
from openerp import _
from openerp.tools import float_compare
from datetime import datetime, date, timedelta
import openerp.addons.decimal_precision as dp

# ==========================================================================================================================

class account_voucher(osv.osv):
	_inherit = 'account.voucher'

	def _default_writeoff_acc_id(self, cr, uid, context={}):
		model, account_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'account_counterpart_payable_rounding')
		return account_id or None

	# OVERRIDES -------------------------------------------------------------------------------------------------------------

	def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
		result = super(account_voucher, self).onchange_partner_id(
			cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context)
	# ambil default account buat payment. default sesuai yang diset di user atau cabang
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
	# ambil default account buat payment. default sesuai yang diset di user atau cabang
		res['value']['account_id'] = self._get_account_id(cr, uid, ttype, uid, context)[0]
		return res
	
	def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context=None):
		result = super(account_voucher, self).onchange_journal(
			cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id, context)
		
		if journal_id:
		# ambil default account buat payment. default sesuai yang diset di user atau cabang
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
	
	def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
	# cegah dari otomatis mencentang line-line invoice bila ada perubahan paid amount
	# dengan ini, pemilihan invoice yang mau dibayar harus totally manual
	# hanya jalankan ketika mode create, sehingga list voucher ter-load untuk user centang
	# bila sudah edit maka jangan set ulang list dr/cr
		if not ids:
			price = 0
			return super(account_voucher, self).recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=context)
		else:
			return {'value': {}}

	def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
		result = super(account_voucher, self).voucher_move_line_create(cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=context)
	# hapus voucher line yang amount paid nya 0, supaya ngga ngebingungin pas liat 
	# detail voucher
		voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=context)
		prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
		line_ids_to_delete = []
		for line in voucher.line_ids:
			if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
				line_ids_to_delete.append(line.id)
		self.pool.get('account.voucher.line').unlink(cr, uid, line_ids_to_delete)
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

	def _selected_amount(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for account_voucher_data in self.browse(cr, uid, ids, context=context):
			total = 0
			for line in account_voucher_data.line_dr_ids:
				if account_voucher_data.type == 'payment':
					total += line.amount
				# if lainnya menyusul
			for line in account_voucher_data.line_cr_ids:
				if account_voucher_data.type == 'payment':
					total -= line.amount
			result[account_voucher_data.id] = total
		return result

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'check_maturity_date': fields.date(string='Check Maturity Date',
			readonly=True, states={'draft': [('readonly', False)]}),
		'bank_id': fields.many2one('res.partner.bank', 'Supplier Bank Account'),
		'is_ready': fields.function(_is_ready, type="boolean", string="Is Ready", store=True),
		'reference': fields.char('Ref #', readonly=False, states={},
			help="Transaction reference number.", copy=False),
		'amount': fields.float('Total Paid', digits_compute=dp.get_precision('Account'), required=True, readonly=True, states={'draft':[('readonly',False)]}),
		'selected_amount': fields.function(_selected_amount, type="float", string="Total Amount"),
	}

	_defaults = {
		'check_maturity_date': lambda *a: datetime.today().strftime('%Y-%m-%d'),
		'writeoff_acc_id': _default_writeoff_acc_id,
		'comment': _('Rounding'),
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

	# ACTIONS ----------------------------------------------------------------------------------------------------------------

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

	def action_dummy(self, cr, uid, ids, context={}):
		return True

# ==========================================================================================================================


class account_voucher_line(osv.osv):
	_inherit = 'account.voucher.line'
	_order = 'voucher_id, id'
	
	def _invoice_id(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for line in self.browse(cr, uid, ids, context=context):
			result[line.id] = line.move_line_id.invoice.id
		return result

	_columns = {
		'invoice_id': fields.function(_invoice_id, type='many2one', relation='account.invoice',
			string='Invoice'),
	}

	def action_open_invoice(self, cr, uid, ids, context={}):
		model_obj = self.pool.get('ir.model.data')
		model, view_id = model_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
		line_data = self.browse(cr, uid, ids[0], context=context)
		return {
			'type': 'ir.actions.act_window',
			'name': 'Invoice Detail',
			'view_mode': 'form',
			'view_type': 'form',
			'view_id': view_id,
			'res_id': line_data.invoice_id.id,
			'res_model': 'account.invoice',
			'nodestroy': True,
			'flags': {'form': {'options': {'mode': 'view'} } },
			'context': {'simple_view': 1},
			'target': 'new',
		}
