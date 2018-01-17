from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta


# ===========================================================================================================================

class account_journal_simplified(osv.osv):
	_inherit = 'account.journal.simplified'
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'employee_id': fields.many2one('hr.employee', 'Employee'),
		'preset_id': fields.many2one('account.journal.preset', 'Transaction Type', required=True, domain="['|', ('branch_id', '=', branch_id), ('branch_id', '=', False)]"),
		'preset_code': fields.char('Preset Code'),
		'expense_line_ids': fields.one2many('account.journal.simplified.line.expense', 'account_journal_simplified_id', 'Lines'),
		'retur_line_ids': fields.one2many('account.journal.simplified.line.retur', 'account_journal_simplified_id', 'Lines'),
		'paysupp_line_ids': fields.one2many('account.journal.simplified.line.paysupp', 'account_journal_simplified_id', 'Lines'),
	}
	
	_defaults = {
		'branch_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id,
	}
	
	def create(self, cr, uid, vals, context={}):
		def _execute_tbvip_scenarios(created_simplified_journal):
			code = created_simplified_journal.preset_id.code
			if code.startswith('EXPENSE'):
				if not vals.get('employee_id', False):
					raise osv.except_osv(_('Error Expense Preset!'), _("Please specify the Employee."))
				# "catat expense non-canvassing. Harus ada list product expense nya (misal pungli, iuran warga, dsb) yang
				# ketika save transaksi ada create hr.expense.expense."
				expense_obj = self.pool.get('hr.expense.expense')
				expense_line_obj = self.pool.get('hr.expense.line')
				new_expense_id = expense_obj.create(cr, uid, {
					'employee_id': created_simplified_journal.employee_id.id or False,
					'date': created_simplified_journal.journal_date,
					'name': created_simplified_journal.name,
				})
				for line in created_simplified_journal.line_ids:
					expense_line_obj.create(cr, uid, {
						'expense_id': new_expense_id,
						'product_id': line.product_id.id,
						'date_value': created_simplified_journal.journal_date,
						'name': created_simplified_journal.name,
						'uom_id': line.product_id.uom_id.id,
						'unit_amount': line.amount,
						'unit_quantity': line.qty,
					})
			elif code.startswith("RETUR"):
				pass
			elif code.startswith("PAYSUPP"):
				# "bayar supplier. Harus plus list invoice yang mau dibayar beserta amount pembayarannya (onchange invoice,
				# autofill amount nya idem amount terhutang invoice itu). account_journal_simplified.amount diisi otomatis
				# sebagai jumlah dari amount seluruh invoice yang dipilih."
				# for line in created_simplified_journal.line_ids:
				# 	self.pool.get('account.invoice').pay_and_reconcile(cr, uid, [line.invoice_id.id], line.amount,
				# 		line.invoice_id.account_id.id, line.invoice_id.period_id.id, line.invoice_id.journal_id.id,
				# 		line.invoice_id.account_id.id, line.invoice_id.period_id.id, line.invoice_id.journal_id.id, context)
				# for line in created_simplified_journal.line_ids:
					# voucher_obj = self.pool.get('account.voucher')
					# inv = line.invoice_id
					# move_line_id = 0
					# for move_line in inv.move_id.line_id:
					# 	if inv.type == 'in_invoice':
					# 		move_line_id = move_line.id if move_line.debit == 0 else move_line_id
					# 	else:
					# 		move_line_id = move_line.id if move_line.credit == 0 else move_line_id
					# new_voucher_id = voucher_obj.create(cr, uid, {
					# 	'partner_id': inv.partner_id.id,
					# 	'amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
					# 	'account_id': inv.account_id.id,
					# 	'journal_id': inv.journal_id.id,
					# 	'type': 'receipt' if inv.type == 'out_invoice' else 'payment',
					# 	'reference': created_simplified_journal.name,
					# 	'date': created_simplified_journal.journal_date,
					# 	'pay_now': 'pay_now',
					# 	'date_due': created_simplified_journal.journal_date,
					# 	'line_dr_ids': [(0, False, {
					# 		'type': 'dr' if inv.type == 'in_invoice' else 'cr',
					# 		'account_id': inv.account_id.id,
					# 		'partner_id': inv.partner_id.id,
					# 		'amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
					# 		'move_line_id': move_line_id,
					# 		'reconcile': True,
					# 	})]
					# })
					# voucher_obj.proforma_voucher(cr, uid, [new_voucher_id])
					# if self.type in ('in_invoice', 'in_refund'):
					# 	ref = self.reference
					# 	else:
					# 	ref = self.number
					# partner = self.partner_id._find_accounting_partner(self.partner_id)
					# name = name or self.invoice_line[0].name or self.number
					# # Pay attention to the sign for both debit/credit AND amount_currency
					# l1 = {
					# 	'name': name,
					# 	'debit': direction * pay_amount > 0 and direction * pay_amount,
					# 	'credit': direction * pay_amount < 0 and -direction * pay_amount,
					# 	'account_id': self.account_id.id,
					# 	'partner_id': partner.id,
					# 	'ref': ref,
					# 	'date': date,
					# 	'currency_id': currency_id,
					# 	'amount_currency': direction * (amount_currency or 0.0),
					# 	'company_id': self.company_id.id,
					# }
					# l2 = {
					# 	'name': name,
					# 	'debit': direction * pay_amount < 0 and -direction * pay_amount,
					# 	'credit': direction * pay_amount > 0 and direction * pay_amount,
					# 	'account_id': pay_account_id,
					# 	'partner_id': partner.id,
					# 	'ref': ref,
					# 	'date': date,
					# 	'currency_id': currency_id,
					# 	'amount_currency': -direction * (amount_currency or 0.0),
					# 	'company_id': self.company_id.id,
					# }
					# move = self.env['account.move'].create({
					# 	'ref': ref,
					# 	'line_id': [(0, 0, l1), (0, 0, l2)],
					# 	'journal_id': pay_journal_id,
					# 	'period_id': period_id,
					# 	'date': date,
					# })
				pass
			elif code.startswith("DAYEND"):
				pass
			
				
		
		new_id = super(account_journal_simplified, self).create(cr, uid, vals, context)
		# Check for some particular codes for several tbvip related scenarios
		_execute_tbvip_scenarios(self.browse(cr, uid, new_id, context))
		return new_id
	
	def onchange_preset_id(self, cr, uid, ids, preset_id, context=None):
		result = {
			'value': {
				'preset_code': '',
			}
		}
		if preset_id:
			account_journal_preset_obj = self.pool.get('account.journal.preset')
			acc_journal_preset = account_journal_preset_obj.browse(cr, uid, preset_id, context=context)
			code = acc_journal_preset.code
			if code:
				if code.startswith('EXPENSE'):
					result['value']['preset_code'] = 'EXPENSE'
				elif code.startswith("RETUR"):
					result['value']['preset_code'] = 'RETUR'
				elif code.startswith("PAYSUPP"):
					result['value']['preset_code'] = 'PAYSUPP'
				elif code.startswith("DAYEND"):
					result['value']['preset_code'] = 'DAYEND'
		return result
	
