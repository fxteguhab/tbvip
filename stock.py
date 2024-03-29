from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api

# ==========================================================================================================================

class stock_quant(osv.osv):
	"""
	Quants are the smallest unit of stock physical instances
	"""
	_inherit = "stock.quant"
	
	_columns = {
		'cost': fields.float('Unit Cost',group_operator="avg"),
		#'categ_id' : fields.char(related = "product_id.categ_id.name",string="Category",store=True),
	}

	def _get_inventory_value(self, cr, uid, quant, context=None):
		"""
		Overrides so that inventory value is calculated from qty * quant.cost; instead of
		product_id.standard_price
		"""
		return (quant.cost * quant.qty) or (quant.product_id.standard_price * quant.qty)

# ==========================================================================================================================


class stock_unit(osv.osv):
	
	_name = 'stock.unit'
	
# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'name': fields.char('Name'),
		'unit': fields.float('Unit'),
	}

# ==========================================================================================================================

class stock_location(osv.osv):
	
	_inherit = 'stock.location'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'is_branch': fields.boolean('Is Branch?'),
		# 'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}

	"""
	def _initialize_default_stock_location_data(self, cr, uid, ids=None, context=None):
		stock_warehouse_obj = self.pool.get('stock.warehouse')
		branch_obj = self.pool.get('tbvip.branch')
		data_obj = self.pool.get('ir.model.data')
		stock_warehouse_id = data_obj.get_object(cr, uid, 'stock', 'warehouse0').id
		stock_warehouse = stock_warehouse_obj.browse(cr, uid, stock_warehouse_id)
		if stock_warehouse:
			stock_location_id = stock_warehouse.view_location_id
			name_gudang_22 = "Gudang 22"
			name_gudang_85 = "Gudang 85"
			name_gudang_cikutra = "Gudang Cikutra"
			
		# cari dahulu apakah sudah pernah dibikin, jika iya gunakan location yang lama
			stock_location_22 = self.search(cr, uid, [
				('name', '=', name_gudang_22),
			], limit=1)
			stock_location_85 = self.search(cr, uid, [
				('name', '=', name_gudang_85),
			], limit=1)
			stock_location_cikutra = self.search(cr, uid, [
				('name', '=', name_gudang_cikutra),
			], limit=1)
			
			if len(stock_location_22)==0:
				stock_location_22 = self.create(cr, uid, {
					'name': name_gudang_22,
					'location_id': stock_location_id.id,
					'usage': 'internal',
					'is_branch': True,
				})
			else :
				stock_location_22 = stock_location_22[0]
			if len(stock_location_85)==0:
				stock_location_85 = self.create(cr, uid, {
					'name': name_gudang_85,
					'location_id': stock_location_id.id,
					'usage': 'internal',
					'is_branch': True,
				})
			else :
				stock_location_85 = stock_location_85[0]
			if len(stock_location_cikutra)==0:
				stock_location_cikutra = self.create(cr, uid, {
					'name': name_gudang_cikutra,
					'location_id': stock_location_id.id,
					'usage': 'internal',
					'is_branch': True,
				})
			else :
				stock_location_cikutra = stock_location_cikutra[0]
			
			branch_id_22 = data_obj.get_object(cr, uid, 'tbvip', 'tbvip_branch_22').id
			branch_id_85 = data_obj.get_object(cr, uid, 'tbvip', 'tbvip_branch_85').id
			
			branch_obj.write(cr, uid, branch_id_22, {
				'default_incoming_location_id' : stock_location_22,
				'default_outgoing_location_id' : stock_location_22,
				'default_stock_location_id' : stock_location_22,
			})
			
			branch_obj.write(cr, uid, branch_id_85, {
				'default_incoming_location_id' : stock_location_85,
				'default_outgoing_location_id' : stock_location_85,
				'default_stock_location_id' : stock_location_85,
			})
			
				
			#TODO location cikutra belum di set kemana2, karena belum ada branch
		return True
	"""		
	
# ==========================================================================================================================

