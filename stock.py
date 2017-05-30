from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime

# ==========================================================================================================================

class stock_location(osv.osv):
	
	_inherit = 'stock.location'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'is_branch': fields.boolean('Is Branch?'),
		# 'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
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
	
	def _default_location_source(self, cr, uid, context=None):
		result = super(stock_move, self)._default_location_source(cr, uid, context)
		if not result:
			users_obj = self.pool.get('res.users')
			outgoing_location = users_obj.browse(cr, uid, [uid], context).branch_id.default_outgoing_location_id
			if outgoing_location:
				result = outgoing_location
		return result
	
	_defaults = {
		'location_id': _default_location_source,
	}
	
	# OVERRIDES ------------------------------------------------------------------------------------------------------------
	
	def unlink(self, cr, uid, ids, context=None):
		result = super(stock_move, self).write(cr, uid, ids, context)
		demand_line_obj = self.pool.get('tbvip.demand.line')
		demand_line_ids = demand_line_obj.search(cr, uid, [('stock_move_id','in',ids)])
		demand_line_obj.write(cr, uid, demand_line_ids, {
			'state': 'requested'
		})
		return result