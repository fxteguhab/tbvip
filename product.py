from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

# ==========================================================================================================================

class product_category(osv.osv):
	
	_inherit = 'product.category'

# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
	}
	
# ORDER --------------------------------------------------------------------------------------------------------------------
	
	#_order = 'parent_id, codex_id'

# ==========================================================================================================================

class product_template(osv.osv):
	
	_inherit = 'product.template'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'codex_id': fields.integer('MySQL Product ID'),
	}
	
	def create(self, cr, uid, vals, context={}):
		new_id = super(product_template, self).create(cr, uid, vals, context)
	# waktu create product baru, samakan variant_codex_id anak-anaknya dengan codex_id parent
		new_data = self.browse(cr, uid, new_id, context=context)
		product_obj = self.pool.get('product.product')
		for variant in new_data.product_variant_ids:
			product_obj.write(cr, uid, [variant.id], {
				'variant_codex_id': new_data.codex_id,
			})
		return new_id
	
# ==========================================================================================================================

class product_product(osv.osv):
	
	_inherit = 'product.product'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'variant_codex_id': fields.integer('MySQL Variant Product ID'),
	}
