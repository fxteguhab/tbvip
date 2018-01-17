from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta


class account_journal_simplified(osv.osv):
	_inherit = 'account.journal.simplified'
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'employee_id': fields.many2one('hr.employee', 'Employee'),
		'preset_id': fields.many2one('account.journal.preset', 'Transaction Type', required=True, domain="['|', ('branch_id', '=', branch_id), ('branch_id', '=', False)]"),
		'line_ids': fields.one2many('account.journal.simplified.line', 'account_journal_simplified_id', 'Lines'),
	}
	
	_defaults = {
		'branch_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id,
	}
	
	def create(self, cr, uid, vals, context={}):
		def _execute_tbvip_scenarios(created_simplified_journal):
			code = created_simplified_journal.preset_id.code
			if code.startswith('EXPENSE'):
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
				for line in created_simplified_journal.line_ids:
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
					if self.type in ('in_invoice', 'in_refund'):
						ref = self.reference
						else:
						ref = self.number
					partner = self.partner_id._find_accounting_partner(self.partner_id)
					name = name or self.invoice_line[0].name or self.number
					# Pay attention to the sign for both debit/credit AND amount_currency
					l1 = {
						'name': name,
						'debit': direction * pay_amount > 0 and direction * pay_amount,
						'credit': direction * pay_amount < 0 and -direction * pay_amount,
						'account_id': self.account_id.id,
						'partner_id': partner.id,
						'ref': ref,
						'date': date,
						'currency_id': currency_id,
						'amount_currency': direction * (amount_currency or 0.0),
						'company_id': self.company_id.id,
					}
					l2 = {
						'name': name,
						'debit': direction * pay_amount < 0 and -direction * pay_amount,
						'credit': direction * pay_amount > 0 and direction * pay_amount,
						'account_id': pay_account_id,
						'partner_id': partner.id,
						'ref': ref,
						'date': date,
						'currency_id': currency_id,
						'amount_currency': -direction * (amount_currency or 0.0),
						'company_id': self.company_id.id,
					}
					move = self.env['account.move'].create({
						'ref': ref,
						'line_id': [(0, 0, l1), (0, 0, l2)],
						'journal_id': pay_journal_id,
						'period_id': period_id,
						'date': date,
					})
				pass
			elif code.startswith("DAYEND"):
				pass
			
				
		
		new_id = super(account_journal_simplified, self).create(cr, uid, vals, context)
		# Check for some particular codes for several tbvip related scenarios
		_execute_tbvip_scenarios(self.browse(cr, uid, new_id, context))
		return new_id
	
	
class account_journal_simplified_line(osv.osv):
	_name = 'account.journal.simplified.line'
	
	_columns = {
		'account_journal_simplified_id': fields.many2one('account.journal.simplified', 'Simplified Account Journal'),
		'product_id': fields.many2one('product.product', 'Product'),
		'invoice_id': fields.many2one('account.invoice', 'Invoice'),
		'qty': fields.float('Qty'),
		'amount': fields.float('Amount'),
	}
	
	_defaults = {
		'qty': lambda self, cr, uid, context: 1,
	}
	

class account_journal_preset(osv.osv):
	_inherit = 'account.journal.preset'
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', help="Empty for global preset."),
	}
	
	_defaults = {
		'branch_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id,
	}
