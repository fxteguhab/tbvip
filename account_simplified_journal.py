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
				for line in created_simplified_journal.expense_line_ids:
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
				# retur barang, harus plus list barang yang diretur. Ketika save transaksi, buat stock picking baru dengan
				# barang2 ini move dari customer location ke cabang di mana retur terjadi.
				# contoh create dapet dari point_of_sale, create_picking, baris 843
				if not created_simplified_journal.branch_id:
					raise osv.except_osv(_('Retur Error'),_('Please input branch for Retur transaction.'))
				picking_obj = self.pool.get('stock.picking')
				model_obj = self.pool.get('ir.model.data')
				location_obj = self.pool.get('stock.location')
				stock_move_obj = self.pool.get('stock.move')
				warehouse_obj = self.pool.get('stock.warehouse')
				
				location_src = location_obj.browse(cr, uid, model_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')[1]),
				location_dest = created_simplified_journal.branch_id.default_incoming_location_id.id
				warehouse_id = warehouse_obj.search(cr, uid, [('lot_stock_id', '=', location_src.id)], limit=1)
				warehouse = warehouse_obj.browse(cr, uid, warehouse_id, context)
				max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
				max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
				
				picking_id = picking_obj.create(cr, uid, {
					'picking_type_id': model_obj.get_object_reference(cr, uid, 'stock', 'picking_type_internal')[1],
					'move_type': 'direct',
					'note': 'Cash Transaction ' + location_src.name + '/' + location_dest.name,
					'location_id': location_src.id,
					'location_dest_id': location_dest.id,
					'origin': 'Cash Transaction - ' + str(created_simplified_journal.name),
				}, context=context)
				#untuk setiap product, bikin stock movenya
				for line in created_simplified_journal.retur_line_ids:
					picking_type_id = stock_move_obj.create(cr, uid, vals={
						'name': _('Stock_move') + ' ' + location_src.name + '/' + location_dest.name,
						'warehouse_id': warehouse.id,
						'location_id': location_src.id,
						'location_dest_id': location_dest.id,
						'sequence': max_sequence + 1,
						'product_id': line.product_id.id,
						'product_uom': line.uom_id.id,
						'picking_id' : picking_id,
						'product_uom_qty' : line.qty
					}, context=context)
				pass
			elif code.startswith("PAYSUPP"):
				# "bayar supplier. Harus plus list invoice yang mau dibayar beserta amount pembayarannya (onchange invoice,
				# autofill amount nya idem amount terhutang invoice itu). account_journal_simplified.amount diisi otomatis
				# sebagai jumlah dari amount seluruh invoice yang dipilih."
				for line in created_simplified_journal.line_ids:
					self.pool.get('account.invoice').pay_and_reconcile(cr, uid, [line.invoice_id.id], line.amount,
						line.invoice_id.account_id.id, line.invoice_id.period_id.id, line.invoice_id.journal_id.id,
						line.invoice_id.account_id.id, line.invoice_id.period_id.id, line.invoice_id.journal_id.id, context)
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


# ===========================================================================================================================

class account_journal_simplified_line_paysupp(osv.osv):
	_name = 'account.journal.simplified.line.paysupp'
	
	_columns = {
		'account_journal_simplified_id': fields.many2one('account.journal.simplified', 'Simplified Account Journal'),
		'invoice_id': fields.many2one('account.invoice', 'Invoice', required=True),
		'amount': fields.float('Amount', required=True),
	}
	
	def onchange_invoice_id(self, cr, uid, ids, invoice_id, context=None):
		pass

# ===========================================================================================================================

class account_journal_preset(osv.osv):
	_inherit = 'account.journal.preset'
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', help="Empty for global preset."),
	}
	
	_defaults = {
		'branch_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id,
	}
