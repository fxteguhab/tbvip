from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _

# ==========================================================================================================================

class koreksi_bon(osv.osv_memory):
	_name = 'koreksi.bon'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'sale_order_id': fields.many2one('sale.order', 'Sale Order', required=True,  domain=[('state', '!=', 'cancel')]),
		'order_line': fields.one2many('koreksi.bon.sale.order.line', 'koreksi_bon_id', 'Order Lines'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', readonly=True),
		#'date_order': fields.date('Date Order', readonly=True),
		'date_order': fields.datetime('Date Order', required=True),
		'bon_number': fields.char('Bon Number', readonly=True),
		'partner_id': fields.many2one('res.partner', 'Customer', readonly=True),
		'price_type_id': fields.many2one('price.type', 'Price Type', readonly=True),
		'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),
		'customer_address': fields.char('Customer Address'),
		'shipped_or_taken': fields.selection([
			('shipped', 'Shipped'),
			('taken', 'Taken')
		], 'Shipped or Taken', readonly=True),
		'client_order_ref': fields.char('Reference/Description', readonly=True),
		'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', readonly=True),
		'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position', readonly=True),
		'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', readonly=True),
		
		
		
		'product_return_moves': fields.one2many('koreksi.bon.return.picking.line', 'wizard_id', 'Moves'),
		'move_dest_exists': fields.boolean('Chained Move Exists', readonly=True, help="Technical field used to hide help tooltip if not needed"),
		
	}
	
	def onchange_sale_order_id(self, cr, uid, ids, sale_order_id, context=None):
		if sale_order_id:
			sale_order_obj = self.pool.get('sale.order')
			sale_order_line_obj = self.pool.get('sale.order.line')
			stock_return_picking_obj = self.pool.get('stock.return.picking')
			sale_order = sale_order_obj.browse(cr, uid, sale_order_id)
			order_lines = []
			
			# for picking return
			if len(sale_order.picking_ids.ids) > 1:
				raise osv.except_osv(_('Warning!'), _("This sale order has a return picking, koreksi bon cannot be done."))
			context = dict(context or {})
			context['active_id'] = sale_order.picking_ids.ids[0] if len(sale_order.picking_ids.ids) == 1 else False
			result_default_get = stock_return_picking_obj.default_get(cr, uid, ['product_return_moves', 'move_dest_exists'], context)
			
			for order_line in sale_order.order_line:
				order_lines.append({
					'name': order_line.name,
					'product_id': order_line.product_id.id,
					'price_type_id': order_line.price_type_id.id,
					'product_uom_qty': order_line.product_uom_qty,
					'product_uom': order_line.product_uom.id,
					'price_unit': order_line.price_unit,
					'discount_string': order_line.discount_string,
					'price_subtotal': order_line.price_subtotal,
				})
				
			return {
				'value': {
					'branch_id': sale_order.branch_id.id,
					'date_order': sale_order.date_order,
					'bon_number': sale_order.bon_number,
					'partner_id': sale_order.partner_id.id,
					'price_type_id': sale_order.price_type_id.id,
					'employee_id': sale_order.employee_id.id,
					'shipped_or_taken': sale_order.shipped_or_taken,
					'client_order_ref': sale_order.client_order_ref,
					'pricelist_id': sale_order.pricelist_id,
					'fiscal_position': sale_order.fiscal_position,
					'warehouse_id': sale_order.warehouse_id,
					'order_line': order_lines,
					'product_return_moves': result_default_get.get('product_return_moves', False),
					'move_dest_exists': result_default_get.get('move_dest_exists', False),
				},
			}
		return
	
	def _refund_invoice(self, cr, uid, invoice_ids, context=None):
		"""
		 Fungsi ini didapat dari account_invoice_refund dan dimodifikasi
		 Fungsi ini menggunakan filter_refund = 'cancel'
		"""
		inv_obj = self.pool.get('account.invoice')
		account_m_line_obj = self.pool.get('account.move.line')
		if context is None:
			context = {}
		
		created_inv = []
		for inv in inv_obj.browse(cr, uid, invoice_ids, context=context):
			if inv.state in ['draft', 'proforma2', 'cancel']:
				raise osv.except_osv(_('Error!'), _('Cannot cancel draft/proforma/cancel invoice.'))
			# Ko teguh pengen ketika sudah di reconciled juga dapat di retur, tetapi invoice yang sudah paid atau dibayar sebagian tidak dapat di cancel
			# Dengan demikian pengecekan raise di comment, tidak tau apakah effect buruknya, karena diliat dari journal saldo tetap balance
			# if inv.reconciled:
			# 	raise osv.except_osv(_('Error!'), _('Cannot cancel invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.'))

			period = inv.period_id and inv.period_id.id or False
			journal_id = inv.journal_id.id
			date = inv.date_invoice
			description = "Koreksi Bon " + inv.name
			
			if not period:
				raise osv.except_osv(_('Insufficient Data!'), \
					_('No period found on the invoice.'))
			
			#  Bikin Invoice refund
			refund_id = inv_obj.refund(cr, uid, [inv.id], date, period, description, journal_id, context=context)
			refund = inv_obj.browse(cr, uid, refund_id[0], context=context)
			inv_obj.write(cr, uid, [refund.id], {'date_due': date,
				'check_total': inv.check_total})
			inv_obj.button_compute(cr, uid, refund_id)
			
			created_inv.append(refund_id[0])
			movelines = inv.move_id.line_id
			to_reconcile_ids = {}
			
			for line in movelines:
				if line.account_id.id == inv.account_id.id:
					to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
				if line.reconcile_id:
					line.reconcile_id.unlink()
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

			#### revoke journal untuk kas laci#######################################################################
			journal_entry_obj = self.pool.get('account.move')
			journal_obj = self.pool.get('account.journal')
			user_obj = self.pool.get('res.users')
			cashier = user_obj.browse(cr, uid, uid)

			branch_id = cashier.branch_id.id
			branch_data = self.pool['tbvip.branch'].browse(cr,uid,branch_id)
			branch_employee = branch_data.employee_list
			journal_retur_id = None
			for employee in branch_employee:
				if employee.user_id.id == uid:
					journal_retur_id =  employee.default_journal_sales_retur_override.id
			'''
			if cashier.default_journal_sales_override:
				journal_retur_id = cashier.default_journal_sales_retur_override.id
			elif cashier.branch_id.default_journal_sales_retur:
				journal_retur_id = cashier.branch_id.default_journal_sales_retur.id
			'''

			journal_retur =  journal_obj.browse(cr, uid, journal_retur_id, context=context)
			name = 'REVOKE '+inv.name
			entry_data = journal_entry_obj.account_move_prepare(cr, uid, journal_retur.id, date=date, ref=name)
			entry_data['line_id'] = [
				[0,False,{
					'name': name, 
					'account_id': journal_retur.default_credit_account_id.id,
					'credit': inv.amount_total, #vals.get('amount', 0),
					'debit': 0,
					'partner_id' : cashier.partner_id.id,
				}],
				[0,False,{
					'name': name, 
					'account_id': journal_retur.default_debit_account_id.id, 
					'debit': inv.amount_total, 
					'credit': 0,
					'partner_id' : inv.commercial_partner_id.id,
				}],
			]

			new_entry_id = journal_entry_obj.create(cr, uid, entry_data, context=context)
			journal_entry_obj.post(cr, uid, [new_entry_id], context=context)
			
			inv_obj.write(cr, uid, invoice_ids, {
				'state': 'cancel'
			}, context=context)
			return
	
	def action_save_koreksi_bon(self, cr, uid, ids, context=None):
		sale_order_obj = self.pool.get('sale.order')
		koreksi_bon_log_obj = self.pool.get('koreksi.bon.log')
		account_invoice_cancel_obj = self.pool.get('account.invoice.cancel')
		stock_picking_obj = self.pool.get('stock.picking')
		stock_return_picking_obj = self.pool.get('stock.return.picking')
		for koreksi_bon in self.browse(cr, uid, ids):
			# copy SO lines
			order_lines = []
			for order_line in koreksi_bon.order_line:
				order_lines.append([0, False,{
					'name': order_line.name,
					'product_id': order_line.product_id.id,
					'price_type_id': order_line.price_type_id.id,
					'product_uom_qty': order_line.product_uom_qty,
					'product_uom': order_line.product_uom.id,
					'price_unit': order_line.price_unit,
					'discount_string': order_line.discount_string,
					'price_subtotal': order_line.price_subtotal,
				}])
			
			sale_order = sale_order_obj.browse(cr, uid, koreksi_bon.sale_order_id.id)
			total_paid = sale_order.payment_transfer_amount + \
						 sale_order.payment_cash_amount + \
						 sale_order.payment_receivable_amount + \
						 sale_order.payment_giro_amount
			
			
			# cancel invoice
			# invoice yang sudah lunas atau dibayar sebagian tidak dapat di cancel, jika demikian maka lakukan refund invoice
			if total_paid==0:
				account_invoice_cancel_obj.invoice_cancel(cr, uid, [], context={'active_ids':sale_order.invoice_ids.ids})
			else:
				self._refund_invoice(cr, uid, sale_order.invoice_ids.ids, context)
			
			# cancel picking
			# action_cancel cannot be used because stock picking state is done, instead create return stock picking
			# stock_picking_obj.action_cancel(cr, uid, sale_order.picking_ids.ids)
			if len(sale_order.picking_ids.ids) > 1:
				raise osv.except_osv(_('Warning!'), _("This sale order has a return picking, koreksi bon cannot be done."))
			if len(sale_order.picking_ids.ids) == 1:
				context = dict(context or {})
				context['active_id'] = sale_order.picking_ids.ids[0]
				new_picking, picking_type_id = self._create_returns(cr, uid, [koreksi_bon.id], context)
				
			# cancel SO
			# sale_order_obj.action_cancel(cr, uid, sale_order.id, context)
			sale_order_obj.write(cr, uid, koreksi_bon.sale_order_id.id, {
				'state': 'cancel'
			}, context=context)
			
			# create new SO
			new_sale_order_id = sale_order_obj.create(cr, uid, {
				'name': 'Koreksi ' + koreksi_bon.sale_order_id.name,
				'branch_id': koreksi_bon.sale_order_id.branch_id.id,
				'date_order': koreksi_bon.date_order,
				'bon_number': koreksi_bon.sale_order_id.bon_number,
				'partner_id': koreksi_bon.sale_order_id.partner_id.id,
				'price_type_id': koreksi_bon.sale_order_id.price_type_id.id,
				'employee_id': koreksi_bon.sale_order_id.employee_id.id,
				'shipped_or_taken': koreksi_bon.sale_order_id.shipped_or_taken,
				'client_order_ref': koreksi_bon.sale_order_id.client_order_ref,
				'pricelist_id': koreksi_bon.sale_order_id.pricelist_id.id,
				'customer_address': koreksi_bon.sale_order_id.customer_address,
				'order_line': order_lines,
			})
			
			# create koreksi bon log
			koreksi_bon_log_obj.create(cr, uid, {
				'old_sale_order_id': koreksi_bon.sale_order_id.id,
				'new_sale_order_id': new_sale_order_id
			})
		return new_sale_order_id
	
	# copied from stock_return_picking, auto transfer
	def _create_returns(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		record_id = context and context.get('active_id', False) or False
		move_obj = self.pool.get('stock.move')
		pick_obj = self.pool.get('stock.picking')
		uom_obj = self.pool.get('product.uom')
		data_obj = self.pool.get('koreksi.bon.return.picking.line')
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
		
		pop_up = pick_obj.do_enter_transfer_details(cr, uid, [new_picking], context)
		if pop_up:
			stock_transfer_detail_id = pop_up['res_id']
			stock_transfer_detail_obj = self.pool.get(pop_up['res_model'])
			stock_transfer_detail_obj.do_detailed_transfer(cr, uid, stock_transfer_detail_id)
		
		return new_picking, pick_type_id

# class sale_order_line(osv.osv):
# 	_inherit = 'sale.order.line'
#
# # COLUMNS ------------------------------------------------------------------------------------------------------------------
#
# 	_columns = {
# 		'koreksi_bon_id': fields.many2one('koreksi.bon', 'Koreksi Bon'),
# 	}

class koreksi_bon_log(osv.osv):
	_name = 'koreksi.bon.log'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'old_sale_order_id': fields.many2one('sale.order', 'Old Sale Order', required=True),
		'new_sale_order_id': fields.many2one('sale.order', 'New Sale Order', required=True),
	}


