from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta
from openerp.osv.orm import browse_record_list, browse_record, browse_null
from openerp.tools.float_utils import float_compare, float_is_zero
from openerp import tools

import openerp.addons.purchase_sale_discount as psd
import openerp.addons.sale as imported_sale
import openerp.addons.portal_sale as imported_portal_sale
import openerp.addons.sale_stock as imported_sale_stock
import openerp.addons.purchase_sale_discount as imported_purchase_sale_discount
import openerp.addons.sale_multiple_payment as imported_sale_multiple_payment
import openerp.addons.product_custom_conversion as imported_product_custom_conversion
import openerp.addons.chjs_price_list as imported_price_list
import openerp.addons.decimal_precision as dp

# ==========================================================================================================================

class purchase_order(osv.osv):
	_inherit = 'purchase.order'
	
	# FIELD FUNCTION METHODS ------------------------------------------------------------------------------------------------
	
	def _alert(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for data in self.browse(cr, uid, ids):
			max_alert = -1
			for line in data.order_line:
				max_alert = max(max_alert, line.alert)
			result[data.id] = max_alert
		return result
	
	def _default_partner_id(self, cr, uid, context={}):
		model, general_supplier_id = self.pool['ir.model.data'].get_object_reference(
			cr, uid, 'tbvip', 'tbvip_supplier_general')
		return general_supplier_id
	
	def _default_branch_id(self, cr, uid, context={}):
		# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.id or None
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_purchase_id': fields.integer('MySQL Purchase ID'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True,
			states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)],
				'done': [('readonly', True)]}),
		'cashier': fields.char('Cashier'),
		'alert': fields.function(_alert, method=True, type='integer', string="Alert", store=True),
		'adm_point': fields.float('Adm. Point'),
		'pickup_vehicle_id': fields.many2one('fleet.vehicle', 'Pickup Vehicle'),
		'driver_id': fields.many2one('hr.employee', 'Pickup Driver'),
		'partner_ref': fields.char('Supplier Reference', states={},
			copy=False, track_visibility='always',
			help="Reference of the sales order or bid sent by your supplier. "
				 "It's mainly used to do the matching when you receive the "
				 "products as this reference is usually written on the "
				 "delivery order sent by your supplier.", ),
		'date_order': fields.datetime('Order Date', required=True, states={'confirmed': [('readonly', True)],
			'approved': [('readonly', True)]},
			select=True, copy=False, track_visibility='always',
			help="Depicts the date where the Quotation should be validated and "
				 "converted into a Purchase Order, by default it's the creation date.", ),
		'shipped_or_taken': fields.selection([
			('shipped', 'Shipped'),
			('taken', 'Taken')
		], 'Shipped or Taken'),
		'delivered_date': fields.datetime('Delivered Date', required=True),
		'description' :fields.char('Description'),

	}
	
	_defaults = {
		# 'partner_id': _default_partner_id,
		'delivered_date': lambda *a: (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
		'branch_id': _default_branch_id,
		'shipped_or_taken': 'shipped',
		'payment_term_id': lambda self, cr, uid, ctx=None: self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'account_payment_term_net')[1],
	}
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	#def create(self, cr, uid, vals, context={}):
	#	new_id = super(purchase_order, self).create(cr, uid, vals, context=context)
	#	
	#	# langsung confirm purchasenya bila diinginkan. otomatis dia bikin satu invoice dan satu incoming goods
	#	if context.get('direct_confirm', False):
	#		purchase_data = self.browse(cr, uid, new_id)
	#		self.signal_workflow(cr, uid, [new_id], 'purchase_confirm', context)
	#		# samakan tanggal invoice dengan tanggal PO, jadi tidak default tanggal hari ini
	#		invoice_obj = self.pool.get('account.invoice')
	#		for invoice in purchase_data.invoice_ids:
	#			invoice_obj.write(cr, uid, [invoice.id], {
	#				'date_invoice': purchase_data.date_order,
	#			})
	#	return new_id
	
	#def write(self, cr, uid, ids, vals, context=None):
	#	result = super(purchase_order, self).write(cr, uid, ids, vals, context)
	#	self.message_post(cr, uid, ids, body="Draft PO <b>Edited</b>", subject = "DRAFT PO EDIT",context=context)
	#	return result
			
	#	result = super(purchase_order, self).write(cr, uid, ids, vals, context)
	#	if vals.get('state', False) and vals['state'] == 'confirmed':
	#	demand_line_obj = self.pool.get('tbvip.demand.line')
	#		for po in self.browse(cr, uid, ids):
	#			demand_line_ids = demand_line_obj.search(cr, uid, [('purchase_order_line_id','in',po.order_line.ids)])
	#			demand_line_obj.ready_demand_lines(cr, uid, demand_line_ids, context)
	# 		#20180411: confirm PO tidak lagi otomatis mendeliver barang; bisa ada jeda waktu
	# 		#antara confirm dan barang datang
	#		"""
	#		self.write(cr, uid, ids, {
	#			'delivered_date': datetime.today().strftime('%Y-%m-%d %H:%M:%S')
	#		})
	#		"""
	#	return result

	def onchange_picking_type_id(self, cr, uid, ids, picking_type_id, context=None):
		result = super(purchase_order, self).onchange_picking_type_id(cr, uid, ids, picking_type_id, context)
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		location_id =  user_data.branch_id.default_incoming_location_id.id or None
		result.update({
			'location_id': location_id,
		})
		return {'value': result}
	
	def onchange_branch_id(self, cr, uid, ids, branch_id, context=None):
		result = {}
		branch_obj = self.pool.get('tbvip.branch')
		location_id =  branch_obj.browse(cr, uid, branch_id)[0].default_incoming_location_id.id or None
		result.update({
			'location_id': location_id,
		})
		return {'value': result}
	
	#def picking_done(self, cr, uid, ids, context=None):
		"""
		Overrides picking_done to also mark the picking as transfered
		"""
		# 20180411: di-comment supaya incoming shipment jangan diasumsikan langsung Transferred
		# sebelumnya, confirm PO diasumsikan ketika barang datang dan sudah dihitung semua, dan
		# draft PO sudah diedit untuk menyesuaikan dengan barang yang diterima. per April 2018
		# confirm PO terjadi sebelum barang diterima.
		"""
		picking_ids = []
		for po in self.browse(cr, uid, ids, context=context):
			if po.shipped_or_taken == 'shipped':
				picking_ids += [picking.id for picking in po.picking_ids]
		picking_obj = self.pool.get('stock.picking')
		picking_obj.do_transfer(cr, uid, picking_ids)
		"""
	#	return super(purchase_order, self).picking_done(cr, uid, ids, context)

	def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
	# kondisikan supaya price_type_id di po line ikut dicopy ke invoice
		result = super(purchase_order, self)._prepare_inv_line(cr, uid, account_id, order_line, context=context)
			
		#print "tbvip/purchase.py: order_line.price_type_id : %s" % (order_line.price_type_id.id)
		#raise osv.except_osv('test','test')

		result.update({
			'price_type_id': order_line.price_type_id.id,
			})
		return result
	
	def action_invoice_create(self, cr, uid, ids, context=None):
		"""Overrides so that on creating invoice from confirming a PO, the invoice is set as open
		:param ids: list of ids of purchase orders.
		:return: ID of created invoice.
		:rtype: int
		"""
		result = super(purchase_order, self).action_invoice_create(cr, uid, ids, context)
		# 20180411: ditutup karena per April 2018 invoice digenerate bukan ketika PO di-confirm
		# tapi ketika barang datang. Ditambah lagi, juga ada request supaya ketika PO 
		# sudah jadi invoice pun masih bisa diedit sebelum benar2 menjadi hutang
		"""
		invoice_obj = self.pool.get('account.invoice')
		for invoice in invoice_obj.browse(cr, uid, [result]):
			invoice.signal_workflow('invoice_open')
		"""
		return result
	
	def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
	# supaya kalau sudah set partner lalu set payment term, bila lalu ganti partner lagi
	# payment term supaya tetap (jangan diganti)
	# ini karena default payment term bukan sesuai supplier tapi fixed (see bagian _defaults
	# di atas)
		if not partner_id: return {}
		result = super(purchase_order, self).onchange_partner_id(cr, uid, ids, partner_id, context)
		values = result.get('value', False)
		if values:
			payment_term_id = values.get('payment_term_id', False)
			if not payment_term_id:
				values.pop('payment_term_id')
		return result
	
	#TEGUH20180409 : override merge method, 
	#sebelumnya error 'nyangkut' di price list type id
	def do_merge(self, cr, uid, ids, context=None):
		def make_key(br, fields):
			list_key = []
			for field in fields:
				field_val = getattr(br, field)
				if field in ('product_id', 'account_analytic_id'):
					if not field_val:
						field_val = False
				if isinstance(field_val, browse_record):
					field_val = field_val.id
				elif isinstance(field_val, browse_null):
					field_val = False
				elif isinstance(field_val, browse_record_list):
					field_val = ((6, 0, tuple([v.id for v in field_val])),)
				list_key.append((field, field_val))
			list_key.sort()
			return tuple(list_key)

		context = dict(context or {})

		# Compute what the new orders should contain
		new_orders = {}

		order_lines_to_move = {}
		for porder in [order for order in self.browse(cr, uid, ids, context=context) if order.state == 'draft']:
			order_key = make_key(porder, ('partner_id', 'location_id', 'pricelist_id', 'currency_id'))
			new_order = new_orders.setdefault(order_key, ({}, []))
			new_order[1].append(porder.id)
			order_infos = new_order[0]
			order_lines_to_move.setdefault(order_key, [])

			if not order_infos:
				order_infos.update({
					'origin': porder.origin,
					'date_order': porder.date_order,
					'partner_id': porder.partner_id.id,
					'dest_address_id': porder.dest_address_id.id,
					'picking_type_id': porder.picking_type_id.id,
					'location_id': porder.location_id.id,
					'pricelist_id': porder.pricelist_id.id,
					'currency_id': porder.currency_id.id,
					#TEGUH201809 : add this line
					'price_type_id':porder.price_type_id.id,
					'state': 'draft',
					'order_line': {},
					'notes': '%s' % (porder.notes or '',),
					'fiscal_position': porder.fiscal_position and porder.fiscal_position.id or False,
				})
			else:
				if porder.date_order < order_infos['date_order']:
					order_infos['date_order'] = porder.date_order
				if porder.notes:
					order_infos['notes'] = (order_infos['notes'] or '') + ('\n%s' % (porder.notes,))
				if porder.origin:
					order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin

			order_lines_to_move[order_key] += [order_line.id for order_line in porder.order_line
											   if order_line.state != 'cancel']

		allorders = []
		orders_info = {}
		for order_key, (order_data, old_ids) in new_orders.iteritems():
			# skip merges with only one order
			if len(old_ids) < 2:
				allorders += (old_ids or [])
				continue

			# cleanup order line data
			for key, value in order_data['order_line'].iteritems():
				del value['uom_factor']
				value.update(dict(key))
			order_data['order_line'] = [(6, 0, order_lines_to_move[order_key])]

			# create the new order
			context.update({'mail_create_nolog': True})
			neworder_id = self.create(cr, uid, order_data)
			self.message_post(cr, uid, [neworder_id], body=_("Draft Merged PO Create"), context=context)
			orders_info.update({neworder_id: old_ids})
			allorders.append(neworder_id)

			# make triggers pointing to the old orders point to the new order
			for old_id in old_ids:
				self.redirect_workflow(cr, uid, [(old_id, neworder_id)])
				self.signal_workflow(cr, uid, [old_id], 'purchase_cancel')

		return orders_info


	#TEGUH@20180425 : overide fungsi ini, bagian partner_id di move_template	
	def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):	
		product_uom = self.pool.get('product.uom')
		price_unit = order_line.price_unit
		if order_line.taxes_id:
			taxes = self.pool['account.tax'].compute_all(cr, uid, order_line.taxes_id, price_unit, 1.0,order_line.product_id, order.partner_id)
			price_unit = taxes['total']
		if order_line.product_uom.id != order_line.product_id.uom_id.id:
			price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
		if order.currency_id.id != order.company_id.currency_id.id:
			#we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
			price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
		res = []
		if order.location_id.usage == 'customer':
			name = order_line.product_id.with_context(dict(context or {}, lang=order.dest_address_id.lang)).display_name
		else:
			name = order_line.name or ''
		move_template = {
			'name': name,
			'product_id': order_line.product_id.id,
			'product_uom': order_line.product_uom.id,
			'product_uos': order_line.product_uom.id,
			'date': order.date_order,
			'date_expected': fields.date.date_to_datetime(self, cr, uid, order_line.date_planned, context),
			'location_id': order.partner_id.property_stock_supplier.id,
			'location_dest_id': order.location_id.id,
			'picking_id': picking_id,
			#TEGUH@20180425 : overide line ini, variable awal : 'order.dest_address_id.id' ,diganti jadi 'order.partner_id.id',
			'partner_id': order.partner_id.id,
			'move_dest_id': False,
			'state': 'draft',
			'purchase_line_id': order_line.id,
			'company_id': order.company_id.id,
			'price_unit': price_unit,
			'picking_type_id': order.picking_type_id.id,
			'group_id': group_id,
			'procurement_id': False,
			'origin': order.name,
			'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
			'warehouse_id':order.picking_type_id.warehouse_id.id,
			'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
		}

		diff_quantity = order_line.product_qty
		for procurement in order_line.procurement_ids:
			procurement_qty = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, to_uom_id=order_line.product_uom.id)
			tmp = move_template.copy()
			tmp.update({
				'product_uom_qty': min(procurement_qty, diff_quantity),
				'product_uos_qty': min(procurement_qty, diff_quantity),
				'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
				'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
				'procurement_id': procurement.id,
				'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='2binvoiced' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
				'propagate': procurement.rule_id.propagate,
			})
			diff_quantity -= min(procurement_qty, diff_quantity)
			if not float_is_zero(tmp['product_uom_qty'], precision_rounding=order_line.product_uom.rounding):
				res.append(tmp)
		#if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
		#split the future stock move in two because the route followed may be different.
		if float_compare(diff_quantity, 0.0, precision_rounding=order_line.product_uom.rounding) > 0:
			move_template['product_uom_qty'] = diff_quantity
			move_template['product_uos_qty'] = diff_quantity
			res.append(move_template)
		return res


	# PRINTS ----------------------------------------------------------------------------------------------------------------
	
	def print_draft_purchase_order(self, cr, uid, ids, context):
		if self.browse(cr,uid,ids)[0].order_line:
			return {
				'type' : 'ir.actions.act_url',
				'url': '/tbvip/print/purchase.order/' + str(ids[0]),
				'target': 'self',
			}
		else:
			raise osv.except_osv(_('Print Draft PO Error'),_('PO must have at least one line to be printed.'))

