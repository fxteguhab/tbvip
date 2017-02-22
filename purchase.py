from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

# ==========================================================================================================================

class purchase_order(osv.osv):
	
	_inherit = 'purchase.order'
	
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
	# langsung terima juga barangnya
	# 	if context.get('direct_receive', False):
	# 		purchase_data = self.browse(cr, uid, new_id)
	# 		receive_obj = self.pool.get('stock.picking')
	# 		picking_ids = [picking.id for picking in purchase_data.picking_ids]
	# 		receive_obj.action_done(cr, uid, picking_ids)
		return new_id

