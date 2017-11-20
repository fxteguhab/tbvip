from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _

# ==========================================================================================================================

class tbvip_interbranch_stock_move(osv.Model):
	_name = 'tbvip.interbranch.stock.move'
	_description = 'Stock Move between branches'
	_inherit = ['mail.thread']
	_order = "move_date DESC, id DESC"
	
	# COLUMNS --------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'from_stock_location_id': fields.many2one('stock.location', 'Incoming Location', required=True),
		'to_stock_location_id': fields.many2one('stock.location', 'Outgoing Location', required=True),
		'input_user_id': fields.many2one('res.users', 'Input by', required=True),
		'prepare_employee_id':  fields.many2one('hr.employee', 'Prepared by', required=True),
		'move_date': fields.datetime('Move Date', required=True),
		'state': fields.selection([
			('draft', 'Draft'),
			('accepted', 'Accepted'),
			('rejected', 'Rejected')]
			, 'State', readonly=True),
		'accepted_by_user_id': fields.many2one('res.users', 'Accepted by'),
		'interbranch_stock_move_line_ids': fields.one2many('tbvip.interbranch.stock.move.line', 'header_id', 'Move Lines'),
	}
	
	_defaults = {
		'from_stock_location_id': lambda self, cr, uid, ctx:
			self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_outgoing_location_id.id,
		'input_user_id': lambda self, cr, uid, ctx: uid,
		'move_date': datetime.now(),
		'state': 'draft',
	}
	
	# OVERRIDES ------------------------------------------------------------------------------------------------------------

	
	
	
	# METHODS --------------------------------------------------------------------------------------------------------------
	
	def action_accept(self, cr, uid, ids, context=None):
		pass
	
	def action_reject(self, cr, uid, ids, context=None):
		pass

# ==========================================================================================================================

class tbvip_interbranch_stock_move_line(osv.Model):
	_name = 'tbvip.interbranch.stock.move.line'
	_description = 'Detail Stock Move between branches'
	
	# COLUMNS --------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'header_id': fields.many2one('tbvip.interbranch.stock.move', 'Interbranch Stock Move'),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'qty': fields.float('Quantity', required=True),
		'uom_id': fields.many2one('product.uom', 'Product UoM', required=True),
		'is_changed': fields.boolean('Is Changed?'),
		'move_date': fields.related('header_id', 'move_date', type="datetime", string="Move Date"),
		'notes': fields.text('Notes'),
	}
	
	_defaults = {
		'is_changed': False,
	}
	
	# OVERRIDES ------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		new_id = super(tbvip_interbranch_stock_move_line, self).create(cr, uid, vals, context)
		# when created, message post to header
		tbvip_interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		if vals.get('header_id', False):
			product_obj = self.pool.get('product.product')
			new_product = product_obj.browse(cr, uid, vals['product_id'], context=context)
			tbvip_interbranch_stock_move_obj.message_post(cr, uid, vals['header_id'],
				body=_("New line added: %s %s %s") % (new_product.name, vals['qty'], vals['uom_id']))
		return new_id
	
	def write(self, cr, uid, ids, vals, context=None):
		# if there are any changes, message post to header
		tbvip_interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		product_obj = self.pool.get('product.product')
		for line in self.browse(cr, uid, ids, context=context):
			if vals.get('header_id', False):
				product_obj = self.pool.get('product.product')
				new_product = product_obj.browse(cr, uid, vals['product_id'], context=context)
				tbvip_interbranch_stock_move_obj.message_post(cr, uid, vals['header_id'],
					body=_("New line added: %s - %s %s") % (new_product.name, vals['qty'], vals['uom_id']))
			if vals.get('product_id', False):
				new_product = product_obj.browse(cr, uid, vals['product_id'], context=context)
				tbvip_interbranch_stock_move_obj.message_post(cr, uid, line.header_id.id,
					body=_("Product \"%s\" changed into \"%s\"") % (line.product_id.name, new_product.name))
			if vals.get('qty', False):
				tbvip_interbranch_stock_move_obj.message_post(cr, uid, line.header_id.id,
					body=_("There is a change on quantity for product \"%s\" from %s to %s") %
						 (line.product_id.name, line.qty, vals['qty']))
			# any changes, if uid not the same as header_id.input_user_id.id, then set is_changed to True
			if not vals.get('is_changed', False):
				if uid != line.header_id.input_user_id.id:
					self.write(cr, uid, line.id, {
						'is_changed': True,
					}, context=context)
		return super(tbvip_interbranch_stock_move_line, self).write(cr, uid, ids, vals, context)
	
	def unlink(self, cr, uid, ids, context=None):
		# when deleted, message post to header
		tbvip_interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		for line in self.browse(cr, uid, ids, context=context):
			tbvip_interbranch_stock_move_obj.message_post(cr, uid, line.header_id.id,
				body=_("Line removed: %s - %s %s") % (line.product_id.name, line.qty, line.uom_id.name))
		return super(tbvip_interbranch_stock_move_line, self).unlink(cr, uid, ids, context)
	
	# METHODS --------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		return {
			'value': {'uom_id': product.product_tmpl_id.uom_id.id},
			'domain': {'uom_id': [('category_id','=', product.product_tmpl_id.uom_id.category_id.id)]}
		}