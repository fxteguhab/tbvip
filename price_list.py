from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

# ==========================================================================================================================
class price_list_line_product(osv.osv):
	_inherit = 'price.list.line.product'
	
# OVERRIDE ------------------------------------------------------------------------------------------------------------------
	
	def onchange_product_template_id(self, cr, uid, ids, product_template_id, context=None):
		res = super(price_list_line_product, self).onchange_product_template_id(cr, uid, ids, product_template_id, context)
		res = self._update_uom_domain(res)
		return res
	
# METHOD ------------------------------------------------------------------------------------------------------------------
	
	def _update_uom_domain(self, onchange_result):
		if onchange_result.get('domain', False):
			if onchange_result['domain'].get('product_uom', False):
				onchange_result['domain']['uom_id_1'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_2'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_3'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_4'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_5'].append(('is_auto_create', '=', False))
			else:
				onchange_result['domain']['uom_id_1'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_2'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_3'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_4'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_5'] = [('is_auto_create', '=', False)]
		else:
			onchange_result.update({'domain': {'uom_id_1': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_2': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_3': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_4': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_5': [('is_auto_create', '=', False)]}})
		return onchange_result
		
# ==========================================================================================================================

class price_list_line_category(osv.osv):
	_inherit = 'price.list.line.category'

# OVERRIDE ------------------------------------------------------------------------------------------------------------------
	def onchange_product_category_id(self, cr, uid, ids, product_category_id, context=None):
		res = super(price_list_line_category, self).onchange_product_category_id(cr, uid, ids, product_category_id, context)
		res = self._update_uom_domain(res)
		return res
	
# METHOD ------------------------------------------------------------------------------------------------------------------
	
	def _update_uom_domain(self, onchange_result):
		if onchange_result.get('domain', False):
			if onchange_result['domain'].get('product_uom', False):
				onchange_result['domain']['uom_id_1'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_2'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_3'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_4'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_5'].append(('is_auto_create', '=', False))
			else:
				onchange_result['domain']['uom_id_1'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_2'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_3'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_4'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_5'] = [('is_auto_create', '=', False)]
		else:
			onchange_result.update({'domain': {'uom_id_1': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_2': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_3': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_4': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_5': [('is_auto_create', '=', False)]}})
		return onchange_result
	
# ==========================================================================================================================

class product_current_price(osv.osv):
	_inherit = 'product.current.price'
	
# OVERRIDE ------------------------------------------------------------------------------------------------------------------
	def onchange_product_id(self, cr, uid, ids, product_category_id, context=None):
		res = super(product_current_price, self).onchange_product_id(cr, uid, ids, product_category_id, context)
		res = self._update_uom_domain(res)
		return res
	
# METHOD ------------------------------------------------------------------------------------------------------------------
	
	def _update_uom_domain(self, onchange_result):
		if onchange_result.get('domain', False):
			if onchange_result['domain'].get('product_uom', False):
				onchange_result['domain']['uom_id_1'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_2'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_3'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_4'].append(('is_auto_create', '=', False))
				onchange_result['domain']['uom_id_5'].append(('is_auto_create', '=', False))
			else:
				onchange_result['domain']['uom_id_1'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_2'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_3'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_4'] = [('is_auto_create', '=', False)]
				onchange_result['domain']['uom_id_5'] = [('is_auto_create', '=', False)]
		else:
			onchange_result.update({'domain': {'uom_id_1': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_2': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_3': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_4': [('is_auto_create', '=', False)]}})
			onchange_result.update({'domain': {'uom_id_5': [('is_auto_create', '=', False)]}})
		return onchange_result
		
# ==========================================================================================================================