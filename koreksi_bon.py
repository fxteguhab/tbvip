from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _

# ==========================================================================================================================

class koreksi_bon(osv.osv):
	_name = 'koreksi.bon'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'sale_order_id': fields.many2one('sale.order', 'Sale Order', required=True),
		'order_line': fields.one2many('sale.order.line', 'koreksi_bon_id', 'Order Lines'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', readonly=True),
		'date_order': fields.date('Date Order', readonly=True),
		'bon_number': fields.char('Bon Number', readonly=True),
		'partner_id': fields.many2one('res.partner', 'Customer', readonly=True),
		'price_type_id': fields.many2one('price.type', 'Price Type', readonly=True),
		'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),
		'shipped_or_taken': fields.selection([
			('shipped', 'Shipped'),
			('taken', 'Taken')
		], 'Shipped or Taken', readonly=True),
		'client_order_ref': fields.char('Reference/Description', readonly=True)
	}
	
	def onchange_sale_order_id(self, cr, uid, ids, sale_order_id, context=None):
		if sale_order_id:
			sale_order_obj = self.pool.get('sale.order')
			sale_order = sale_order_obj.browse(cr, uid, sale_order_id)
			order_lines = []
			for order_line in sale_order.order_line:
				order_lines.append(order_line.id)
			return {
				'value': {
					'branch_id': sale_order.branch_id.id,
					'date_order': sale_order.date_order,
					'bon_number': sale_order.bon_number,
					'partner_id': sale_order.partner_id.id,
					'price_type_id': sale_order.price_type_id.id,
					'employee_id': sale_order.employee_id.id,
					'shipped_or_taken': sale_order.shipped_or_taken,
					'client_order_ref': sale_order.client_order_ref,
					'order_line': order_lines,
				}
			}
		return
	
	def action_save_koreksi_bon(self, cr, uid, ids, context=None):
		return

class sale_order_line(osv.osv):
	_inherit = 'sale.order.line'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'state': fields.selection([
			('draft', 'Draft'),
		], 'State', readonly=True),
		'koreksi_bon_id': fields.many2one('koreksi.bon', 'Koreksi Bon'),
	}