class stock_bonus_usage(osv.osv):
	
	_name = 'stock.bonus.usage'
	_description = 'Stock Bonus Usage'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'usage_date': fields.datetime('Usage Date', required=True),
		'name': fields.char('Name', required=True),
		'usage_by_id': fields.many2one('res.users', 'Usage By', required=True),
		'move_from_id': fields.many2one('stock.location', 'Move From', required=True),
		'bonus_usage_line_ids': fields.one2many('stock.bonus.usage.line', 'bonus_usage_id', 'Usage'),
		'state': fields.selection([
			('draft','Draft'),
			('approved','Approved'),
			('rejected','Rejected')], 'State', required=True),
	}
	
	# DEFAULTS --------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'usage_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'usage_by_id': lambda self, cr, uid, ctx: uid,
		'state': 'draft',
	}
	
	# CONSTRAINT ---------------------------------------------------------------------------------------------------------------
	
	def _usage_line_min(self, cr, uid, ids, context=None):
		# Cek bonus usage line harus ada minimal 1 baris
		for bonus_usage in self.browse(cr, uid, ids, context):
			if len(bonus_usage.bonus_usage_line_ids) == 0:
				return False
		return True
	
	def _move_from_min_qty(self, cr, uid, ids, context=None):
		# Cek bahwa setiap product di line harus punya minimal sejumlah qty yang diminta di stock location move_from
		quant_obj = self.pool["stock.quant"]
		uom_obj = self.pool["product.uom"]
		for bonus_usage in self.browse(cr, uid, ids, context):
			for line in bonus_usage.bonus_usage_line_ids:
				domain = [('location_id', '=', bonus_usage.move_from_id.id), ('product_id','=', line.product_id.id)]
				quant_ids = quant_obj.search(cr, uid, domain, context=context)
				quants = quant_obj.browse(cr, uid, quant_ids, context=context)
				tot_qty = sum([x.qty for x in quants])
				if line.uom_id and line.product_id.uom_id.id != line.uom_id.id:
					tot_qty = uom_obj._compute_qty_obj(cr, uid, line.product_id.uom_id, tot_qty, line.uom_id, context=context)
				if tot_qty < line.qty:
					return False
		return True
	
	_constraints = [
		(_usage_line_min, _('You must have at least one usage line.'), ['bonus_usage_line_ids']),
		(_move_from_min_qty, _('The location does not have that many product.'), ['move_from_id', 'bonus_usage_line_ids']),
	]
	
	# ACTION ----------------------------------------------------------------------------------------------------------------
	
	def action_approve (self, cr, uid, ids, context=None):
		move_obj = self.pool.get('stock.move')
		model_obj = self.pool.get('ir.model.data')
		model, location_bonus_usage_id = model_obj.get_object_reference(cr, uid, 'tbvip', 'stock_location_bonus_usage')
		for bonus_usage in self.browse(cr, uid, ids, context=context):
			for bonus_usage_line in bonus_usage.bonus_usage_line_ids:
				if bonus_usage_line.qty < 0:
					raise osv.except_osv(_('Warning'), _('You cannot set a negative product quantity in bonus usage line:\n\t%s - qty: %s' % (bonus_usage_line.product_id.name, bonus_usage_line.qty)))
				vals = {
					'name': bonus_usage.name,
					'date': bonus_usage.usage_date,
					'location_id': bonus_usage.move_from_id.id,
					'location_dest_id': location_bonus_usage_id,
					'product_id': bonus_usage_line.product_id.id,
					'product_uom_qty': bonus_usage_line.qty,
					'product_uom': bonus_usage_line.uom_id.id,
					'product_tmpl_id': bonus_usage_line.product_id.product_tmpl_id.id,
				}
				new_move_id = move_obj.create(cr, uid, vals, context=context)
				move_obj.action_done(cr, uid, new_move_id, context=context)
			self.write(cr, uid, [bonus_usage.id], {'state': 'approved'}, context=context)
		return True
	
	def action_reject (self, cr, uid, ids, context=None):
		for bonus_usage in self.browse(cr, uid, ids, context):
			self.write(cr, uid, [bonus_usage.id], {'state': 'rejected'}, context=context)
		return

# ==========================================================================================================================

