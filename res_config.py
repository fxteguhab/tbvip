from openerp.osv import osv

# ==========================================================================================================================

class sale_configuration(osv.TransientModel):
	_inherit = 'sale.config.settings'
	
	_defaults = {
		'group_uom': True,
		'group_discount_per_so_line': True,
	}