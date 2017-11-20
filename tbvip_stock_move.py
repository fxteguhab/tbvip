from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _
from lxml import etree

# ==========================================================================================================================

class tbvip_interbranch_stock_move(osv.Model):
	_name = 'tbvip.interbranch.stock.move'
	_description = 'Stock Move between branches'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'from_stock_location_id': fields.many2one('stock.location', 'Incoming Location', required=True),
		'to_stock_location_id': fields.many2one('stock.location', 'Outgoing Location', required=True),
		'input_user_id': fields.many2one('res.users', 'Input by', required=True),
		'prepare_employee_id':  fields.many2one('hr.employee', 'Prepared by', required=True),
		'move_date': fields.datetime('Move Date'),
		'state': fields.selection([
			('draft', 'Draft'),
			('accepted', 'Accepted'),
			('rejected', 'Rejected')]
			, 'State', readonly=True),
		'accepted_by_user_id': fields.many2one('res.users', 'Accepted by'),
		'interbranch_stock_move_line_ids': fields.one2many('koreksi.bon.sale.order.line', 'koreksi_bon_id', 'Order Lines'),
	}
	
	_defaults = {
		'from_stock_location_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_outgoing_location_id.id,
		'state': 'draft',
	}


# ==========================================================================================================================

class tbvip_interbranch_stock_move_line(osv.Model):
	_name = 'tbvip.interbranch.stock.move.line'
	_description = 'Detail Stock Move between branches'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'header_id': fields.many2one('tbvip.interbranch.stock.move', 'Interbranch Stock Move'),
		'product_id': fields.many2one('stock.location', 'Incoming Location', required=True),
		'qty': fields.many2one('stock.location', 'Outgoing Location', required=True),
		'uom_id': fields.many2one('res.users', 'Input by', required=True),
		'notes':  fields.many2one('hr.employee', 'Prepared by', required=True),
		'is_changed': fields.boolean('Is Changing?'),
		'move_date': fields.related('move_date', relation='tbvip.interbranch.stock.move', type='datetime',
			string='Move Date', readonly=True)
	}
	
	
	# ==========================================================================================================================