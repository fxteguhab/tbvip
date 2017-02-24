from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

# ==========================================================================================================================

class purchase_order(osv.osv):
	
	_inherit = 'purchase.order'

	#Attributes
	_max_discount = 3
	
# FIELD FUNCTION METHODS ---------------------------------------------------------------------------------------------------

	def _alert(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for data in self.browse(cr, uid, ids):
			max_alert = -1
			for line in data.order_line:
				max_alert = max(max_alert, line.alert)
			result[data.id] = max_alert
		return result
		
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_purchase_id': fields.integer('MySQL Purchase ID'),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True,
									 states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)],
											 'done': [('readonly', True)]}),
		'cashier': fields.char('Cashier'),
		'general_discount': fields.float('Discount'),
		'alert': fields.function(_alert, method=True, type='integer', string="Alert", store=True),
		'adm_point': fields.float('Adm. Point'),
		'pickup_vehicle_id': fields.many2one('fleet.vehicle', 'Pickup Vehicle'),
		'driver_id': fields.many2one('hr.employee', 'Pickup Driver'),
		'need_id': fields.many2one('purchase.needs', 'Purchase Needs'),
	}

# OVERRIDES ----------------------------------------------------------------------------------------------------------------

	def create(self, cr, uid, vals, context={}):
		new_id = super(purchase_order, self).create(cr, uid, vals, context=context)
		# langsung confirm purchasenya bila diinginkan. otomatis dia bikin satu invoice dan satu incoming goods
		if context.get('direct_confirm', False):
			purchase_data = self.browse(cr, uid, new_id)
			self.signal_workflow(cr, uid, [new_id], 'purchase_confirm', context)
			# langsung validate juga invoicenya
			invoice_obj = self.pool.get('account.invoice')
			for invoice in purchase_data.invoice_ids:
				invoice_obj.write(cr, uid, [invoice.id], {
					'date_invoice': purchase_data.date_order,
				})
				invoice_obj.signal_workflow(cr, uid, [invoice.id], 'invoice_open', context)
		return new_id

# ==========================================================================================================================


class purchase_order_line(osv.osv):

	_inherit = 'purchase.order.line'

	def _message_cost_price_changed(self, cr, uid, data, product, order_id, context):
		if product.standard_price > 0 and data['price_unit'] != product.standard_price:
			purchase_order_obj = self.pool.get('purchase.order')
			purchase_order = purchase_order_obj.browse(cr, uid, order_id)
			# message post to SUPERUSER and all users in group Purchases Manager
			group_obj = self.pool.get('res.groups')
			purchase_manager_group_ids = group_obj.search(cr, uid,
														  [('category_id.name', '=', 'Purchases'),
														   ('name', '=', 'Manager')])
			partner_ids = [SUPERUSER_ID]
			for user in group_obj.browse(cr, uid, purchase_manager_group_ids).users:
				partner_ids += [user.partner_id.id]
			partner_ids = list(set(partner_ids))
			purchase_order_obj.message_post(cr, uid, purchase_order.id, context=context, partner_ids=partner_ids,
											body=_("There is a change on cost price for %s in %s Purchase Order")
												 % (product.name, purchase_order.name))

	def create(self, cr, uid, data, context=None):
		new_order_line = super(purchase_order_line, self).create(cr, uid, data, context)
		if 'product_id' in data and data['product_id'] and 'price_unit' in data and data['price_unit']:
			product_obj = self.pool.get('product.product')
			product = product_obj.browse(cr, uid, data['product_id'])
			self._message_cost_price_changed(cr, uid, data, product, data['order_id'], context)
		return new_order_line

	def write(self, cr, uid, ids, data, context=None):
		edited_order_line = super(purchase_order_line,self).write(cr, uid, ids, data, context)
		for id in ids:
			if 'price_unit' in data and data['price_unit']:
				product_obj = self.pool.get('product.product')
				product = product_obj.browse(cr, uid, self.browse(cr, uid, id).product_id.id)
				self._message_cost_price_changed(cr, uid, data, product, self.browse(cr, uid, id).order_id.id, context)
		return edited_order_line