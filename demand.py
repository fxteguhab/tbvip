from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
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

_RESPONSE_TYPE = [
	('buy_from_supplier', 'Buy from Supplier'),
	('fulfill', 'Fulfill'),
	('cannot_provide', 'Cannot Provide'),
]

# ==========================================================================================================================

class tbvip_demand(osv.osv):
	_name = "tbvip.demand"
	_description = "Demand"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'request_date': fields.datetime('Request Date', required=True, help='Request date.'),
		'demand_type': fields.selection(_DEMAND_TYPE, 'Demand Type', required=True,
			help='Whether this demand is inter branches in the same management or in different managements.'),
		'state': fields.selection(_DEMAND_FULFILLMENT, 'Demand State', required=True),
		'target_branch_id': fields.many2one('tbvip.branch', 'Targeted Branch', required=True,
			help='Which branch this demand is requested to.'),
		'requester_branch_id': fields.many2one('tbvip.branch', 'Requester Branch',
			help='Which branch requested this demand.'),
		'demand_line_ids': fields.one2many('tbvip.demand.line', 'demand_id', 'Demand Lines'),
	}
	
# DEFAULTS ------------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'request_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'demand_type': 'interbranch',
		'state': 'requested',
		'requester_branch_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, [uid]).branch_id,
	}
	
# CONSTRAINTS ---------------------------------------------------------------------------------------------------------------
	
	def _check_user_assigned_to_branch(self, cr, uid, ids, context=None):
		users_obj = self.pool.get('res.users')
		user_branch_id = users_obj.browse(cr, uid, [uid], context).branch_id
		for demand in self.browse(cr, uid, ids, context):
			if demand.demand_type == 'interbranch' and not user_branch_id:
				return False
		return True
	
	_constraints = [
		(_check_user_assigned_to_branch, _('You must be assigned to a branch.'), ['demand_type']),
	]

# OVERRIDES -----------------------------------------------------------------------------------------------------------------

	def name_get(self, cr, uid, ids, context=None):
		result = []
		for demand in self.browse(cr, uid, ids, context):
			result.append((
				demand.id,
				demand.request_date + ' | ' + demand.target_branch_id.name + ' - ' + demand.requester_branch_id.name
			))
		return result

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
	
	def _demand_type(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for line in self.browse(cr, uid, ids, context=context):
			result[line.id] = line.demand_id.demand_type
		return result
	
	_columns = {
		'demand_id': fields.many2one('tbvip.demand', 'Demand', required=True),
		'request_date': fields.function(_request_date, string="Total Amount Reconciled", type='datetime', store=True),
		'response_date': fields.datetime('User Respond Time'),
		'demand_type': fields.function(_demand_type, string="Demand Type", type='selection', selection=_DEMAND_TYPE, store=True),
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
		'state': 'requested',
	}
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def write(self, cr, uid, ids, vals, context=None):
		if vals.get('state', False):
			if vals['state'] == 'requested':
				vals['stock_move_id'] = None
				vals['sale_order_line_id'] = None
				vals['purchase_order_line_id'] = None
		result = super(tbvip_demand_line, self).write(cr, uid, ids, vals, context)
		if vals.get('state', False):
			demand_obj = self.pool.get('tbvip.demand')
			for demand_line in self.browse(cr, uid, ids):
				counter = 0
				for line in demand_line.demand_id.demand_line_ids:
					if line.state == 'ready_for_transfer' or line.state == 'canceled':
						counter += 1
				if counter == len(demand_line.demand_id.demand_line_ids):
					demand_obj.write(cr, uid, demand_line.demand_id.id, { 'state': 'fulfilled' })
				elif counter == 0:
					demand_obj.write(cr, uid, demand_line.demand_id.id, { 'state': 'requested' })
				else:
					demand_obj.write(cr, uid, demand_line.demand_id.id, { 'state': 'partially_fulfilled' })
		return result
	
	def name_get(self, cr, uid, ids, context=None):
		result = []
		for demand in self.browse(cr, uid, ids, context):
			result.append((
				demand.id,
				demand.product_id.name
			))
		return result
	
# ONCHANGE ------------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		return {'value': {'uom_id': product.product_tmpl_id.uom_id.id},
				'domain': {'uom_id': [('category_id','=', product.product_tmpl_id.uom_id.category_id.id)]}}
	
