##############################################################################
#
#    Kelas ini merupakan gabungan dari modul account - account_invoice_refund.py,
# 	 modul stock - stock_return_picking.py, dan modul account - account_invoice.py
#
#    Kelas ini menggabungkan fungsi-fungsi dan field-field dari account_invoice_refund.py,
# 	 stock_return_picking.py, dan account_invoice dengan memodifikasi beberapa fungsi
#
##############################################################################

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import time
from openerp import models, api, _
from openerp import fields as fields10

TYPE2REFUND = {
	'out_invoice': 'out_refund',        # Customer Invoice
	'in_invoice': 'in_refund',          # Supplier Invoice
	'out_refund': 'out_invoice',        # Customer Refund
	'in_refund': 'in_invoice',          # Supplier Refund
}

MAGIC_COLUMNS = ('id', 'create_uid', 'create_date', 'write_uid', 'write_date')

# ==========================================================================================================================

class sale_order_return_line(osv.osv_memory):
	_name = "sale.order.return.line"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'product_id': fields.many2one('product.product', string="Product", required=True),
		'quantity': fields.float("Quantity", digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
		'amount_price': fields.float("Amount Price", digits_compute=dp.get_precision('Account'), required=True),
		'sale_order_return_id': fields.many2one('sale.order.return', string="Sale Order Return"),
		'move_id': fields.many2one('stock.move', "Move"),
		'lot_id': fields.many2one('stock.production.lot', 'Serial Number', help="Used to choose the lot/serial number of the product returned"),
	}

# ==========================================================================================================================
	