class stock_bonus_usage_line(osv.osv):
	
	_name = 'stock.bonus.usage.line'
	_description = 'Stock Bonus Usage Line'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'bonus_usage_id': fields.many2one('stock.bonus.usage', 'Bonus Usage'),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'qty': fields.float('Qty', required=True),
		'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True),
	}
	
	# ONCHANGE -----------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		# uom_id hanya bisa uom_id product ybs
		if not product_id: return {}
		product_obj = self.pool.get('product.product')
		res = {}
		res['value'] = {'uom_id': ''}
		for product_data in product_obj.browse(cr, uid, product_id):
			res['domain'] = {'uom_id': [('category_id','=', product_data.product_tmpl_id.uom_id.category_id.id)]}
		return res
	
	def onchange_uom_id(self, cr, uid, ids, uom_id, product_id, context=None):
		# uom_id hanya bisa uom_id product ybs
		if not product_id: return {}
		product_obj = self.pool.get('product.product')
		uom_obj = self.pool.get('product.uom')
		res = {}
		for product_data in product_obj.browse(cr, uid, product_id):
			for uom_data in uom_obj.browse(cr, uid, uom_id):
				if product_data.product_tmpl_id.uom_id.category_id.id != uom_data.category_id.id:
					res = self.onchange_product_id(cr, uid, ids, product_id, context)
					res['warning'] = {'title': _('Warning!'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure.')}
		return res

# ==========================================================================================================================


class stock_check_memory(osv.osv_memory):
	
	_name = 'stock.check.memory'
	_description = 'Stock Bonus Usage Line'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'check_line': fields.one2many('stock.check.memory.line', 'header_id', 'Check Lines')
	}

# ==========================================================================================================================


class stock_check_memory_line(osv.osv_memory):
	_name = 'stock.check.memory.line'
	_description = 'Stock Bonus Usage Line'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'header_id': fields.many2one('stock.check.memory', 'Stock Check'),
		'product_id': fields.many2one('product.product', 'Product', domain="[('sale_ok', '=', True)]"),
		'price_info':fields.text('Price Info'),
		'stock_info': fields.text('Stock Info')
	}

	# ONCHANGE --------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		result = {}
		if not product_id: return result
		product_obj = self.pool.get('product.product')
		value = {}
		value.update({'stock_info': self.get_stock_info(cr, uid, ids, product_id)})
		result['value'] = value
		return result
	
	def get_stock_info(self, cr, uid, ids, product_id):
		result = ''
		quant_obj = self.pool.get('stock.quant')
		quant_ids = quant_obj.search(cr, uid, [('product_id', '=', product_id), ('location_id.usage','=', 'internal')])
		map = {}
		default_uom = ''
		for quant in quant_obj.browse(cr, uid, quant_ids):
			default_uom = quant.product_id.uom_id.name
			map[quant.location_id.display_name] = map.get(quant.location_id.display_name, 0) + quant.qty
		for key in sorted(map.iterkeys()):
			result += key + ': ' + str(map[key]) + ' ' + default_uom + '\r\n'
		return result

	def get_price_info(self, cr, uid, ids, product_id):
		result = {}
		return result
# ==========================================================================================================================
	
