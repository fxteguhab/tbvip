from openerp.osv import osv, fields

class purchase_needs_algorithm(osv.osv):

	_inherit = 'mail.thread'
	_name = 'tbvip.purchase.needs.algorithm'
	_description = 'Purchase Needs Algorithm'

	def create(self, cr, uid, vals, context={}):
		result = super(purchase_needs_algorithm, self).create(cr, uid, vals, context)
		data = self.browse(cr, uid, result)
		print data
	
	_columns = {
		'name': fields.char('Name', required=True, track_visibility='onchange'),
		'is_used': fields.boolean('Is Used', track_visibility='onchange'),
		'algorithm': fields.text('Address', required=True),
	}
	
	_defaults = {
		'is_used': False,
	}