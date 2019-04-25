from openerp.osv import osv, fields
from openerp.tools.translate import _


class product_conversion(osv.osv):
	_inherit = "product.conversion"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'categ_id' : fields.char(related = "product_template_id.categ_id.name",string="Category",store=True),
	}
	
	