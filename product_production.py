from openerp import api
from openerp.osv import osv, fields
from openerp.tools.translate import _


class product_production(osv.osv):
	_inherit = "product.production"
	
	def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
		employee_obj = self.pool.get('hr.employee')
		employee = employee_obj.browse(cr, uid, employee_id)
		return { 'value': { 'location_id': employee.user_id.branch_id.default_incoming_location_id.id }}