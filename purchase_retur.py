from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import models, api, _
from datetime import datetime, date, timedelta

_RETUR_STATE = [
	('draft', 'Draft'),
	('open','Open'),
	('done', 'Done'),
]

class purchase_retur(osv.osv):

	_name = 'purchase.retur'
	_description = 'Purchase Retur'

	def calc_amount(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for purchase_retur in self.browse(cr, uid, ids, context=context):
			total = 0
			for line in purchase_retur.retur_line_ids:
				total += line.price_unit_nett * line.qty
			result[purchase_retur.id] = total
		return result


	_columns = {
		'journal_date': fields.datetime('Transaction Date', required=True),
		#'amount': fields.float('Amount', required=True),
		'amount': fields.function(calc_amount, type="float", string="Total Amount"),
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		#'employee_id': fields.many2one('hr.employee', 'Employee'),
		'retur_line_ids': fields.one2many('purchase.retur.line', 'purchase_retur_id', 'Product Return:',  required=True, readonly=True, states={'draft':[('readonly',False)]}),
		#'payment_purchase_retur_journal': fields.many2one('account.journal', 'Journal for Cash Retur', domain=[('type','in',['cash','bank'])]),
		'partner_id': fields.many2one('res.partner', 'Supplier', required=True, domain="[('supplier', '=', True)]"),
		'desc': fields.char('Description'),
		'bon_number': fields.char('Invoice No', required=True),
		'state': fields.selection(_RETUR_STATE, 'State', required=True),
		'period' : fields.many2one('account.period', 'Force period'),
		'refund_journal_id' : fields.many2one('account.journal', 'Purchase Refund Journal'),
	}

	def _default_branch_id(self, cr, uid, context={}):
	# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.id or None

	def _default_payment_cash_journal(self, cr, uid, context={}):
		if user_data.branch_id.default_journal_purchase_retur:
			return user_data.branch_id.default_journal_purchase_retur.id
		else:
			return None
	
	def _get_journal(self, cr, uid, context=None):
		"""
		Fungsi ini didapat dari account_invoice_refund tanpa ada perubahan fungsi
		"""
		obj_journal = self.pool.get('account.journal')
		user_obj = self.pool.get('res.users')
		if context is None:
			context = {}
		inv_type = context.get('type', 'in_invoice')
		company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
		type = (inv_type == 'out_invoice') and 'sale_refund' or \
			   (inv_type == 'out_refund') and 'sale' or \
			   (inv_type == 'in_invoice') and 'purchase_refund' or \
			   (inv_type == 'in_refund') and 'purchase'
		journal = obj_journal.search(cr, uid, [('type', '=', type), ('company_id','=',company_id)], limit=1, context=context)
		return journal and journal[0] or False

	_defaults = {
		'journal_date': lambda self, cr, uid, context: datetime.now(),
		'branch_id': _default_branch_id,
		'state': 'draft',
		'refund_journal_id': _get_journal,
	}

	def button_retur(self, cr, uid, ids, context=None):		
		journal_obj = self.pool.get('account.journal')
		journal_entry_obj = self.pool.get('account.move')
		user_obj = self.pool.get('res.users')
		cashier = user_obj.browse(cr, uid, uid)
		company = cashier.company_id

		retur = self.browse(cr,uid,ids)
		partner_id = retur.partner_id
		name = str(retur.partner_id.name)+'/ '+ str(retur.bon_number)
		date = retur.journal_date
		amount = retur.amount
		refund_journal_id = retur.refund_journal_id

		
		period = retur.period.id
		if not retur.period.id:
			cr.execute("select name from ir_model_fields \
									where model = 'account.period' \
									and name = 'company_id'")
			result_query = cr.fetchone()
			if result_query:
				cr.execute("""select p.id from account_fiscalyear y, account_period p where y.id=p.fiscalyear_id \
							and date(%s) between p.date_start AND p.date_stop and y.company_id = %s limit 1""", (date, company.id,))
			else:
				cr.execute("""SELECT id
								from account_period where date(%s)
								between date_start AND  date_stop  \
								limit 1 """, (date,))
			res = cr.fetchone()
			if res:
				period = res[0]

		inv_obj = self.pool.get('account.invoice')
		picking_obj = self.pool.get('stock.picking')
		model_obj = self.pool.get('ir.model.data')
		location_obj = self.pool.get('stock.location')
		stock_move_obj = self.pool.get('stock.move')
		warehouse_obj = self.pool.get('stock.warehouse')
		
		location_dest = location_obj.browse(cr, uid, model_obj.get_object_reference(cr, uid, 'stock', 'stock_location_suppliers')[1])
		location_src = retur.branch_id.default_incoming_location_id
		warehouse_id = warehouse_obj.search(cr, uid, [('lot_stock_id', '=', location_src.id)], limit=1)
		warehouse = warehouse_obj.browse(cr, uid, warehouse_id, context)
		#max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
		#max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
		
		picking_id = picking_obj.create(cr, uid, {
			'picking_type_id': model_obj.get_object_reference(cr, uid, 'stock', 'picking_type_internal')[1],
			'move_type': 'direct',
			'note': 'Cash Transaction ' + location_src.name + '/' + location_dest.name,
			'location_id': location_src.id,
			'location_dest_id': location_dest.id,
			'origin': 'Purchase Retur - ' + str(name),
		}, context=context)
		#untuk setiap product, bikin stock movenya
		for line in retur.retur_line_ids:
			stock_move = stock_move_obj.create(cr, uid, vals={
				'name' : line.product_id.name_template,
				'warehouse_id': warehouse.id,
				'location_id': location_src.id,
				'location_dest_id': location_dest.id,
				#'sequence': max_sequence + 1,
				'product_id': line.product_id.id,
				'product_uom': line.product_id.uom_id.id,
				'picking_id': picking_id,
				'product_uom_qty': line.qty,
				'price_unit' : line.price_unit_nett,
				'origin': 'Purchase Retur - ' + str(name),
			}, context=context)
		# Transfer created picking
		picking_obj.do_transfer(cr, uid, picking_id, context)


		###################################################################################################################################################################
		price_type_ids = self.pool.get('price.type').search(cr, uid, [('type','=','buy'),('is_default','=',True),])
		default_price_type_id = price_type_ids[0]

		retur_lines = []	
		for return_line in retur.retur_line_ids:
			values = {}
			values['quantity'] = return_line.qty
			values['price_subtotal']= return_line.qty * return_line.price_unit_nett
			values['price_unit'] = return_line.price_unit_nett
			values['origin'] = name
			values['product_id'] = return_line.product_id.id
			values['name'] = return_line.product_id.name_template
			values['partner_id'] = partner_id.id
			values['account_id'] = return_line.product_id.categ_id.property_account_expense_categ.id #journal_retur.default_debit_account_id.id
			values['price_type_id'] = default_price_type_id
			if values:
				retur_lines.append((0, 0, values))
		
		#  Bikin Invoice refund
		refund_invoice = inv_obj.create(cr, uid, {
			'reference' : str(retur.desc),
			#'date_due' : date,
			'number'  : False,
			'company_id' : cashier.company_id.id,
			'partner_id' : partner_id.id,
			'journal_id' : refund_journal_id.id,
 			'date_invoice': date,
 			'type' : 'in_refund',
 			'state' : 'draft',
 			'origin': retur.id,
 			'invoice_line' : retur_lines,
 			'account_id' : refund_journal_id.default_debit_account_id.id,
 			'period_id': period,
 			'name':name,
		}, context=context)
		
		inv_obj.button_compute(cr, uid, refund_invoice)
		refund = inv_obj.browse(cr, uid, refund_invoice, context=context)
		refund.signal_workflow('invoice_open')

		self.write(cr, uid, ids, {
			'state': 'open',
			'period':period,
		}, context=context)
		

class purchase_retur_line(osv.osv):
	_name = 'purchase.retur.line'
	
	_columns = {
		'purchase_retur_id': fields.many2one('purchase.retur', 'Purchase Retur'),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'qty': fields.float('Qty', required=True),
		'price_unit_nett' : fields.float(related = "product_id.product_tmpl_id.list_price",string="Price Nett"),
	}
	
	_defaults = {
		'qty': lambda self, cr, uid, context: 1,
	}