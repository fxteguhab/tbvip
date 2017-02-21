from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta
from openerp import SUPERUSER_ID

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

# OVERRIDES ----------------------------------------------------------------------------------------------------------------

	# to also update the price_unit_nett when the product_id is changed
	# def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
	# 						partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
	# 						name=False, price_unit=False, state='draft', context=None):
	# 	result = super(purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
	# 									  partner_id, date_order, fiscal_position_id, date_planned,
	# 									  name, price_unit, state, context)
	# 	result['value'].update({'price_unit_nett': self._calculate_price_unit_nett(cr, uid, ids)})
	# 	return result

	def create(self, cr, uid, data, context=None):
		new_order_line = super(purchase_order_line, self).create(cr, uid, data, context)
		if 'product_id' in data and data['product_id'] and 'price_unit' in data and data['price_unit']:
			product_obj = self.pool.get('product.product')
			product = product_obj.browse(cr, uid, data['product_id'])
			if product.standard_price > 0 and data['price_unit'] != product.standard_price:
				purchase_order_obj = self.pool.get('purchase.order')
				purchase_order = purchase_order_obj.browse(cr, uid, data['order_id'])
				# message post to SUPERUSER
				purchase_order_obj.message_post(cr, SUPERUSER_ID, purchase_order.id,
					body=_("Ada perubahan harga beli untuk produk "+product.name+" di PO "+purchase_order.name), context=context)
				# message post to all users in group Purchases Manager
				group_obj = self.pool.get('res.groups')
				purchase_group_ids = group_obj.search(cr, uid, [('category_id.name', '=', 'Purchases'),('name', '=', 'Manager')])
				for user in group_obj.browse(cr, uid, purchase_group_ids).users:
					purchase_order_obj.message_post(cr, user.id, purchase_order.id,
						body=_("Ada perubahan harga beli untuk produk "+product.name+" di PO "+purchase_order.name), context=context)
		return new_order_line

	def write(self, cr, uid, ids, data, context=None):
		edited_order_line = super(purchase_order_line,self).write(cr, uid, ids, data, context)
		if 'product_id' in data and data['product_id'] and 'price_unit' in data and data['price_unit']:
			product_obj = self.pool.get('product.product')
			product = product_obj.browse(cr, uid, data['product_id'])
			if product.standard_price > 0 and data['price_unit'] != product.standard_price:
				purchase_order_obj = self.pool.get('purchase.order')
				purchase_order = purchase_order_obj.browse(cr, uid, data['order_id'])
				# message post to SUPERUSER
				purchase_order_obj.message_post(cr, SUPERUSER_ID, purchase_order.id,
												body=_("Ada perubahan harga beli untuk produk "+product.name+" di PO "+purchase_order.name), context=context)
				# message post to all users in group Purchases Manager
				group_obj = self.pool.get('res.groups')
				purchase_group_ids = group_obj.search(cr, uid, [('category_id.name', '=', 'Purchases'),('name', '=', 'Manager')])
				for user in group_obj.browse(cr, uid, purchase_group_ids).users:
					purchase_order_obj.message_post(cr, user.id, purchase_order.id,
													body=_("Ada perubahan harga beli untuk produk "+product.name+" di PO "+purchase_order.name), context=context)
		return edited_order_line

# FIELD FUNCTION METHODS ---------------------------------------------------------------------------------------------------

	def _price_unit_nett(self, cr, uid, ids, field_name={}, arg={}, context={}):
		print "I am called"
		result = {}
		for data in self.browse(cr, uid, ids):
			result[data.id] = self._calculate_price_unit_nett(cr, uid, ids, data)
		return result

	def _calculate_price_unit_nett(self, cr, uid, ids, data):
		return data.price_unit - (data.disc1 + data.disc2 + data.disc3 + data.disc4 + data.disc5)
	
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

