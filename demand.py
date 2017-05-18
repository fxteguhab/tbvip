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

# ==========================================================================================================================

class tbvip_demand(osv.osv):
	_name = "tbvip.demand"
	_description = "Demand"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'request_date': fields.date('Request Date', required=True, help='Request date.'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True, help='Which branch this demand is requested to.'),
		'demand_type': fields.selection(_DEMAND_TYPE, 'Demand Type',
			help='Whether this demand is inter branches in the same management or in different managements.'),
		'state': fields.selection(_DEMAND_STATE, 'Demand State', required=True),
		'stock_move_id': fields.many2one('stock.move', 'Stock Move',
			help='Is set if demand type is interbranch and state is Ready for Transfer.'),
		'sale_order_id': fields.many2one('sale.order', 'Sale Order',
			help='Is set if demand type is different_management and state is Ready for Transfer.'),
		'cancel_reason': fields.text('Cancel Reason'),
		'cancel_by': fields.many2one('res.users', 'Canceled By'),
		'cancel_time': fields.datetime('Canceled Time'),
		'demand_line_ids': fields.one2many('tbvip.demand.line', 'demand_id', 'Demand Lines'),
	}
	
	_defaults = {
		'request_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'demand_type': 'interbranch',
		'state': 'requested',
	}

# OVERRIDES ----------------------------------------------------------------------------------------------------------------



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
				sale_order_id = sale_order_obj.create(cr, uid, {
					'partner_id': uid,
					'date_order': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
					'order_line': order_lines,
				})
				sale_order_obj.action_button_confirm(cr, uid, [sale_order_id])
				self.write(cr, uid, id, {
					'state': 'ready_for_transfer',
					'sale_order_id': sale_order_id,
				})
		return True
	
	def action_cancel(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {
			'state': 'canceled',
			'cancel_reason': 1,
			'cancel_by': uid,
			'cancel_time': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		})
		return True


# ==========================================================================================================================

class tbvip_demand_line(osv.osv):
	_name = "tbvip.demand.line"
	_description = "Detail Demand"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'demand_id': fields.many2one('tbvip.demand', 'Demand'),
		'product_id': fields.many2one('product.product', 'Product', required=True, help="Demanded product."),
		'qty': fields.float('Quantity'),
		'uom_id': fields.many2one('product.uom', 'Product UoM'),
	}
	
# METHODS ------------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		return {'value': {'uom_id': product.product_tmpl_id.uom_id.id},
				'domain': {'uom_id': [('category_id','=', product.product_tmpl_id.uom_id.category_id.id)]}}