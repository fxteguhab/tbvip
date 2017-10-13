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
		'sale_order_id': fields.many2one('sale.order', 'Sale Order', required=True),
		'order_line': fields.one2many('koreksi.bon.sale.order.line', 'koreksi_bon_id', 'Order Lines'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', readonly=True),
		'date_order': fields.date('Date Order', readonly=True),
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
	
	def action_save_koreksi_bon(self, cr, uid, ids, context=None):
		sale_order_obj = self.pool.get('sale.order')
		koreksi_bon_log_obj = self.pool.get('koreksi.bon.log')
		account_invoice_cancel_obj = self.pool.get('account.invoice.cancel')
		stock_picking_obj = self.pool.get('stock.picking')
		stock_return_picking_obj = self.pool.get('stock.return.picking')
		for koreksi_bon in self.browse(cr, uid, ids):
			# copy SO lines
			order_lines = []
			for order_line in koreksi_bon.sale_order_id.order_line:
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
			# cancel invoice
			# invoice cannot be canceled if paid, instead ???????????????
			account_invoice_cancel_obj.invoice_cancel(cr, uid, sale_order.invoice_ids.ids)
			# cancel picking
			# action_cancel cannot be used because stock picking state is done, instead create return stock picking
			# stock_picking_obj.action_cancel(cr, uid, sale_order.picking_ids.ids)
			if len(sale_order.picking_ids.ids) > 1:
				raise osv.except_osv(_('Warning!'), _("This sale order has a return picking, koreksi bon cannot be done."))
			context = dict(context or {})
			context['active_id'] = sale_order.picking_ids.ids[0] if len(sale_order.picking_ids.ids) == 1 else False
			new_picking, picking_type_id = self._create_returns(cr, uid, [koreksi_bon.id], context)
			# cancel SO
			sale_order_obj.action_cancel(cr, uid, sale_order.id, context)
			
			# create new SO
			new_sale_order_id = sale_order_obj.create(cr, uid, {
				'name': 'Koreksi ' + koreksi_bon.sale_order_id.name,
				'branch_id': koreksi_bon.sale_order_id.branch_id.id,
				'date_order': koreksi_bon.sale_order_id.date_order,
				'bon_number': koreksi_bon.sale_order_id.bon_number,
				'partner_id': koreksi_bon.sale_order_id.partner_id.id,
				'price_type_id': koreksi_bon.sale_order_id.price_type_id.id,
				'employee_id': koreksi_bon.sale_order_id.employee_id.id,
				'shipped_or_taken': koreksi_bon.sale_order_id.shipped_or_taken,
				'client_order_ref': koreksi_bon.sale_order_id.client_order_ref,
				'pricelist_id': koreksi_bon.sale_order_id.pricelist_id,
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
		data_obj = self.pool.get('stock.return.picking.line')
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
	
	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
		return self.pool.get('sale.order.line')._amount_line(cr, uid, ids, field_name, arg, context)
	
	_columns = {
		'koreksi_bon_id': fields.many2one('koreksi.bon', string="Koreksi Bon"),
		'name': fields.text('Description', required=True),
		'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True, change_default=True, ondelete='restrict'),
		'price_type_id': fields.many2one('price.type', 'Price Type', required=True),
		'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Product UoS'), required=True),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True),
		'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price')),
		'discount_string': fields.char('Discount'),
		'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute=dp.get_precision('Account')),
		
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