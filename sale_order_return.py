from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import time
from openerp.tools.translate import _

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
	
class sale_order_return(osv.osv_memory):
	_name = 'sale.order.return'
	_description = 'Return Sale Order'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
		
	_columns = {
		#return stock
		'product_return_moves': fields.one2many('sale.order.return.line', 'sale_order_return_id', 'Moves'),
		'move_dest_exists': fields.boolean('Chained Move Exists', readonly=True, help="Technical field used to hide help tooltip if not needed"),
		
		#refund invoice
		'date': fields.date('Date'),
		'period': fields.many2one('account.period', 'Force period'),
		'journal_id': fields.many2one('account.journal', 'Refund Journal', help='You can select here the journal to use for the credit note that will be created. If you leave that field empty, it will use the same journal as the current invoice.'),
		'description': fields.char('Reason', required=True),
		'filter_refund': fields.selection([('refund', 'Create a draft refund'), ('cancel', 'Cancel: create refund and reconcile'),('modify', 'Modify: create refund, reconcile and create a new draft invoice')], "Refund Method", required=True, help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled'),
	}
	
	def _get_journal(self, cr, uid, context=None):
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
		'filter_refund': 'cancel',
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
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
		 To get default values for the object.
		 @param self: The object pointer.
		 @param cr: A database cursor
		 @param uid: ID of the user currently logged in
		 @param fields: List of fields for which we want default values
		 @param context: A standard dictionary
		 @return: A dictionary with default values for all field in ``fields``
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
		
	# Modify to make state done
		pop_up = pick_obj.do_enter_transfer_details(cr, uid, [new_picking], context)
		if pop_up:
			stock_transfer_detail_id = pop_up['res_id']
			stock_transfer_detail_obj = self.pool.get(pop_up['res_model'])
			stock_transfer_detail_obj.do_detailed_transfer(cr, uid, stock_transfer_detail_id)
		
		return new_picking, pick_type_id
	
	def compute_refund(self, cr, uid, ids, mode='refund', context=None):
		inv_obj = self.pool.get('account.invoice')
		account_m_line_obj = self.pool.get('account.move.line')
		mod_obj = self.pool.get('ir.model.data')
		act_obj = self.pool.get('ir.actions.act_window')
		inv_tax_obj = self.pool.get('account.invoice.tax')
		inv_line_obj = self.pool.get('account.invoice.line')
		res_users_obj = self.pool.get('res.users')
		if context is None:
			context = {}
		
		for form in self.browse(cr, uid, ids, mode, context=context):
			created_inv = []
			company = res_users_obj.browse(cr, uid, uid, context=context).company_id
			journal_id = form.journal_id.id
			for inv in inv_obj.browse(cr, uid, context.get('invoice_ids'), context=context):
				if inv.state in ['draft', 'proforma2', 'cancel']:
					raise osv.except_osv(_('Error!'), _('Cannot %s draft/proforma/cancel invoice.') % (mode))
				if inv.reconciled and mode in ('cancel', 'modify'):
					raise osv.except_osv(_('Error!'), _('Cannot %s invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.') % (mode))
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
				
				refund_id = inv_obj.refund(cr, uid, [inv.id], date, period, description, journal_id, context=context)
				refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
				inv_obj.write(cr, uid, [refund.id], {'date_due': date,
					'check_total': inv.check_total})
				inv_obj.button_compute(cr, uid, refund_id)
				
				created_inv.append(refund_id[0])
				if mode in ('cancel', 'modify'):
					movelines = inv.move_id.line_id
					to_reconcile_ids = {}
					for line in movelines:
						if line.account_id.id == inv.account_id.id:
							to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
						if line.reconcile_id:
							line.reconcile_id.unlink()
					refund.signal_workflow('invoice_open')
					refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
					for tmpline in  refund.move_id.line_id:
						if tmpline.account_id.id == inv.account_id.id:
							to_reconcile_ids[tmpline.account_id.id].append(tmpline.id)
					for account in to_reconcile_ids:
						account_m_line_obj.reconcile(cr, uid, to_reconcile_ids[account],
							writeoff_period_id=period,
							writeoff_journal_id = inv.journal_id.id,
							writeoff_acc_id=inv.account_id.id
						)
					if mode == 'modify':
						invoice = inv_obj.read(cr, uid, [inv.id],
							['name', 'type', 'number', 'reference',
								'comment', 'date_due', 'partner_id',
								'partner_insite', 'partner_contact',
								'partner_ref', 'payment_term', 'account_id',
								'currency_id', 'invoice_line', 'tax_line',
								'journal_id', 'period_id'], context=context)
						invoice = invoice[0]
						del invoice['id']
						invoice_lines = inv_line_obj.browse(cr, uid, invoice['invoice_line'], context=context)
						invoice_lines = inv_obj._refund_cleanup_lines(cr, uid, invoice_lines, context=context)
						tax_lines = inv_tax_obj.browse(cr, uid, invoice['tax_line'], context=context)
						tax_lines = inv_obj._refund_cleanup_lines(cr, uid, tax_lines, context=context)
						invoice.update({
							'type': inv.type,
							'date_invoice': date,
							'state': 'draft',
							'number': False,
							'invoice_line': invoice_lines,
							'tax_line': tax_lines,
							'period_id': period,
							'name': description
						})
						for field in ('partner_id', 'account_id', 'currency_id',
						'payment_term', 'journal_id'):
							invoice[field] = invoice[field] and invoice[field][0]
						inv_id = inv_obj.create(cr, uid, invoice, {})
						if inv.payment_term.id:
							data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv.payment_term.id, date)
							if 'value' in data and data['value']:
								inv_obj.write(cr, uid, [inv_id], data['value'])
						created_inv.append(inv_id)
			
			xml_id = (inv.type == 'out_refund') and 'action_invoice_tree1' or \
					 (inv.type == 'in_refund') and 'action_invoice_tree2' or \
					 (inv.type == 'out_invoice') and 'action_invoice_tree3' or \
					 (inv.type == 'in_invoice') and 'action_invoice_tree4'
			result = mod_obj.get_object_reference(cr, uid, 'account', xml_id)
			id = result and result[1] or False
			
			result = act_obj.read(cr, uid, [id], context=context)[0]
			
			invoice_domain = eval(result['domain'])
			invoice_domain.append(('id', 'in', created_inv))
			
			#edit line akun piutang
			return_line = self.read(cr, uid, ids, ['product_return_moves'],context=context)[0]['product_return_moves']
			
			result['domain'] = invoice_domain
			return result
		
	def _create_invoice_refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None):
		new_invoices = []
		inv_obj = self.pool.get('account.invoice')
		for invoice in inv_obj.browse(cr, uid, ids):
			# create the new invoice
			values = self._prepare_refund(invoice, date=date, period_id=period_id,
				description=description, journal_id=journal_id)
			new_invoices += inv_obj.create(values)
		return new_invoices

	def create_returns(self, cr, uid, ids, context=None):
		"""
		 Creates return picking.
		 @param self: The object pointer.
		 @param cr: A database cursor
		 @param uid: ID of the user currently logged in
		 @param ids: List of ids selected
		 @param context: A standard dictionary
		 @return: A dictionary which of fields with values.
		"""
		
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
		data_refund = self.read(cr, uid, ids, ['filter_refund'],context=context)[0]['filter_refund']
		form_customer_refund = self.compute_refund(cr, uid, ids, data_refund, context=context)
		
		return form_customer_refund