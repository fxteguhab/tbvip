from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

import utility

class product_current_price(osv.osv):
	_inherit = 'product.current.price'
	
# OVERRIDE ------------------------------------------------------------------------------------------------------------------
	def onchange_product_id(self, cr, uid, ids, product_category_id, context=None):
		res = super(product_current_price, self).onchange_product_id(cr, uid, ids, product_category_id, context)
		res = utility.update_uom_domain_price_list(res)
		return res
# ==========================================================================================================================