# ===========================================================================================================================

class account_journal_simplified_line_expense(osv.osv):
	_name = 'account.journal.simplified.line.expense'
	
	_columns = {
		'account_journal_simplified_id': fields.many2one('account.journal.simplified', 'Simplified Account Journal'),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'amount': fields.float('Amount', required=True),
	}


# ===========================================================================================================================

class account_journal_simplified_line_retur(osv.osv):
	_name = 'account.journal.simplified.line.retur'
	
	_columns = {
		'account_journal_simplified_id': fields.many2one('account.journal.simplified', 'Simplified Account Journal'),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'qty': fields.float('Qty', required=True),
	}
	
	_defaults = {
		'qty': lambda self, cr, uid, context: 1,
	}


# ===========================================================================================================================

class account_journal_simplified_line_paysupp(osv.osv):
	_name = 'account.journal.simplified.line.paysupp'
	
	_columns = {
		'account_journal_simplified_id': fields.many2one('account.journal.simplified', 'Simplified Account Journal'),
		'invoice_id': fields.many2one('account.invoice', 'Invoice', required=True),
		'amount': fields.float('Amount', required=True),
	}
	
	def onchange_invoice_id(self, cr, uid, ids, invoice_id, context=None):
		result = {
			'value': {
				'amount': '',
			}
		}
		if invoice_id:
			account_invoice_obj = self.pool.get('account.invoice')
			acc_inv = account_invoice_obj.browse(cr, uid, invoice_id, context=context)
			result['value']['amount'] = acc_inv.residual
		return result

# ===========================================================================================================================

class account_journal_preset(osv.osv):
	_inherit = 'account.journal.preset'
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', help="Empty for global preset."),
	}
	
	_defaults = {
		'branch_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id,
	}
