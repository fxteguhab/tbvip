from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

_DEMAND_TYPE = [
	('interbranch', 'Interbranch'),
	('different_management', 'Different Management'),
]

_DEMAND_STATE = [
	('requested', 'Requested'),
	('waiting_for_supplier', 'Waiting for Supplier'),
	('ready_for_transfer', 'Ready for Transfer'),
	('canceled', 'Canceled'),
]

_DEMAND_FULFILLMENT = [
	('requested', 'Requested'),
	('partially_fulfilled', 'Partially Fulfilled'),
	('fulfilled', 'Fulfilled'),
]

# ==========================================================================================================================

class tbvip_demand(osv.osv):
	_name = "tbvip.demand"
	_description = "Demand"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'request_date': fields.date('Request Date', required=True, help='Request date.'),
		'demand_type': fields.selection(_DEMAND_TYPE, 'Demand Type',
			help='Whether this demand is inter branches in the same management or in different managements.'),
		'state': fields.selection(_DEMAND_FULFILLMENT, 'Demand State', required=True),
		'target_branch_id': fields.many2one('tbvip.branch', 'Targeted Branch', required=True,
			help='Which branch this demand is requested to.'),
		'requestor_branch_id': fields.many2one('tbvip.branch', 'Requestor Branch', required=[('demand_type','=','interbranch')],
			help='Which branch requested this demand.'),
		'demand_line_ids': fields.one2many('tbvip.demand.line', 'demand_id', 'Demand Lines'),
	}
	
	_defaults = {
		'request_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'demand_type': 'interbranch',
		'state': 'requested',
		'requestor_branch_id': lambda self, cr, uid, ctx: 1,
	}

# OVERRIDES ----------------------------------------------------------------------------------------------------------------





# ==========================================================================================================================

class tbvip_demand_line(osv.osv):
	_name = "tbvip.demand.line"
	_description = "Detail Demand"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	def _request_date(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for line in self.browse(cr, uid, ids, context=context):
			result[line.id] = line.demand_id.request_date
		return result
	
	_columns = {
		'demand_id': fields.many2one('tbvip.demand', 'Demand'),
		'request_date': fields.function(_request_date, string="Total Amount Reconciled", type='date', store=True),
		'response_date': fields.datetime('User Respond Time'),
		'demand_type': fields.selection(_DEMAND_TYPE, 'Demand Type',
			help='Whether this demand is inter branches in the same management or in different managements.'),
		'state': fields.selection(_DEMAND_STATE, 'Demand Line State', required=True),
		'stock_move_id': fields.many2one('stock.move', 'Stock Move', ondelete="set null",
			help='Is set if demand type is interbranch and state is Ready for Transfer.'),
		'sale_order_line_id': fields.many2one('sale.order.line', 'Sale Order Line', ondelete="set null",
			help='Is set if demand type is different_management and state is Ready for Transfer.'),
		'purchase_order_line_id': fields.many2one('purchase.order.line', 'Purchase Order Line', ondelete="set null",
			help='Is set if state is Waiting for Supplier.'),
		'cancel_reason': fields.text('Cancel Reason'),
		'cancel_by': fields.many2one('res.users', 'Canceled By'),
		'cancel_time': fields.datetime('Canceled Time'),
		'demand_line_ids': fields.one2many('tbvip.demand.line', 'demand_id', 'Demand Lines'),
		'product_id': fields.many2one('product.product', 'Product', required=True, help="Demanded product."),
		'qty': fields.float('Quantity'),
		'uom_id': fields.many2one('product.uom', 'Product UoM'),
	}
	
	_defaults = {
		'demand_type': 'interbranch',
		'state': 'requested',
	}
	
# METHODS ------------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		return {'value': {'uom_id': product.product_tmpl_id.uom_id.id},
				'domain': {'uom_id': [('category_id','=', product.product_tmpl_id.uom_id.category_id.id)]}}
	
	
	# ACTIONS ------------------------------------------------------------------------------------------------------------------
	
	def action_set_wait(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {
			'state': 'waiting_for_supplier',
		})
		return True
	
	def action_set_ready(self, cr, uid, ids, context=None):
		for id in ids:
			demand = self.browse(cr, uid, id)
			if demand.demand_type == 'interbranch':
				# create stock move, set to available
				stock_move_obj = self.pool.get('stock.move')
				stock_move_ids = []
				for demand_line in demand.demand_line_ids:
					stock_move_ids.append(stock_move_obj.create(cr, uid, {
						'demand_id': id,
						'product_id': demand_line.product_id.id,
						'product_uom': demand_line.uom_id.id,
						'product_uom_qty': demand_line.qty,
						'name': 'From demand',
						'location_id': 1,
						'location_dest_id': 1,
					}))
				stock_move_obj.force_assign(cr, uid, stock_move_ids)
				self.write(cr, uid, id, {
					'state': 'ready_for_transfer',
				})
			elif demand.demand_type == 'different_management':
				# create sales order, set to confirm
				sale_order_obj = self.pool.get('sale.order')
				order_lines = []
				for demand_line in demand.demand_line_ids:
					order_lines.append((0, False, {
						'product_id': demand_line.product_id.id,
						'product_uom': demand_line.uom_id.id,
						'product_uom_qty': demand_line.qty,
					}))
				sale_order_line_id = sale_order_obj.create(cr, uid, {
					'partner_id': uid,
					'date_order': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
					'order_line': order_lines,
				})
				sale_order_obj.action_button_confirm(cr, uid, [sale_order_line_id])
				self.write(cr, uid, id, {
					'state': 'ready_for_transfer',
					'sale_order_line_id': sale_order_line_id,
				})
		return True

# ---------------------------------------------------------------------------------------------------------------------------

class stock_opname_memory(osv.osv_memory):
	_name = "tbvip.demand.memory"
	_description = "Demand Memory"
	
	_columns = {
		'cancel_reason': fields.text('Cancel Reason'),
	}
	
	def action_cancel(self, cr, uid, ids, context=None):
		demand_obj = self.pool.get('tbvip.demand')
		for demand_memory in self.browse(cr, uid, ids):
			demand_obj.write(cr, uid, context['active_id'], {
				'state': 'canceled',
				'cancel_reason': demand_memory.cancel_reason,
				'cancel_by': uid,
				'cancel_time': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
			})
		return True