# ==========================================================================================================================

class purchase_order_line(osv.osv):
	_inherit = 'purchase.order.line'
	
	WATCHED_FIELDS_FROM_PO = ['product_id', 'product_qty', 'price_unit', 'discount_string']
	SOURCE = [('needs', 'Needs'), ('manual', 'Manual'), ('owner', 'Owner')]
	
	def _purchase_hour(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		lines = self.browse(cr, uid, ids)
		for line in lines:
			purchase_date = datetime.strptime(line.date_order, '%Y-%m-%d %H:%M:%S')
			result[line.id] = purchase_date.hour * 3600 + purchase_date.minute * 60
		return result

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'source': fields.selection(SOURCE, 'Source'),
		'mysql_purchase_det_id': fields.integer('MySQL Purchase Detail ID'),
		'purchase_hour': fields.function(_purchase_hour, method=True, string='Purchase Hour', type='float'),
		'alert': fields.integer('Alert'),
		'product_qty': fields.float('Quantity', digits_compute= dp.get_precision('Decimal Custom Order Line'), required=True),
		'uom_category_filter_id': fields.related('product_id', 'product_tmpl_id', 'uom_id', 'category_id', relation='product.uom.categ', type='many2one',
			string='UoM Category', readonly=True),	
		'nett_price_old': fields.float(string = 'Nett Old'),	
	}
	
	_sql_constraints = [
		('po_quantity_less_than_zero', 'CHECK(product_qty > 0)', 'Quantity must be more than zero.'),
		('po_price_unit_less_than_zero', 'CHECK(price_unit >= 0)', 'Price must be more than zero.'),
	]
	
	# DEFAULTS --------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'source': 'manual',
	}
	
	# METHODS ---------------------------------------------------------------------------------------------------------------
	def _message_cost_price_changed(self, cr, uid, old_price,new_price, product, order_id, context):
	# message post to SUPERUSER and all users in group Purchases Manager
	# kalau harga yang diinput tidak sama dengan standard price product	
		if ((old_price > 0) and (old_price != new_price)):
			purchase_order_obj = self.pool.get('purchase.order')
			purchase_order = purchase_order_obj.browse(cr, uid, order_id)			
			message="There is a change on cost price for %s in Purchase Order %s. Original: %s to %s." % (product.name, purchase_order.name, old_price,new_price)		
			purchase_order_obj.message_post(cr, uid, purchase_order.id, body=message)

		#if product.standard_price > 0 and data['price_unit'] != product.standard_price:
		#	purchase_order_obj = self.pool.get('purchase.order')
		#	purchase_order = purchase_order_obj.browse(cr, uid, order_id)
		#	group_obj = self.pool.get('res.groups')
		#	purchase_manager_group_ids = group_obj.search(cr, uid, [
		#		('category_id.name', '=', 'Purchases'),
		#		('name', '=', 'Manager')
		#		])
		#	partner_ids = [SUPERUSER_ID]
		#	for user in group_obj.browse(cr, uid, purchase_manager_group_ids).users:
		#		partner_ids += [user.partner_id.id]
		#	partner_ids = list(set(partner_ids))
		#	purchase_order_obj.message_post(cr, uid, purchase_order.id, context=context, partner_ids=partner_ids,
		#		body=_(
		#			"There is a change on cost price for %s in Purchase Order %s. Original: %s, in PO: %s.")
		#			 % (product.name, purchase_order.name, product.standard_price,
		#		data['price_unit']))
	
	def _message_line_changes(self, cr, uid, vals, line_id, create=False, context=None):
		purchase_order_obj = self.pool.get('purchase.order')
		product_obj = self.pool.get('product.product')
		line = self.browse(cr, uid, line_id)
		message = _("Order line changed:") if not create else _("Order line created:")
		for key, val in vals.iteritems():
			if key in self.WATCHED_FIELDS_FROM_PO:
				value_from = ''
				value_to = val
				if key == 'product_id':
					value_from = line.product_id.name
					value_to = product_obj.browse(cr, uid, val).name
				elif key == 'product_qty':
					value_from = line.product_qty
					value_to = val
				elif key == 'price_unit':
					value_from = line.price_unit
					value_to = val
				elif key == 'discount_string':
					value_from = line.discount_string
					value_to = val
				message += "\n<li><b>%s</b>: %s %s %s</li>" % (self._columns[key].string, value_from, u'\u2192', value_to) \
					if not create else \
					"\n<li><b>%s</b>: %s</li>" % (self._columns[key].string, value_to)
		purchase_order_obj.message_post(cr, uid, line.order_id.id, body=message)
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context=None):
		new_order_line = super(purchase_order_line, self).create(cr, uid, vals, context)
		new_data = self.browse(cr, uid, new_order_line)
		
		if vals.get('product_id', False) and vals.get('price_unit', False):
			#cek bila ada perubahan harga beli
			#product_obj = self.pool.get('product.product')
			#product = product_obj.browse(cr, uid, vals['product_id'])
			#notif nya pindah ke invoice line
			#self._message_cost_price_changed(cr, uid, vals['nett_price_old'],vals['price_unit_nett'], product,vals['order_id'], context)
			#self._message_line_changes(cr, uid, vals, new_order_line, create=True, context=None)
		
		# otomatis create current price kalo belum ada
			if vals.get('price_type_id', False) and vals.get('product_uom', False):
				self.pool.get('price.list')._create_product_current_price_if_none(cr, uid,
					vals['price_type_id'], vals['product_id'], vals['product_uom'],
					vals['price_unit'], vals['discount_string'], partner_id=new_data.order_id.partner_id.id)
		
		# otomatis isi incoming location dengan default stock location cabang di mana user ini login
		# artinya, secara default barang akan dikirim ke cabang user pembuat PO ini
		# hanya bila tidak diset di vals nya
		if not vals.get('location_id', False):
			users_obj = self.pool.get('res.users')
			incoming_location = users_obj.browse(cr, uid, [uid], context).branch_id.default_incoming_location_id
			if incoming_location != False:
				vals['location_id'] = incoming_location
		return new_order_line
	
	def write(self, cr, uid, ids, vals, context=None):			
		for id in ids:
			self._message_line_changes(cr, uid, vals, id, context=None)								
		edited_order_line = super(purchase_order_line, self).write(cr, uid, ids, vals, context)
		
		for po_line in self.browse(cr, uid, ids):		
			#cek perubahan harga, tp masih ERROR
			price_unit_nett = po_line.price_unit_nett
			nett_price_old = po_line.nett_price_old
			#notif nya pindah ke invoice line
			#self._message_cost_price_changed(cr, uid, nett_price_old,price_unit_nett, po_line.product_id, po_line.order_id.id, context)	
			
			# bikin product current price baru bila belum ada
			product_id = po_line.product_id.id
			price_type_id = po_line.price_type_id.id
			product_uom = po_line.product_uom.id
			price_unit = po_line.price_unit
			#TEGUH@20180501 : tambah field discount_string
			discount_string = po_line.discount_string
			if vals.get('product_id', False): product_id = vals['product_id']
			if vals.get('price_type_id', False): price_type_id = vals['price_type_id']
			if vals.get('product_uom', False): product_uom = vals['product_uom']
			if vals.get('price_unit', False): price_unit = vals['price_unit']
			#TEGUH@20180501 : tambah field discount string
			if vals.get('discount_string', False): discount_string = vals['discount_string']
			self.pool.get('price.list')._create_product_current_price_if_none(
				cr, uid, price_type_id, product_id, product_uom, price_unit, discount_string,
				partner_id=po_line.order_id.partner_id.id)
		return edited_order_line
	
	#def unlink(self, cr, uid, ids, context=None):
	# kalau line ini batal, maka demand yang menyebabkan adanya purchase order (di mana 
	# purchase order line ini berada) ini berubah status kembali menjadi requested
	# artinya demand tersebut dianggap belum fulfilled
	#	result = super(purchase_order_line, self).unlink(cr, uid, ids, context)
	#	demand_line_obj = self.pool.get('tbvip.demand.line')
	#	demand_line_ids = demand_line_obj.search(cr, uid, [('purchase_order_line_id','in',ids)])
	#	demand_line_obj.write(cr, uid, demand_line_ids, {
	#		'state': 'requested'
	#	})
	#	return result
	# OVERRIDES -------------------------------------------------------------------------------------------------------------

	def onchange_product_id_tbvip(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
			partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
			name=False, price_unit=False, state='draft', parent_price_type_id=False, price_type_id=False,
			discount_from_subtotal=False, context=None):
		result = self.onchange_product_tbvip(cr, uid, ids, pricelist_id, product_id, qty, uom_id, partner_id, date_order,
			fiscal_position_id, date_planned, name, price_unit, state, parent_price_type_id, price_type_id,
			discount_from_subtotal,context)
		if product_id:
			product_obj = self.pool.get('product.product')
			product = product_obj.browse(cr, uid, product_id)
			result['value']['product_uom'] = product.uom_id.id
		return result
	
	def onchange_product_tbvip(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
		partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
		name=False, price_unit=False, state='draft', parent_price_type_id=False, 
		price_type_id=False, discount_from_subtotal=False, context=None):
	# karena tbvip inherit dari berbagai modul yang sebagian punya onchange product id,
	# maka dibuatlah method onchange ini. pada dasarnya ini memanggil onchange2 module
	# general-purpose yang terlibat di tbvip (contoh chjs_price_list, purchase_sale_discount)
	# dan menggabungkan hasilnya (baik warning, value, domain) ke dalam satu return
	# hati2, urutan pemanggilan sangatlah penting karena efek yang satu bisa ditiadakan/
	# dianulir setelah memanggil onchange yang lain.
		
		result = {'value': {}, 'domain': {}}

		product_conversion_obj = self.pool.get('product.conversion')
		uom_id = product_conversion_obj.get_uom_from_auto_uom(cr, uid, uom_id, context).id
		
	# jalankan onchange dari modul price list
		oc_price_list = \
			imported_price_list.purchase.purchase_order_line.onchange_product_id(
			self, cr, uid, ids, pricelist_id, product_id, qty, uom_id, partner_id, date_order, fiscal_position_id,
			date_planned, name, price_unit, state, parent_price_type_id, price_type_id,context)
	# hide warning dari price_list ketika tidak menemukan harga untuk uom dan product id yang dipilih
		oc_price_list['warning'] = {}
		result['value'].update(oc_price_list.get('value', {}))

	# default diskon diambil dari current price
		current_price_unit = oc_price_list['value'].get('price_unit', price_unit)		
		current_discount = self.pool.get('product.current.price').get_current(
			cr, uid, product_id, price_type_id, uom_id, partner_id=partner_id, field="disc", context=context)	
	# isi nett price old dari price list	
		nett_price_old = self.pool.get('product.current.price').get_current(
			cr, uid, product_id, price_type_id, uom_id, partner_id=partner_id, field="nett", context=context)			
	# jalankan onchange diskon. price unit dan discount string, as per logic di dalam 
	# onchange_product_id_purchase_sale_discount, akan tetap memakai yang dari current price
	# di atas
		oc_purchase_sale_discount = \
			imported_purchase_sale_discount.purchase_discount.purchase_order_line.onchange_product_id_purchase_sale_discount(
			self, cr, uid, ids, product_id, partner_id, uom_id, qty, current_price_unit, current_discount, discount_from_subtotal)
		if oc_purchase_sale_discount:
			result['value'].update(oc_purchase_sale_discount.get('value', {}))
		
		final_product_uom = uom_id
		if not final_product_uom:
			product_obj = self.pool.get('product.product')
			product = product_obj.browse(cr, uid, product_id)
			final_product_uom = product.uom_id.id

	# jalankan onchange custom conversion
		"""
		oc_custom_conversion = \
			imported_product_custom_conversion.purchase.purchase_order_line.onchange_product_uom(
			self, cr, uid, ids, pricelist_id, product_id, qty, uom_id, partner_id, date_order, 
			fiscal_position_id, date_planned, name, current_price_unit, state, context=context)
		if result.get('domain', False) and oc_custom_conversion.get('domain', False):
			result['domain']['product_uom'] = result['domain']['product_uom'] + oc_custom_conversion['domain']['product_uom']		
		custom_product_uom = oc_custom_conversion['value'].get('product_uom', False)
		if custom_product_uom:
			final_product_uom = custom_product_uom
		"""
		
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		result['value'].update({
			'product_uom': final_product_uom,
			'uom_category_filter_id': product.product_tmpl_id.uom_id.category_id.id,
			'nett_price_old' : nett_price_old,
		})
		
		return result

