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
