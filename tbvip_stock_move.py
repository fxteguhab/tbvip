from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _
from lxml import etree

# ==========================================================================================================================

class tbvip_interbranch_stock_move(osv.Model):
	_name = 'tbvip.interbranch.stock.move'
	_description = 'Stock Move between branches'
	_inherit = ['mail.thread']
	_order = "move_date DESC, id DESC"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'from_stock_location_id': fields.many2one('stock.location', 'Incoming Location', required=True),
		'to_stock_location_id': fields.many2one('stock.location', 'Outgoing Location', required=True),
		'input_user_id': fields.many2one('res.users', 'Input by', required=True),
		'prepare_employee_id':  fields.many2one('hr.employee', 'Prepared by', required=True),
		'move_date': fields.datetime('Move Date', required=True),
		'state': fields.selection([
			('draft', 'Draft'),
			('accepted', 'Accepeted'),
			('rejected', 'Rejected')]
			, 'State', readonly=True),
		'accepted_by_user_id': fields.many2one('res.users', 'Accepted by'),
		'interbranch_stock_move_line_ids': fields.one2many('tbvip.interbranch.stock.move.line', 'header_id', 'Move Lines'),
	}
	
	_defaults = {
		'from_stock_location_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_outgoing_location_id.id,
		'state': 'draft',
	}
	
	def action_accept(self, cr, uid, ids, context=None):
		pass
	
	def action_reject(self, cr, uid, ids, context=None):
		pass

# ==========================================================================================================================

class tbvip_interbranch_stock_move_line(osv.Model):
	_name = 'tbvip.interbranch.stock.move.line'
	_description = 'Detail Stock Move between branches'
	_order = "move_date DESC, id DESC"
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
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
	
	
	# ==========================================================================================================================
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		return {
			'value': {'uom_id': product.product_tmpl_id.uom_id.id},
			'domain': {'uom_id': [('category_id','=', product.product_tmpl_id.uom_id.category_id.id)]}
		}