class sale_order_return(models.TransientModel):
	_name = 'sale.order.return'
	_description = 'Return Sale Order'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	#return stock
	product_return_moves = fields10.One2many('sale.order.return.line', 'sale_order_return_id', 'Moves')
	move_dest_exists= fields10.Boolean('Chained Move Exists', readonly=True, help="Technical field used to hide help tooltip if not needed")
	
	#refund invoice
	date = fields10.Date('Date')
	period = fields10.Many2one('account.period', 'Force period')
	journal_id = fields10.Many2one('account.journal', 'Refund Journal', help='You can select here the journal to use for the credit note that will be created. If you leave that field empty, it will use the same journal as the current invoice.')
	description = fields10.Char('Reason', required=True)
	
	def _get_journal(self, cr, uid, context=None):
		"""
		Fungsi ini didapat dari account_invoice_refund tanpa ada perubahan fungsi
		"""
		obj_journal = self.pool.get('account.journal')
		user_obj = self.pool.get('res.users')
		if context is None:
			context = {}
		inv_type = context.get('type', 'out_invoice')
		company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
		type = (inv_type == 'out_invoice') and 'sale_refund' or \
			   (inv_type == 'out_refund') and 'sale' or \
			   (inv_type == 'in_invoice') and 'purchase_refund' or \
			   (inv_type == 'in_refund') and 'purchase'
		journal = obj_journal.search(cr, uid, [('type', '=', type), ('company_id','=',company_id)], limit=1, context=context)
		return journal and journal[0] or False
	
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		'journal_id': _get_journal,
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
		"""
		Fungsi ini didapat dari account_invoice_refund tanpa ada perubahan fungsi
		"""
		journal_obj = self.pool.get('account.journal')
		user_obj = self.pool.get('res.users')
		# remove the entry with key 'form_view_ref', otherwise fields_view_get crashes
		context = dict(context or {})
		context.pop('form_view_ref', None)
		res = super(sale_order_return,self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
		company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
		journal_type = 'sale_refund'
		for field in res['fields']:
			if field == 'journal_id':
				journal_select = journal_obj._name_search(cr, uid, '', [('type', '=', journal_type), ('company_id','child_of',[company_id])], context=context)
				res['fields'][field]['selection'] = journal_select
		return res
	
	def default_get(self, cr, uid, fields, context=None):
		"""
		 Fungsi ini didapat dari stock_return_picking tanpa ada perubahan fungsi
		"""
		result1 = []
		if context is None:
			context = {}
		if context and context.get('stock_picking_ids', False):
			if len(context.get('stock_picking_ids')) > 1:
				raise osv.except_osv(_('Warning!'), _("You may only return one picking at a time!"))
		res = super(sale_order_return, self).default_get(cr, uid, fields, context=context)
		record_id = context and context.get('stock_picking_id', False) or False
		uom_obj = self.pool.get('product.uom')
		pick_obj = self.pool.get('stock.picking')
		pick = pick_obj.browse(cr, uid, record_id, context=context)
		quant_obj = self.pool.get("stock.quant")
		chained_move_exist = False
		if pick:
			if pick.state != 'done':
				raise osv.except_osv(_('Warning!'), _("You may only return pickings that are Done!"))

			for move in pick.move_lines:
				if move.move_dest_id:
					chained_move_exist = True
				#Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
				qty = 0
				quant_search = quant_obj.search(cr, uid, [('history_ids', 'in', move.id), ('qty', '>', 0.0), ('location_id', 'child_of', move.location_dest_id.id)], context=context)
				for quant in quant_obj.browse(cr, uid, quant_search, context=context):
					if not quant.reservation_id or quant.reservation_id.origin_returned_move_id.id != move.id:
						qty += quant.qty
				qty = uom_obj._compute_qty(cr, uid, move.product_id.uom_id.id, qty, move.product_uom.id)
				result1.append({'product_id': move.product_id.id, 'quantity': qty, 'move_id': move.id})

			if len(result1) == 0:
				raise osv.except_osv(_('Warning!'), _("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
			if 'product_return_moves' in fields:
				res.update({'product_return_moves': result1})
			if 'move_dest_exists' in fields:
				res.update({'move_dest_exists': chained_move_exist})
		return res
	
# FUNCTION ------------------------------------------------------------------------------------------------------------------

	def _create_returns(self, cr, uid, ids, context=None):
		"""
		 Fungsi ini didapat dari stock_return_picking dan dimodifikasi
		"""
		if context is None:
			context = {}
		record_id = context and context.get('stock_picking_id', False) or False
		move_obj = self.pool.get('stock.move')
		pick_obj = self.pool.get('stock.picking')
		uom_obj = self.pool.get('product.uom')
		data_obj = self.pool.get('sale.order.return.line')
		pick = pick_obj.browse(cr, uid, record_id, context=context)
		data = self.read(cr, uid, ids[0], context=context)
		returned_lines = 0

		# Cancel assignment of existing chained assigned moves
		moves_to_unreserve = []
		for move in pick.move_lines:
			to_check_moves = [move.move_dest_id] if move.move_dest_id.id else []
			while to_check_moves:
				current_move = to_check_moves.pop()
				if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
					moves_to_unreserve.append(current_move.id)
				split_move_ids = move_obj.search(cr, uid, [('split_from', '=', current_move.id)], context=context)
				if split_move_ids:
					to_check_moves += move_obj.browse(cr, uid, split_move_ids, context=context)

		if moves_to_unreserve:
			move_obj.do_unreserve(cr, uid, moves_to_unreserve, context=context)
			#break the link between moves in order to be able to fix them later if needed
			move_obj.write(cr, uid, moves_to_unreserve, {'move_orig_ids': False}, context=context)

		#Create new picking for returned products
		pick_type_id = pick.picking_type_id.return_picking_type_id and pick.picking_type_id.return_picking_type_id.id or pick.picking_type_id.id
		new_picking = pick_obj.copy(cr, uid, pick.id, {
			'move_lines': [],
			'picking_type_id': pick_type_id,
			'state': 'draft',
			'origin': pick.name,
		}, context=context)

		for data_get in data_obj.browse(cr, uid, data['product_return_moves'], context=context):
			move = data_get.move_id
			if not move:
				raise osv.except_osv(_('Warning !'), _("You have manually created product lines, please delete them to proceed"))
			new_qty = data_get.quantity
			if new_qty:
				# The return of a return should be linked with the original's destination move if it was not cancelled
				if move.origin_returned_move_id.move_dest_id.id and move.origin_returned_move_id.move_dest_id.state != 'cancel':
					move_dest_id = move.origin_returned_move_id.move_dest_id.id
				else:
					move_dest_id = False

				returned_lines += 1
				move_obj.copy(cr, uid, move.id, {
					'product_id': data_get.product_id.id,
					'product_uom_qty': new_qty,
					'product_uos_qty': new_qty * move.product_uos_qty / move.product_uom_qty,
					'picking_id': new_picking,
					'state': 'draft',
					'location_id': move.location_dest_id.id,
					'location_dest_id': move.location_id.id,
					'picking_type_id': pick_type_id,
					'warehouse_id': pick.picking_type_id.warehouse_id.id,
					'origin_returned_move_id': move.id,
					'procure_method': 'make_to_stock',
					'restrict_lot_id': data_get.lot_id.id,
					'move_dest_id': move_dest_id,
				})

		if not returned_lines:
			raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))

		pick_obj.action_confirm(cr, uid, [new_picking], context=context)
		pick_obj.action_assign(cr, uid, [new_picking], context)
		
	# Modify to make state done (stock transferred)
		pop_up = pick_obj.do_enter_transfer_details(cr, uid, [new_picking], context)
		if pop_up:
			stock_transfer_detail_id = pop_up['res_id']
			stock_transfer_detail_obj = self.pool.get(pop_up['res_model'])
			stock_transfer_detail_obj.do_detailed_transfer(cr, uid, stock_transfer_detail_id)
		
		return new_picking, pick_type_id
	
	def compute_refund(self, cr, uid, ids, context=None):
		"""
		 Fungsi ini didapat dari account_invoice_refund dan dimodifikasi
		 Fungsi ini menggunakan filter_refund = 'cancel'
		"""
		inv_obj = self.pool.get('account.invoice')
		account_m_line_obj = self.pool.get('account.move.line')
		mod_obj = self.pool.get('ir.model.data')
		act_obj = self.pool.get('ir.actions.act_window')
		res_users_obj = self.pool.get('res.users')
		sale_order_obj = self.pool.get('sale.order')
		if context is None:
			context = {}

		sale_order_id = context.get('so_id', 0)
		return_amount = 0
		
		for form in self.browse(cr, uid, ids, context=context):
			created_inv = []
			company = res_users_obj.browse(cr, uid, uid, context=context).company_id
			journal_id = form.journal_id.id
			for inv in inv_obj.browse(cr, uid, context.get('invoice_ids'), context=context):
				if inv.state in ['draft', 'proforma2', 'cancel']:
					raise osv.except_osv(_('Error!'), _('Cannot cancel draft/proforma/cancel invoice.'))
				# Ko teguh pengen ketika sudah di reconciled juga dapat di retur, tetapi invoice yang sudah paid atau dibayar sebagian tidak dapat di cancel
				# Dengan demikian pengecekan raise di comment, tidak tau apakah effect buruknya, karena diliat dari journal saldo tetap balance
				# if inv.reconciled:
				# 	raise osv.except_osv(_('Error!'), _('Cannot cancel invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.'))
				if form.period.id:
					period = form.period.id
				else:
					period = inv.period_id and inv.period_id.id or False
				
				if not journal_id:
					journal_id = inv.journal_id.id
				
				if form.date:
					date = form.date
					if not form.period.id:
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
				else:
					date = inv.date_invoice
				if form.description:
					description = form.description
				else:
					description = inv.name
				
				if not period:
					raise osv.except_osv(_('Insufficient Data!'), \
						_('No period found on the invoice.'))
				
				dict_line = {}
			# bikin dictionary retur_line untuk fungsi _refund_cleanup_lines
				
				inv_obj.write(cr, uid, [inv.id], {'number': inv.number + " <Retur>"})
				
				for return_line in form.product_return_moves:
					dict_line[return_line.product_id.id] = {'quantity' : return_line.quantity,
															'price_subtotal': return_line.amount_price,
															'price_unit': return_line.amount_price/return_line.quantity}
					return_amount += return_line.amount_price
								
			#  Bikin Invoice refund
				refund_id = self._create_invoice_refund(cr, uid, ids, date, period, description, journal_id, [inv.id], dict_line,context=context)
				refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
				inv_obj.write(cr, uid, [refund.id], {'date_due': date,
					'check_total': inv.check_total})
				inv_obj.button_compute(cr, uid, refund_id)
				
				created_inv.append(refund_id[0])
				movelines = inv.move_id.line_id
				to_reconcile_ids = {}
				
			# Invoice yang direfund jangan di reconcile(dilunasin), biarkan dia tetap state asal. Karena bisa aja kasusnya balikin duit doang, belum lunasin
			# Invoice refund baru di reooncile
				# for line in movelines:
				#     if line.account_id.id == inv.account_id.id:
				#         to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
				#     if line.reconcile_id:
				#         line.reconcile_id.unlink()
	
				refund.signal_workflow('invoice_open')
				refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
				
				for tmpline in refund.move_id.line_id:
					if tmpline.account_id.id == inv.account_id.id:
						if not to_reconcile_ids.get(tmpline.account_id.id, False):
							to_reconcile_ids.setdefault(tmpline.account_id.id, []).append(tmpline.id)
						else:
							to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
				for account in to_reconcile_ids:
					account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
						writeoff_period_id=period,
						writeoff_journal_id = inv.journal_id.id,
						writeoff_acc_id=inv.account_id.id
					)
					
			if sale_order_id:
				sale_order_obj.write(cr, uid, sale_order_id, {
					'return_amount': return_amount
				})
			
			# xml_id = (inv.type == 'out_refund') and 'action_invoice_tree1' or \
			# 		 (inv.type == 'in_refund') and 'action_invoice_tree2' or \
			# 		 (inv.type == 'out_invoice') and 'action_invoice_tree3' or \
			# 		 (inv.type == 'in_invoice') and 'action_invoice_tree4'
			# result = mod_obj.get_object_reference(cr, uid, 'account', xml_id)
			# id = result and result[1] or False
			#
			# result = act_obj.read(cr, uid, [id], context=context)[0]
			#
			# invoice_domain = eval(result['domain'])
			# invoice_domain.append(('id', 'in', created_inv))
			#
			# result['domain'] = invoice_domain
			# return result
			return True
		
	@api.multi
	@api.returns('self')
	def _create_invoice_refund(self, date=None, period_id=None, description=None, journal_id=None, invoice_ids = [], retur_line = {}):
		"""
		 Fungsi ini didapat dari account_invoice - fungsi refund, direname menjadi _create_invoice_refund
		 Fungsi ini di tambahkan paramater retur_line untuk dipassing ke _prepare_refund
		"""
		inv_obj = self.env['account.invoice']
		new_invoices = inv_obj.browse()
		for invoice in inv_obj.browse(invoice_ids):
			# create the new invoice
			values = self._prepare_refund(invoice, date=date, period_id=period_id,
				description=description, journal_id=journal_id, retur_line = retur_line)
			new_invoices += inv_obj.create(values)
		return new_invoices
	
	@api.model
	def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None, retur_line = {}):
		"""
		 Fungsi ini didapat dari account_invoice,
		 Fungsi ini juga di tambahkan paramater retur_line untuk dipassing ke _refund_cleanup_lines
		"""
		values = {}
		for field in ['name', 'reference', 'comment', 'date_due', 'partner_id', 'company_id',
			'account_id', 'currency_id', 'payment_term', 'user_id', 'fiscal_position']:
			if invoice._fields[field].type == 'many2one':
				values[field] = invoice[field].id
			else:
				values[field] = invoice[field] or False
		
		values['invoice_line'] = self._refund_cleanup_lines(invoice.invoice_line, retur_line)
		
		tax_lines = filter(lambda l: l.manual, invoice.tax_line)
		values['tax_line'] = self._refund_cleanup_lines(tax_lines)
		
		if journal_id:
			journal = self.env['account.journal'].browse(journal_id)
		elif invoice['type'] == 'in_invoice':
			journal = self.env['account.journal'].search([('type', '=', 'purchase_refund')], limit=1)
		else:
			journal = self.env['account.journal'].search([('type', '=', 'sale_refund')], limit=1)
		values['journal_id'] = journal.id
		
		values['type'] = TYPE2REFUND[invoice['type']]
		values['date_invoice'] = date or fields.Date.context_today(invoice)
		values['state'] = 'draft'
		values['number'] = False
		values['origin'] = invoice.number
		
		if period_id:
			values['period_id'] = period_id
		if description:
			values['name'] = description
		return values
	
	@api.model
	def _refund_cleanup_lines(self, lines, retur_line = False):
		"""
		 Fungsi ini didapat dari account_invoice, fungsi ini di tambahkan paramater retur_line
		 retur_line merupakan dictionary dari line sale_order_return, berisi product-product yang akan di retur dan uang yang akan di refund.
		 
		 Fungsi ini pada awalnya berguna untuk membuat line account_invoice untuk refund dari account_invoice yang akan direfund (linenya anggapan dicopy sama persis)
		 Fungsi ini dimodifikasi agar line dari account_invoice refund berisi product yang akan direfund saja, serta dimodifikasi quantity dan price_unit sesuai dengan input dari refund
		"""
		result = []
		for line in lines:
			values = {}
		# Jika tidak diberikan retur_line, maka lines tersebut berisi line tax, bukan line invoice
			if retur_line:
				# Product untuk line account refund hanya berisi sesuai dengan line dari sale_order_return
				if line.product_id.id in retur_line:
					for name, field in line._fields.iteritems():
						if name in MAGIC_COLUMNS:
							continue
						elif field.type == 'many2one':
							values[name] = line[name].id
						elif field.type not in ['many2many', 'one2many']:
							if name == 'quantity':
								values[name] = retur_line[line.product_id.id]['quantity']
							elif name == 'price_unit':
								values[name] = retur_line[line.product_id.id]['price_unit']
							elif name == 'price_subtotal':
								values[name] = retur_line[line.product_id.id]['price_subtotal']
							else:
								values[name] = line[name]
						elif name == 'invoice_line_tax_id':
							values[name] = [(6, 0, line[name].ids)]
					
			else:
				for name, field in line._fields.iteritems():
					if name in MAGIC_COLUMNS:
						continue
					elif field.type == 'many2one':
						values[name] = line[name].id
					elif field.type not in ['many2many', 'one2many']:
						values[name] = line[name]
					elif name == 'invoice_line_tax_id':
						values[name] = [(6, 0, line[name].ids)]
			if values:
				result.append((0, 0, values))
		return result

	def create_returns(self, cr, uid, ids, context=None):
		
		#return stock
		new_picking_id, pick_type_id = self._create_returns(cr, uid, ids, context=context)
		
		# # Override the context to disable all the potential filters that could have been set previously
		# ctx = {
		# 	'search_default_picking_type_id': pick_type_id,
		# 	'search_default_draft': False,
		# 	'search_default_assigned': False,
		# 	'search_default_confirmed': False,
		# 	'search_default_ready': False,
		# 	'search_default_late': False,
		# 	'search_default_available': False,
		# }
		# return {
		# 	'domain': "[('id', 'in', [" + str(new_picking_id) + "])]",
		# 	'name': _('Returned Picking'),
		# 	'view_type': 'form',
		# 	'view_mode': 'tree,form',
		# 	'res_model': 'stock.picking',
		# 	'type': 'ir.actions.act_window',
		# 	'context': ctx,
		# }

		#refund invoice
		form_customer_refund = self.compute_refund(cr, uid, ids, context=context)
		# return form_customer_refund
		return {
			'warning': {
				'title': 'Successful!',
				'message': 'Retur succeeded'}
		}