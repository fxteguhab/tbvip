from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

import utility

# ==========================================================================================================================
class price_list_line_product(osv.osv):
	_inherit = 'price.list.line.product'
	
# OVERRIDE ------------------------------------------------------------------------------------------------------------------
	
	def onchange_product_template_id(self, cr, uid, ids, product_template_id, context=None):
		res = super(price_list_line_product, self).onchange_product_template_id(cr, uid, ids, product_template_id, context)
		res = utility.update_uom_domain_price_list(res)
		return res

# ==========================================================================================================================

class price_list_line_category(osv.osv):
	_inherit = 'price.list.line.category'

# OVERRIDE ------------------------------------------------------------------------------------------------------------------
	def onchange_product_category_id(self, cr, uid, ids, product_category_id, context=None):
		res = super(price_list_line_category, self).onchange_product_category_id(cr, uid, ids, product_category_id, context)
		res = utility.update_uom_domain_price_list(res)
		return res

# ==========================================================================================================================

class product_current_price(osv.osv):
	_inherit = 'product.current.price'
	
# OVERRIDE ------------------------------------------------------------------------------------------------------------------
	def onchange_product_id(self, cr, uid, ids, product_category_id, context=None):
		res = super(product_current_price, self).onchange_product_id(cr, uid, ids, product_category_id, context)
		res = utility.update_uom_domain_price_list(res)
		return res
# ==========================================================================================================================