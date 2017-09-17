from openerp.osv import osv, fields
import google_maps

# ==========================================================================================================================

class canvassing_canvas(osv.osv):
	_inherit = 'canvassing.canvas'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		# 'total_distance': fields.float('Total Distance'),
	}
	
	# OVERRIDES
	
	def action_set_finish(self, cr, uid, ids, context={}):
		super(canvassing_canvas, self).action_set_finish(cr, uid, ids, context=context)
		# for canvas_data in self.browse(cr, uid, ids):
			# total_distance = 0
			# for stock_line_data in canvas_data.stock_line_ids:
			# 	if stock_line_data.is_executed:
			# 		total_distance += stock_line_data.distance
			# for invoice_line_data in canvas_data.invoice_line_ids:
			# 	if invoice_line_data.is_executed:
			# 		total_distance += invoice_line_data.distance
			# self.write(cr, uid, ids, {
			# 	'total_distance': total_distance,
			# })
	
	# ONCHANGE ---------------------------------------------------------------------------------------------------------------
	
	def onchange_branch_id(self, cr, uid, ids, branch_id, context=None):
		context = {} if context is None else context
		po_obj = self.pool.get('purchase.order')
		so_obj = self.pool.get('sale.order')
		
		# Get pickings from Purchase Orders
		po_ids = po_obj.search(cr, uid, [
			('branch_id', '=', branch_id), ('state', '=', 'approved'), ('shipped_or_taken', '=', 'taken')
		], context)
		picking_ids = []
		for po in po_obj.browse(cr, uid, po_ids, context):
			for picking in po.picking_ids:
				if picking.state == 'assigned':
					picking_ids.append(picking)
		
		# Get pickings from Sales Orders
		so_ids = so_obj.search(cr, uid, [
			('branch_id', '=', branch_id), ('state', 'in', ['approved', 'progress']), ('shipped_or_taken', '=', 'shipped')
		], context)
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

class canvasssing_canvas_stock_line(osv.Model):
	_inherit = 'canvassing.canvas.stock.line'

	# OVERRIDES -------------------------------------------------------------------------------------------------------------

	def create(self, cr, uid, vals, context={}):
		new_id = super(canvasssing_canvas_stock_line, self).create(cr, uid, vals, context)
		self._update_distance(cr, uid, [new_id])
		return new_id
	
	def write(self, cr, uid, ids, vals, context=None):
		result = super(canvasssing_canvas_stock_line, self).write(cr, uid, ids, vals, context)
		if vals.get('address',False):
			self._update_distance(cr, uid, ids)
		return result
	
	def _update_distance(self, cr, uid, stock_line_ids, context=None):
		google_map = google_maps.GoogleMaps()
		for obj in self.browse(cr, uid, stock_line_ids):
			if obj.address and obj.canvas_id.branch_id:
				self.write(cr, uid, [obj.id], {
					'distance': google_map.distance(obj.address,obj.canvas_id.branch_id.address,'driving',api='masukkan_google_api_key_yang_benar'),
				})