# METHODS -------------------------------------------------------------------------------------------------------------------
	
	def cancel_demand_lines(self, cr, uid, line_ids, cancel_reason, context=None):
		self.write(cr, uid, line_ids, {
			'state': 'canceled',
			'cancel_reason': cancel_reason,
			'cancel_by': uid,
			'cancel_time': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		})
	
	def ready_demand_lines(self, cr, uid, line_ids, context=None):
		for line in self.browse(cr, uid, line_ids):
			demand = line.demand_id
			if demand.demand_type == 'interbranch':
				# create stock move, set to available
				stock_move_obj = self.pool.get('stock.move')
				stock_location_obj = self.pool.get('stock.location')
				requester_location_ids = stock_location_obj.search(cr, uid, [('branch_id','=',demand.requester_branch_id.id)])
				target_location_ids = stock_location_obj.search(cr, uid, [('branch_id','=',demand.target_branch_id.id)])
				stock_move_id = stock_move_obj.create(cr, uid, {
					'product_id': line.product_id.id,
					'product_uom': line.uom_id.id,
					'product_uom_qty': line.qty,
					'name': 'Demand from ' + demand.requester_branch_id.name + ' at ' + demand.request_date,
					'location_id': requester_location_ids[0],
					'location_dest_id': target_location_ids[0],
				})
				stock_move_obj.force_assign(cr, uid, stock_move_id)
				self.write(cr, uid, line.id, {
					'state': 'ready_for_transfer',
					'stock_move_id': stock_move_id,
				})
			elif demand.demand_type == 'different_management':
				# create sales order, set to confirm
				sale_order_obj = self.pool.get('sale.order')
				order_lines = [(0, False, {
					'name': 'Demand from ' + demand.requester_branch_id.name + ' at ' + demand.request_date,
					'product_id': line.product_id.id,
					'product_uom': line.uom_id.id,
					'product_uom_qty': line.qty,
				})]
				sale_order_id = sale_order_obj.create(cr, uid, {
					'partner_id': uid,
					'date_order': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
					'order_line': order_lines,
				})
				sale_order_obj.action_button_confirm(cr, uid, [sale_order_id])
				sale_order = sale_order_obj.browse(cr, uid, sale_order_id)
				self.write(cr, uid, line.id, {
					'state': 'ready_for_transfer',
					'sale_order_line_id': sale_order.order_line[0].id,
				})
	
	def wait_demand_lines(self, cr, uid, line_ids, context=None):
		# bikin po belom, tambahin juga di linenya tanda kalo ini dari demand atau bukan
		if context is None:
			context = {}
		po_obj = self.pool.get('purchase.order')
		stock_location_obj = self.pool.get('stock.location')
		suppliers_products = {}	# dictionary of partner_id: order_lines
		branch_id = 0
		for line in self.browse(cr, uid, line_ids):
			branch_id = line.demand_id.target_branch_id.id
			if len(line.product_id.seller_ids) == 0:
				raise osv.except_osv(_('Error!'), _("Make sure every product have at least one supplier"))
			else:
				partner_id = line.product_id.seller_ids[0].name.id
				products = suppliers_products[partner_id] if suppliers_products.get(partner_id, False) else []
				products.append((0, False, {
					'product_id': line.product_id.id,
					'name': line.product_id.name,
					'product_qty': line.qty,
					'product_uom': line.uom_id.id,
					'price_unit': line.product_id.standard_price,
					'is_from_demand': True,
					'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
				}))
				suppliers_products[partner_id] = products
		for supplier, products in suppliers_products.iteritems():
			target_location_ids = stock_location_obj.search(cr, uid, [('branch_id','=',line.demand_id.target_branch_id.id)])
			po_obj.create(cr, uid, {
				'branch_id': branch_id,
				'partner_id': supplier,
				'date_order': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
				'picking_type_id': self._get_picking_in(cr, uid, context),
				'location_id': target_location_ids[0],
				'invoice_method': 'order',
				'order_line': products,
				'pricelist_id': self.pool.get('res.partner').browse(cr, uid, supplier).property_product_pricelist_purchase.id,
			}, context)
			self.write(cr, uid, line.id, {
				'state': 'waiting_for_supplier',
			})
	
	def _get_picking_in(self, cr, uid, context=None):
		obj_data = self.pool.get('ir.model.data')
		type_obj = self.pool.get('stock.picking.type')
		user_obj = self.pool.get('res.users')
		company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
		types = type_obj.search(cr, uid, [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)], context=context)
		if not types:
			types = type_obj.search(cr, uid, [('code', '=', 'incoming'), ('warehouse_id', '=', False)], context=context)
			if not types:
				raise osv.except_osv(_('Error!'), _("Make sure you have at least an incoming picking type defined"))
		return types[0]