class purchase_report(osv.osv):
	_inherit = "purchase.report"
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	#TEGUH20180425 : hapus semua tulisan cr.rate
	def init(self, cr):
		tools.sql.drop_view_if_exists(cr, 'purchase_report')
		cr.execute("""
			create or replace view purchase_report as (
				WITH currency_rate (currency_id, rate, date_start, date_end) AS (
					SELECT r.currency_id, r.rate, r.name AS date_start,
						(SELECT name FROM res_currency_rate r2
						WHERE r2.name > r.name AND
							r2.currency_id = r.currency_id
						 ORDER BY r2.name ASC
						 LIMIT 1) AS date_end
					FROM res_currency_rate r
				)
				select
					min(l.id) as id,
					s.date_order as date,
					l.state,
					s.date_approve,
					s.minimum_planned_date as expected_date,
					s.dest_address_id,
					s.pricelist_id,
					s.validator,
					spt.warehouse_id as picking_type_id,
					s.partner_id as partner_id,
					s.create_uid as user_id,
					s.company_id as company_id,
					l.product_id,
					t.categ_id as category_id,
					t.uom_id as product_uom,
					s.location_id as location_id,
					sum(l.product_qty/u.factor*u2.factor) as quantity,
					extract(epoch from age(s.date_approve,s.date_order))/(24*60*60)::decimal(16,2) as delay,
					extract(epoch from age(l.date_planned,s.date_order))/(24*60*60)::decimal(16,2) as delay_pass,
					count(*) as nbr,
					sum(l.price_unit*l.product_qty)::decimal(16,2) as price_total,
					avg(100.0 * (l.price_unit*l.product_qty) / NULLIF(ip.value_float*l.product_qty/u.factor*u2.factor, 0.0))::decimal(16,2) as negociation,
					sum(ip.value_float*l.product_qty/u.factor*u2.factor)::decimal(16,2) as price_standard,
					(sum(l.product_qty*l.price_unit)/NULLIF(sum(l.product_qty/u.factor*u2.factor),0.0))::decimal(16,2) as price_average
				from purchase_order_line l
					join purchase_order s on (l.order_id=s.id)
						left join product_product p on (l.product_id=p.id)
							left join product_template t on (p.product_tmpl_id=t.id)
							LEFT JOIN ir_property ip ON (ip.name='standard_price' AND ip.res_id=CONCAT('product.template,',t.id) AND ip.company_id=s.company_id)
					left join product_uom u on (u.id=l.product_uom)
					left join product_uom u2 on (u2.id=t.uom_id)
					left join stock_picking_type spt on (spt.id=s.picking_type_id)
					join currency_rate cr on (cr.currency_id = s.currency_id and
						cr.date_start <= coalesce(s.date_order, now()) and
						(cr.date_end is null or cr.date_end > coalesce(s.date_order, now())))
				group by
					s.company_id,
					s.create_uid,
					s.partner_id,
					u.factor,
					s.location_id,
					l.price_unit,
					s.date_approve,
					l.date_planned,
					l.product_uom,
					s.minimum_planned_date,
					s.pricelist_id,
					s.validator,
					s.dest_address_id,
					l.product_id,
					t.categ_id,
					s.date_order,
					l.state,
					spt.warehouse_id,
					u.uom_type,
					u.category_id,
					t.uom_id,
					u.id,
					u2.factor
			)
		""")
