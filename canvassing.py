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
		context = {} if context is None else context
		po_obj = self.pool.get('purchase.order')
		so_obj = self.pool.get('sale.order')
		
		# Get picking ids from Purchase Orders
		po_ids = po_obj.search(cr, uid, [('branch_id', '=', branch_id), ('state', '=', 'approved')], context)
		picking_ids = []
		for po in po_obj.browse(cr, uid, po_ids, context):
			for picking in po.picking_ids:
				if picking.state == 'assigned':
					picking_ids.append(picking)
		
		# Get picking ids from Sales Orders
		so_ids = so_obj.search(cr, uid, [('branch_id', '=', branch_id), ('state', 'in', ['approved', 'progress'])], context)
		for so in so_obj.browse(cr, uid, so_ids, context):
			for picking in so.picking_ids:
				if picking.state == 'assigned':
					picking_ids.append(picking)
		
		# Pool result
		canvas_stock_line_vals = []
		for picking_id in picking_ids:
			canvas_stock_line_vals.append((0, False, {
				'stock_picking_id': picking_id.id,
				'address': picking_id.partner_id.street,
			}))
		
		return {'value': {'canvas_stock_line': canvas_stock_line_vals}}
	
	def view_picking(self, cr, uid, branch_id, context=None):
		"""
		Returns existing picking orders of given purchase order ids.
		"""
		context = {} if context is None else context
		
		po_obj = self.pool.get('purchase.order')
		po_ids = po_obj.search(cr, uid, [('branch_id', '=', branch_id)], context)
		picking_ids = []
		for po in po_obj.browse(cr, uid, po_ids, context):
			picking_ids += [picking.id for picking in po.picking_ids]
		return picking_ids

# ==========================================================================================================================
