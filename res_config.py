from openerp.osv import fields, osv


class sale_configuration(osv.TransientModel):
	_inherit = 'sale.config.settings'
	
	_columns = {
		'purchase_needs_latest_sale': fields.integer('Purchase Needs Latest Sales',
			help="Calculate product ranking from n day(s) latest sales."),
	}
	
	def default_get(self, cr, uid, fields, context=None):
		res = super(sale_configuration, self).default_get(cr, uid, fields, context=context)
		purchase_needs_latest_sale = self.pool.get('ir.config_parameter').get_param(cr, uid, 'purchase_needs_latest_sale', None)
		if purchase_needs_latest_sale is not None:
			res['purchase_needs_latest_sale'] = int(purchase_needs_latest_sale)
		return res
	
	def set_sale_defaults(self, cr, uid, ids, context=None):
		super(sale_configuration, self).set_sale_defaults(cr, uid, ids, context=context)
		config_param_obj = self.pool.get('ir.config_parameter')
		config = self.browse(cr, uid, ids[0], context)
		# setting params
		purchase_needs_latest_sale = config.purchase_needs_latest_sale if config.purchase_needs_latest_sale else '0'
		config_param_obj.set_param(cr, uid, 'purchase_needs_latest_sale', purchase_needs_latest_sale)