from openerp.osv import fields, osv


class purchase_config_settings(osv.osv_memory):
	_inherit = 'purchase.config.settings'
	
	_columns = {
		'default_discount_algorithm': fields.boolean("Calculate discount from subtotal", default_model='purchase.order.line',
			help="Allows you to choose algorithm to calculate the discount. Check if discount is calculated from subtotal. Uncheck if discount is calculated from unit price."),
	}