class stock_move(osv.osv):
	_inherit = 'stock.move'
	
	#_columns = {
	#	'sale_line_id': fields.many2one('sale.order.line','Sale Order Line', ondelete='set null', select=True,readonly=True),
	#}

	def create(self, cr, uid, vals, context={}):
		context = {} if context is None else context
		new_id = super(stock_move, self).create(cr, uid, vals, context=context)
		location_id_sale_override = context.get('sale_location_id')
		if location_id_sale_override:
			self.write(cr, uid, [new_id], {
				'location_id': location_id_sale_override,
			})
		return new_id
	
	def unlink(self, cr, uid, ids, context={}):
	# kalau dia punya stock picking dan stock picking itu nyambung sama interbranch transfer,
	# dan transfernya sudah accepted, maka jangan hapus
		for data in self.browse(cr, uid, ids, context=context):
			if not data.picking_id: continue
			if not data.picking_id.interbranch_move_id: continue
			if data.picking_id.interbranch_move_id.state in ['accepted']:
				raise osv.except_osv(_('Interbranch Move Error'),_('One or more of selected transfers has been set as Accepted. You cannot delete these anymore.'))
	# kalau move terkait demand, "batalkan" demandnya menjadi requested
		result = super(stock_move, self).unlink(cr, uid, ids, context)
	#	demand_line_obj = self.pool.get('tbvip.demand.line')
	#	demand_line_ids = demand_line_obj.search(cr, uid, [('stock_move_id','in',ids)])
	#	demand_line_obj.write(cr, uid, demand_line_ids, {
	#		'state': 'requested'
	#	})
		return result
	
	def get_price_unit(self, cr, uid, move, context=None):
		""" Returns the unit price to store on the quant """
		data_obj = self.pool.get('ir.model.data')
	# Jika dari Purchase, maka price untuk quants didapat dari unit price nett
		if move.purchase_line_id:
			price = move.purchase_line_id.price_unit_nett or move.product_id.standard_price
			price = price / move.product_id.uom_id.factor
			return price
			#return move.purchase_line_id.price_unit_nett or move.product_id.standard_price
		#elif move.sale_line_id:
		else:	
			return move.product_id.list_price

		result = super(stock_move, self).get_price_unit(cr, uid, move, context=context)
		
	# Jika price yang didapat 0, maka dapatkan dari price list buy harga default
		if not result:
			#if move.purchase_line_id:
			#	price_type_id = data_obj.get_object(cr, uid, 'tbvip', 'tbvip_normal_price_buy').id
			#if move.sale_line_id:	
			#	price_type_id = data_obj.get_object(cr, uid, 'tbvip', 'tbvip_normal_price_sell').id
			price_type_id = data_obj.get_object(cr, uid, 'tbvip', 'tbvip_normal_price_buy').id
			unit_id = data_obj.get_object(cr, uid, 'product', 'product_uom_unit').id
			product_current_price_obj = self.pool.get('product.current.price')
			product = move.product_id
			current_price = product_current_price_obj.get_current(cr, uid, product.id, price_type_id, unit_id,field="nett")
			current_price = current_price / move.product_id.uom_id.factor
			return current_price

	def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
		result = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
		purchase_line = move.purchase_line_id
		if inv_type == 'in_invoice' and purchase_line:
			price_type = 'buy'
			price_type_ids = self.pool.get('price.type').search(cr, uid, [('type','=',price_type),('is_default','=',True),])
			price_type_id = price_type_ids[0]
			
			price_type_id_sells = self.pool.get('price.type').search(cr, uid, [('type','=','sell'),('is_default','=',True),])
			price_type_id_sell = price_type_id_sells[0]
			general_customer_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')
			sell_price_unit = self.pool.get('product.current.price').get_current(
				cr, uid, purchase_line.product_id.id,price_type_id_sell, purchase_line.product_uom.id, partner_id = general_customer_id[1],field="nett", context=context)
			result.update({
				'price_type_id': price_type_id,
				'price_unit_old' : purchase_line.price_unit_old,
				'discount_string_old' : purchase_line.discount_string_old,
				'price_unit_nett_old' : purchase_line.price_unit_nett_old,
				'sell_price_unit' : sell_price_unit,
				})		
		return result

	def action_done(self, cr, uid, ids, context=None):
		result = super(stock_move, self).action_done(cr, uid, ids, context=context)
		po_obj = self.pool.get('purchase.order')
		stock_mv = self.browse(cr, uid, ids, context)
		if (stock_mv):
			po_line_id = stock_mv[0].purchase_line_id.id
			
			purchase_order_line = self.pool.get('purchase.order.line').browse(cr, uid, po_line_id)
			purchase_order =  po_obj.browse(cr, uid, purchase_order_line.order_id.id)
			
			po_obj.write(cr, uid, purchase_order.id, {
				'delivered_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
				})
		return result
# ==========================================================================================================================

class stock_sublocation(osv.osv):
	_name = 'stock.sublocation'
	
	_MAX_GET_NAME_COUNT = 10
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------

	def _full_name(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for sublocation in self.browse(cr, uid, ids, context):
			name_count = 0
			iter_location = sublocation
			full_name = iter_location.name
			while iter_location.parent_id.id is not False and name_count < self._MAX_GET_NAME_COUNT:
				branch = iter_location.branch_id.name
				iter_location = iter_location.parent_id
				full_name = str(branch) + ' / '+iter_location.name + ' / ' + full_name
				name_count += 1
			result[sublocation.id] = full_name
		return result
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'name': fields.char('Name'),
		'full_name': fields.function(_full_name, type='char', string='Full Name'),
		'parent_id': fields.many2one('stock.sublocation', 'Parent Sublocation'),
		'child_ids': fields.one2many('stock.sublocation', 'parent_id', 'Child Sublocations'),
		#'type': fields.selection([('view', 'View'), ('physical', 'Physical')], 'Type')
		'pic': fields.many2one('hr.employee', 'PiC'),
	}
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def name_get(self, cr, uid, ids, context=None):
		result = []
		for sublocation in self.browse(cr, uid, ids, context):
			result.append((sublocation.id, sublocation.full_name))
		return result

