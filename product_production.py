from openerp import api
from openerp.osv import osv, fields
from openerp.tools.translate import _


class product_production(osv.osv):
	_inherit = "product.production"
	
	def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
		employee_obj = self.pool.get('hr.employee')
		employee = employee_obj.browse(cr, uid, employee_id)
		return { 'value': { 'location_id': employee.user_id.branch_id.default_incoming_location_id.id }}
		
# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		new_id = super(product_production, self).create(cr, uid, vals, context)
		confirm = self.action_confirm(cr, uid, new_id, context)
		finish = self.action_finish(cr, uid, new_id, context)
		return new_id

# ===========================================================================================================================

class product_production_finished(osv.osv):
	_inherit = "product.production.finished"
	
# ONCHANGE ---------------------------------------------------------------------------------------------------------------
	
	def onchange_product_uom(self, cr, uid, ids, product, uom=False, context= {}):
		product_conversion_obj = self.pool.get('product.conversion')
		uom_record = product_conversion_obj.get_conversion_auto_uom(cr, uid, product, uom)
		result = {'value': {
			'uom_id': uom_record.id,
		}}
		return result
		
# ===========================================================================================================================

class product_production_raw(osv.osv):
	_inherit = "product.production.raw"
	
# ONCHANGE ---------------------------------------------------------------------------------------------------------------
	
	def onchange_product_uom(self, cr, uid, ids, product, uom=False, context= {}):
		product_conversion_obj = self.pool.get('product.conversion')
		uom_record = product_conversion_obj.get_conversion_auto_uom(cr, uid, product, uom)
		result = {'value': {
			'uom_id': uom_record.id,
		}}
		return result
		
# ===========================================================================================================================