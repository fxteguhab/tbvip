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
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True), 
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
			self.signal_workflow(cr, uid, [new_id], 'purchase_confirm')
		# langsung validate juga invoicenya
			invoice_obj = self.pool.get('account.invoice')
			for invoice in purchase_data.invoice_ids:
				invoice_obj.write(cr, uid, [invoice.id], {
					'date_invoice': purchase_data.date_order,
				})
				invoice_obj.signal_workflow(cr, uid, [invoice.id], 'invoice_open')
	# langsung terima juga barangnya
		if context.get('direct_receive', False):
			purchase_data = self.browse(cr, uid, new_id)
			receive_obj = self.pool.get('stock.picking')
			picking_ids = [picking.id for picking in purchase_data.picking_ids]
			receive_obj.action_done(cr, uid, picking_ids)
		return new_id

# ==========================================================================================================================

class purchase_order_line(osv.osv):
	
	_inherit = 'purchase.order.line'

# FIELD FUNCTION METHODS ---------------------------------------------------------------------------------------------------

	def _price_unit_nett(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for data in self.browse(cr, uid, ids):
			result[data.id] = data.price_unit - (data.disc1 + data.disc2 + data.disc3 + data.disc4 + data.disc5)
		return result
	
	def _purchase_hour(self, cr, uid, ids, field_name, arg, context={}):
		result = {}
		for data in self.browse(cr, uid, ids):
			purchase_date = datetime.strptime(data.date_order,'%Y-%m-%d %H:%M:%S')
			result[data.id] = purchase_date.hour * 3600 + purchase_date.minute * 60
		return result

	def _calc_line_base_price(self, cr, uid, line, context=None):
		return line.price_unit_nett
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_purchase_det_id': fields.integer('MySQL Purchase Detail ID'),
		'disc1': fields.float('Disc. 1'),
		'disc2': fields.float('Disc. 2'),
		'disc3': fields.float('Disc. 3'),
		'disc4': fields.float('Disc. 4'),
		'disc5': fields.float('Disc. 5'),
		'price_unit_nett': fields.function(_price_unit_nett, method=True, string='Unit Price (Nett)', type='float'),
		'purchase_hour': fields.function(_purchase_hour, method=True, string='Purchase Hour', type='float'),
		'alert': fields.integer('Alert'),
	}
	
	_defaults = {
		'alert': 0,
		'disc1': 0,
		'disc2': 0,
		'disc3': 0,
		'disc4': 0,
		'disc5': 0,
	}

