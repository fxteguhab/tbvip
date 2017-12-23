from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, timedelta
from openerp import api



# ==========================================================================================================================

class stock_quant(osv.osv):
	"""
	Quants are the smallest unit of stock physical instances
	"""
	_inherit = "stock.quant"
	
	def _get_inventory_value(self, cr, uid, quant, context=None):
		"""
		Overrides so that inventory value is calculated from qty * quant.cost; instead of
		product_id.standard_price
		"""
		return quant.cost * quant.qty

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


# ==========================================================================================================================
	
class stock_move(osv.osv):
	_inherit = 'stock.move'
	
	def create(self, cr, uid, vals, context={}):
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
		demand_line_obj = self.pool.get('tbvip.demand.line')
		demand_line_ids = demand_line_obj.search(cr, uid, [('stock_move_id','in',ids)])
		demand_line_obj.write(cr, uid, demand_line_ids, {
			'state': 'requested'
		})
		return result
	
	def get_price_unit(self, cr, uid, move, context=None):
		""" Returns the unit price to store on the quant """
		if move.purchase_line_id:
			return move.purchase_line_id.price_unit_nett
		
		return super(stock_move, self).get_price_unit(cr, uid, move, context=context)

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
				iter_location = iter_location.parent_id
				full_name = iter_location.name + ' / ' + full_name
				name_count += 1
			result[sublocation.id] = full_name
		return result
	
	_columns = {
		'name': fields.char('Name'),
		'full_name': fields.function(_full_name, type='char', string='Full Name'),
		'parent_id': fields.many2one('stock.sublocation', 'Parent Sublocation'),
		'child_ids': fields.one2many('stock.sublocation', 'parent_id', 'Child Sublocations'),
		'type': fields.selection([('view', 'View'), ('physical', 'Physical')], 'Type')
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
	
	# PRINTS ---------------------------------------------------------------------------------------------------------------
	
	def print_stock_inventory(self, cr, uid, ids, context):
		return {
			'type' : 'ir.actions.act_url',
			'url': '/tbvip/print/stock.inventory/' + str(ids[0]),
			'target': 'self',
		}

# ==========================================================================================================================

class stock_picking(osv.osv):
	
	_inherit = 'stock.picking'
	
# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'related_sales_bon_number': fields.char("Nomor Bon", readonly=True),
		'interbranch_move_id': fields.many2one('tbvip.interbranch.stock.move', 'Related Interbranch Transfer', search=False, ondelete="cascade"),
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
		
