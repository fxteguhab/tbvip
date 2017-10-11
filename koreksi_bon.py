from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _

# ==========================================================================================================================

class koreksi_bon(osv.osv_memory):
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
		'customer_address': fields.char('Customer Address'),
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
				# order_lines.append([0, False,{
				# 	'name': 'name',
				# 	'state': order_line.state,
				# 	'product_id': order_line.product_id.id,
				# 	'price_type_id': order_line.price_type_id.id,
				# 	'product_uom_qty': order_line.product_uom_qty,
				# 	'product_uom': order_line.product_uom.id,
				# 	'price_unit': order_line.price_unit,
				# 	'discount_string': order_line.discount_string,
				# 	'price_subtotal': order_line.price_subtotal,
				# }])
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
		for koreksi_bon in self.browse(cr, uid, ids):
			sale_order_obj = self.pool.get('sale.order')
			koreksi_bon_log_obj = self.pool.get('koreksi.bon.log')
			
			order_lines = []
			for order_line in koreksi_bon.sale_order_id.order_line:
				order_lines.append([0, False,{
					'name': 'name',
					'state': order_line.state,
					'product_id': order_line.product_id.id,
					'price_type_id': order_line.price_type_id.id,
					'product_uom_qty': order_line.product_uom_qty,
					'product_uom': order_line.product_uom.id,
					'price_unit': order_line.price_unit,
					'discount_string': order_line.discount_string,
					'price_subtotal': order_line.price_subtotal,
				}])
			
			new_sale_order_id = sale_order_obj.create(cr, uid, {
				'name': 'Koreksi ' + koreksi_bon.sale_order_id.name,
				'branch_id': koreksi_bon.sale_order_id.branch_id.id,
				'date_order': koreksi_bon.sale_order_id.date_order,
				'bon_number': koreksi_bon.sale_order_id.bon_number,
				'partner_id': koreksi_bon.sale_order_id.partner_id.id,
				'price_type_id': koreksi_bon.sale_order_id.price_type_id.id,
				'employee_id': koreksi_bon.sale_order_id.employee_id.id,
				'shipped_or_taken': koreksi_bon.sale_order_id.shipped_or_taken,
				'client_order_ref': koreksi_bon.sale_order_id.client_order_ref,
				'customer_address': koreksi_bon.sale_order_id.customer_address,
				'order_line': order_lines,
			})
			
			koreksi_bon_log_obj.create(cr, uid, {
				'old_sale_order_id': koreksi_bon.sale_order_id.id,
				'new_sale_order_id': new_sale_order_id
			})
		return new_sale_order_id

class sale_order_line(osv.osv):
	_inherit = 'sale.order.line'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'koreksi_bon_id': fields.many2one('koreksi.bon', 'Koreksi Bon'),
	}

class koreksi_bon_log(osv.osv):
	_name = 'koreksi.bon.log'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'old_sale_order_id': fields.many2one('sale.order', 'Old Sale Order', required=True),
		'new_sale_order_id': fields.many2one('sale.order', 'New Sale Order', required=True),
	}