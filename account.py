from openerp.osv import osv, fields

# ==========================================================================================================================

class account_journal_edc(osv.osv):
	_inherit = 'account.journal.edc'

# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'current_branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
# ==========================================================================================================================

class account_journal_edc(osv.osv):
	_inherit = 'account.invoice'
	
	# FIELD FUNCTION METHOD ----------------------------------------------------------------------------------------------------
	
	def _qty_sum(self, cr, uid, ids, field_name, arg, context):
		result = {}
		for invoice_data in self.browse(cr, uid, ids, context):
			result[invoice_data.id] = 0
			for invoice_line_data in invoice_data.invoice_line:
				result[invoice_data.id] += invoice_line_data.quantity
		return result
	
	def _row_count(self, cr, uid, ids, field_name, arg, context):
		result = {}
		for invoice_data in self.browse(cr, uid, ids, context):
			result[invoice_data.id] = len(invoice_data.invoice_line)
		return result
	
# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'qty_sum': fields.function(_qty_sum, type="integer", string="Qty Sum"),
		'row_count': fields.function(_row_count, type="integer", string="Qty Sum"),
	}