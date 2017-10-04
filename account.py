from datetime import datetime, timedelta
from openerp import api
from openerp.osv import osv, fields

# ==========================================================================================================================

class account_journal_edc(osv.osv):
	_inherit = 'account.journal.edc'

# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'current_branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
# ==========================================================================================================================

class account_invoice(osv.osv):
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
		'row_count': fields.function(_row_count, type="integer", string="Row Count"),
		'related_sales_bon_number': fields.char("Nomor Bon", readonly=True),
	}
	
	def invoice_auto_done(self, cr, uid, ids, context=None):
		for invoice in self.browse(cr, uid, ids):
			invoice.signal_workflow('invoice_open')
	
	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		"""
		Update name_search (like in m2o search) domain to search with sale bon number for today (in infix):
		('number', '=', name)
			OR (('related_sales_bon_number', '=', name)
				AND (date_invoice', '>=', today.strftime('%Y-%m-%d'))
				AND ('date_invoice', '<', tommorow.strftime('%Y-%m-%d'))
			)
		"""
		args = args or []
		recs = self.browse()
		if name:
			today = datetime.today()
			tommorow = datetime.today() + timedelta(1)
			recs = self.search([
					'|',
					('number', '=', name),
					'&', ('related_sales_bon_number', '=', name),
					'&', ('date_invoice', '>=', today.strftime('%Y-%m-%d')),
					('date_invoice', '<', tommorow.strftime('%Y-%m-%d'))] + args, limit=limit)
		if not recs:
			recs = self.search([('name', operator, name)] + args, limit=limit)
		return recs.name_get()

# ==========================================================================================================================

class account_move_line(osv.osv):
	_inherit = 'account.move.line'
	_description = 'Modifikasi untuk menambah amount di SO'
	
	def create(self, cr, uid, vals, context={}):
		new_id = super(account_move_line, self).create(cr, uid, vals, context=context)
		if context.get('payment_method_type', False) and context.get('sale_order_id', False):
			sale_order_obj = self.pool.get('sale.order')
			payment_method_type = context['payment_method_type']
			sale_order_id = context['sale_order_id']
			sale_order_data = sale_order_obj.browse(cr, uid, sale_order_id)
			if payment_method_type and vals.get('debit', False):
				if payment_method_type == 'transfer' or payment_method_type == 'receivable':
					sale_order_obj.write(cr, uid, sale_order_id, {
						'is_complex_payment': True
					})
		return new_id