# ===========================================================================================================================

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
	
# ===========================================================================================================================


class tbvip_demand_respond_memory(osv.osv_memory):
	_name = "tbvip.demand.respond.memory"
	_description = "Demand Respond"
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'response_date': fields.datetime('Response Date', required=True),
		'response_type': fields.selection(_RESPONSE_TYPE, 'Response Type', required=True),
		'cancel_reason': fields.text('Cancel Reason'),
		'respond_line': fields.one2many('tbvip.demand.respond.line.memory', 'header_id', 'Respond Line'),
	}
	
	# DEFAULTS --------------------------------------------------------------------------------------------------------------
	
	def _respond_line(self, cr, uid, context=None):
		result = []
		active_model = context.get('active_model')
		if active_model == 'tbvip.demand.line':
			demand_line_obj = self.pool.get('tbvip.demand.line')
			for line in demand_line_obj.browse(cr, uid, context.get('active_ids')):
				if line.state == 'requested':
					result.append((0, False, {
						'demand_line_id': line.id,
						'product_id': line.product_id,
						'qty': line.qty,
						'uom_id': line.uom_id,
					}))
		elif active_model == 'tbvip.demand':
			demand_line_obj = self.pool.get('tbvip.demand')
			for demand in demand_line_obj.browse(cr, uid, context.get('active_ids')):
				for line in demand.demand_line_ids:
					if line.state == 'requested':
						result.append((0, False, {
							'demand_line_id': line.id,
							'product_id': line.product_id,
							'qty': line.qty,
							'uom_id': line.uom_id,
						}))
		return result
	
	_defaults = {
		'response_date': lambda cr, uid, ids, context=None: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'respond_line': _respond_line,
	}
	
	def action_execute_response(self, cr, uid, ids, context=None):
		demand_line_obj = self.pool.get('tbvip.demand.line')
		for memory in self.browse(cr, uid, ids, context):
			line_ids = []
			for line in memory.respond_line:
				if line.demand_line_id.state == 'requested':
					line_ids.append(line.demand_line_id.id)
			if memory.response_type == 'buy_from_supplier':
				demand_line_obj.wait_demand_lines(cr, uid, line_ids, context=None)
			elif memory.response_type == 'fulfill':
				demand_line_obj.ready_demand_lines(cr, uid, line_ids, context=None)
			elif memory.response_type == 'cannot_provide':
				demand_line_obj.cancel_demand_lines(cr, uid, line_ids, memory.cancel_reason, context=None)
			else:
				pass
		return True
	
# ===========================================================================================================================


class tbvip_demand_respond_line_memory(osv.osv_memory):
	_name = "tbvip.demand.respond.line.memory"
	_description = "Demand Respond Line"
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'header_id': fields.many2one('tbvip.demand.respond.memory', 'Demand Respond'),
		'demand_line_id': fields.many2one('tbvip.demand.line', 'Demand Line'),
		'product_id': fields.many2one('product.product', 'Product'),
		'qty': fields.float('Quantity'),
		'uom_id': fields.many2one('product.uom', 'UoM ID'),
	}