# ==========================================================================================================================

class stock_inventory_line(osv.osv):
	_inherit = 'stock.inventory.line'
	
	_columns = {
		'sublocation': fields.text('Sublocations'),
	}
	
	def onchange_createline(self, cr, uid, ids, location_id=False, product_id=False, uom_id=False, package_id=False, prod_lot_id=False, partner_id=False, company_id=False, context=None):
		result = super(stock_inventory_line, self).onchange_createline(cr, uid, ids, location_id, product_id, uom_id, package_id, prod_lot_id, partner_id, company_id, context)
		product_obj = self.pool.get('product.product')
		sublocation_name = ''
		for product in product_obj.browse(cr, uid, [product_id], context):
			for product_sublocation_id in product.product_sublocation_ids:
				sublocation = product_sublocation_id.sublocation_id
				if sublocation:
					sublocation_name += product_sublocation_id.branch_id.name + ' / ' + sublocation.full_name + '\r\n'
		result['value'].update({'sublocation': sublocation_name})
		return result

	def create(self, cr, uid, vals, context={}):
		new_id = super(stock_inventory_line, self).create(cr, uid, vals, context=context)
		onchange_result = self.onchange_createline(cr, uid, [new_id], vals['location_id'], vals['product_id'])
		self.write(cr, uid, [new_id], {
			'sublocation': onchange_result['value']['sublocation']
			})
		return new_id


# ==========================================================================================================================

class stock_inventory(osv.osv):
	_inherit = 'stock.inventory'
	
	def _get_total_qty(self, cr, uid, ids, field_name, args, context=None):
		res = {}
		for inv in self.browse(cr, uid, ids, context=context):
			res[inv.id] = sum([x.product_qty for x in inv.line_ids])
		return res

	# PRINTS ---------------------------------------------------------------------------------------------------------------
	
	def print_stock_inventory(self, cr, uid, ids, context):
		return {
			'type' : 'ir.actions.act_url',
			'url': '/tbvip/print/stock.inventory/' + str(ids[0]),
			'target': 'self',
		}

	def cron_autocancel_expired_stock_opname(self, cr, uid, context=None):
		"""
		Autocancel expired stock inventory based on expiration_date and today's time
		"""
		today = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
	# Pool every stock.inventory with draft or confirmed state
		stock_inventory_ids = self.search(cr, uid, [
			('state', 'in', ['draft', 'confirm']),  # draft or in progress
			('expiration_date', '<', today),
			('is_override', '=', False),
		])
		self.action_cancel_inventory(cr, uid, stock_inventory_ids, context)

# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'total_qty': fields.function(_get_total_qty, type="float", group_operator="sum"),
	}
# ==========================================================================================================================

class stock_picking(osv.osv):
	
	_inherit = 'stock.picking'
	

	def _default_wh_dest_id(self, cr, uid, context={}):
		branch_obj = self.pool.get('tbvip.branch')
		user_data = self.pool['res.users'].browse(cr, uid, uid)

		location_id =  branch_obj.browse(cr, uid, user_data.branch_id.id)[0].default_incoming_location_id.id or None
		return location_id

	def onchange_wh_dest_id(self, cr, uid, ids, wh_dest_id, context=None):
		for picking in self.browse(cr, uid, ids, context=context):
			for move in picking.move_lines:
				move.location_dest_id = wh_dest_id
		return

# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'related_sales_bon_number': fields.char("Nomor Bon", readonly=True),
		'interbranch_move_id': fields.many2one('tbvip.interbranch.stock.move', 'Related Interbranch Transfer', search=False, ondelete="cascade"),
		'wh_dest_id':fields.many2one('stock.location', 'Destination Location', states={'done': [('readonly', True)]}, domain=[('usage', '=', 'internal')]),
	}

	_defaults = {
		'wh_dest_id': _default_wh_dest_id,
	}

	
	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		"""
		Update name_search (like in m2o search) domain to search with sale bon number:
		"""
		args = args or []
		recs = self.browse()
		if name:
			recs = self.search([('related_sales_bon_number', '=', name)] + args, limit=limit)
		else:
			recs = self.search([('name', 'ilike', name)] + args, limit=limit)
		return recs.name_get()
	
	@api.multi
	def name_get(self):
		"""
		Shows nomor bon as name if this picking has related_sales_bon_number
		"""
		result = []
		for picking in self:
			result.append((
					picking.id,
					"Sales Order / " + picking.related_sales_bon_number if picking.related_sales_bon_number else picking.name
				)
			)
		return result

	def unlink(self, cr, uid, ids, context={}):
	# kalau picking ini ngelink sama interbranch transfer, dan transfernya udah accepted,
	# maka ngga boleh dihapus
		for data in self.browse(cr, uid, ids, context):
			if not data.interbranch_move_id: continue
			if data.interbranch_move_id.state in ['accepted']:
				raise osv.except_osv(_('Interbranch Move Error'),_('One or more of selected transfers has been set as Accepted. You cannot delete these anymore.'))
		return super(stock_picking, self).unlink(cr, uid, ids, context=context)

	def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
		result = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context)
		result.update({
				'origin': move.origin,
				})		
	
		return result
	
	def _prepare_values_extra_move(self, cr, uid, op, product, remaining_qty, context=None):
		result = super(stock_picking, self)._prepare_values_extra_move(cr, uid, op, product, remaining_qty, context)
		
		product_id = product.id
		picking_id = op.picking_id.id
		stock_move_obj = self.pool.get('stock.move')
		stock_move_id = stock_move_obj.search(cr, uid, [('picking_id', '=', picking_id),('product_id','=',product_id),('purchase_line_id','!=',None)], limit=1, context=context)
		stock_move = stock_move_obj.browse(cr,uid,stock_move_id)

		result.update({
				'origin': stock_move.origin,
				'purchase_line_id' : stock_move.purchase_line_id.id
				})	
		return result
	
	# PRINTS ----------------------------------------------------------------------------------------------------------------
	
	def print_delivery_order(self, cr, uid, ids, context):
		if self.browse(cr,uid,ids)[0].move_lines:
			return {
				'type' : 'ir.actions.act_url',
				'url': '/tbvip/print/stock.picking/' + str(ids[0]),
				'target': 'self',
			}
		else:
			raise osv.except_osv(_('Print Stock Picking Error'),_('Stock Picking must have at least one line to be printed.'))



class stock_opname_inject(osv.osv):
	_inherit = "stock.opname.inject"

	def create(self, cr, uid, vals, context={}):
		active_ids = False
		if context:
			active_ids = context.get('active_ids',False)
		if active_ids:
			product_obj = self.pool.get('product.product')
			product_ids = product_obj.search(cr, uid, [('product_tmpl_id','in',active_ids)])
		
			for product_id in product_ids:
				vals['product_id'] = product_id
				self.create(cr, uid, vals, context=None)

		else:		
			return super(stock_opname_inject, self).create(cr, uid, vals, context=context)

	def action_add(self, cr, uid, ids, context=None):
		return {'type': 'ir.actions.act_window_close'}
			
'''
class stock_opname_inject_wizard(osv.osv):
	_name = "stock.opname.inject.wizard"
	_description = "Stock opname inject wizard"
	
	_columns = {
		'location_id': fields.many2one('stock.location', 'Location', required=True, select=True),
		'product_id': fields.many2many('product.product', 'Product', required=True),
		'priority': fields.selection([(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6')], 'Priority',
			required=True),
		'active': fields.boolean('Active'),
		'domain': fields.selection(_EMPLOYEE_DOMAIN_TYPE, 'Domain'),
		'employee_id' : fields.many2one('hr.employee','Employee'),
	}
	
	# DEFAULTS --------------------------------------------------------------------------------------------------------------
	
	_defaults = {
		'priority': 1,
		'active': True,
		'location_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_stock_location_id.id,
	}

	def action_add(self, cr, uid, ids, context=None):
		active_ids = context.get('active_ids',0)
		print "active_ids: "+str(active_ids)
		#return {'type': 'ir.actions.act_window_close'}
'''