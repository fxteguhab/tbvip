from openerp.osv import osv, fields
from datetime import datetime
from datetime import timedelta

import margin_utility

class product_template(osv.osv):
	_inherit = 'product.template'

# ATTRIBUTES -------------------------------------------------------------------------------------------------------------
	_max_margin = 3

	_columns = {
		'margin_string' : fields.char('Margin'),
		'margin_value': fields.function(_calc_margin, string="Margin Value", readonly=True)
	}

	

class product_category(osv.osv):
	_inherit = 'product.category'
	_columns = {
		'margin_string' : fields.char('Margin'),
		'margin_value': fields.function(_calc_margin, string="Margin Value", readonly=True)
	}


	