from openerp.osv import osv, fields


# ==========================================================================================================================

class canvassing_canvas(osv.osv):
	_inherit = 'canvassing.canvas'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
	# ONCHANGE ---------------------------------------------------------------------------------------------------------------
	
	def onchange_branch_id(self, cr, uid, ids, branch_id, context=None):
		# TODO
		# mengisi otomatis canvas.stock.line dengan semua stock.picking yang belum Transferred dan berasal dari
		# purchase yang diantar atau sales yang diantar, dan purchase serta sales itu berasal dari cabang yang dipilih.
		# User tinggal menghapus yang ngga perlu untuk trip tsb. canvas.invoice.line TIDAK perlu diisi otomatis
		# context = {} if context is None else None
		# product_obj = self.pool.get('product.product')
		# result = ''
		# for product in product_obj.browse(cr, uid, [product_id], context):
		# 	for product_sublocation_id in product.product_sublocation_ids:
		# 		sublocation = product_sublocation_id.sublocation_id
		# 		result += product_sublocation_id.branch_id.name + ' / ' + sublocation.full_name + '\r\n'
		# return {'value': {'sublocation': result}}
		pass

# ==========================================================================================================================