class koreksi_bon_sale_order_line(osv.osv_memory):
	_name = "koreksi.bon.sale.order.line"
	
	_columns = {
		'koreksi_bon_id': fields.many2one('koreksi.bon', string="Koreksi Bon"),
		'name': fields.text('Description', required=True),
		'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True, change_default=True, ondelete='restrict'),
		'price_type_id': fields.many2one('price.type', 'Price Type', required=True),
		'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Product UoS'), required=True),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True),
		'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price')),
		'discount_string': fields.char('Discount'),
		'price_subtotal': fields.float('Subtotal', digits_compute=dp.get_precision('Account')),
		
		'product_uos_qty': fields.float('Quantity (UoS)', digits_compute= dp.get_precision('Product UoS')),
		'product_packaging': fields.many2one('product.packaging', 'Packaging'),
	}
	
	_defaults = {
		'product_uom_qty': 1.0,
	}
	
	def onchange_product_id_tbvip(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,
			warehouse_id=False, parent_price_type_id=False, price_type_id=False, sale_order_id=None, context=None):
		return self.pool.get('sale.order.line').onchange_product_id_tbvip(cr, uid, ids, pricelist, product, qty, uom,
			qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id,
			parent_price_type_id, price_type_id, sale_order_id, context)
	
	def onchange_product_uom_qty_tbvip(self, cr, uid, ids, pricelist, product, qty=0, uom=False, qty_uos=0, uos=False,
			name='', partner_id=False, lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False,
			flag=False, warehouse_id=False, price_unit=False, discount_string=False, context=None):
		return self.pool.get('sale.order.line').onchange_product_uom_qty_tbvip(cr, uid, ids, pricelist, product, qty, uom,
			qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id,
			price_unit, discount_string, context)
	
	def onchange_product_tbvip(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,
			warehouse_id=False, parent_price_type_id=False, price_type_id=False, context=None):
		return self.pool.get('sale.order.line').onchange_product_tbvip(cr, uid, ids, pricelist, product, qty, uom, qty_uos,
			uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id,
			parent_price_type_id, price_type_id, context)
	
	def onchange_order_line(self, cr, uid, ids, product_qty, price_unit, product_uom, product_id, discount_string, context={}):
		return self.pool.get('sale.order.line').onchange_order_line(cr, uid, ids, product_qty, price_unit, product_uom, product_id, discount_string, context)


class koreksi_bon_return_picking_line(osv.osv_memory):
	_name = "koreksi.bon.return.picking.line"
	_rec_name = 'product_id'
	
	_columns = {
		'product_id': fields.many2one('product.product', string="Product", required=True),
		'quantity': fields.float("Quantity", digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
		'wizard_id': fields.many2one('koreksi.bon', string="Wizard"),
		'move_id': fields.many2one('stock.move', "Move"),
		'lot_id': fields.many2one('stock.production.lot', 'Serial Number', help="Used to choose the lot/serial number of the product returned"),
	}