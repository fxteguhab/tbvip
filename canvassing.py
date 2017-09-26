from openerp.osv import osv, fields
import urllib2
import json
import requests
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, date, timedelta

# ==========================================================================================================================

class canvassing_canvas(osv.osv):
	_inherit = 'canvassing.canvas'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		'total_distance': fields.float('Total Distance', readonly=True),
	}
	
	# OVERRIDES --------------------------------------------------------------------------------------------------------------
		
	def calculate_distance(self, cr, uid, canvas_data):
	# ambil parameter2 sistem
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['gps_base_url','gps_login_path','gps_positions_url','gps_devices_url','gps_username','gps_password'])])
		baseUrl = ""
		login_url = ""
		positions_url = ""
		devices_url = ""
		gps_username = ""
		gps_password = ""
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'gps_base_url':
				baseUrl = param_data.value
			elif param_data.key == 'gps_login_path':
				login_url = baseUrl + param_data.value
			elif param_data.key == 'gps_positions_url':
				positions_url = baseUrl + param_data.value
			elif param_data.key == 'gps_devices_url':
				devices_url = baseUrl + param_data.value
			elif param_data.key == 'gps_username':
				gps_username = param_data.value
			elif param_data.key == 'gps_password':
				gps_password = param_data.value
	# coba login ke sistem GPS
		try:
			request = urllib2.Request(login_url + '?payload=["'+gps_username+'","'+gps_password+'"]')
			response = urllib2.urlopen(request)
			cookie = response.headers.get('Set-Cookie')
		except:
			return -1 # -1 artinya error
	# tentukan device id dari vehicle yang melakukan canvassing ini
		vehicle_gps_id = canvas_data.fleet_vehicle_id and canvas_data.fleet_vehicle_id.gps_id or None
		if not vehicle_gps_id:
			raise osv.except_osv(_('Canvassing Error'),_('This canvassing trip does not have a vehicle or its GPS ID is invalid.'))
		request = urllib2.Request(devices_url)
		request.add_header('Cookie', cookie)
		response = urllib2.urlopen(request)
		j = json.load(response)
		device_id = None
		for i in j:
			if (vehicle_gps_id == i['uniqueId']) :
				device_id = i['id'] 
				break
		if not device_id:
			raise osv.except_osv(_('Canvassing Error'),_('This canvassing trip does not have a vehicle or its GPS ID is invalid.'))
	# ambil jarak antara waktu mulai dan selesai
		date_depart = datetime.strptime(canvas_data.date_depart, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=7)
		date_delivered = datetime.strptime(canvas_data.date_delivered, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=7)
		date_depart = date_depart.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
		date_delivered = date_delivered.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
		header = {'cookie': cookie}
		data = '[{"id":%s},"%s","%s",true]' % (device_id,date_depart+" +0700",date_delivered+' +0700')
		results = requests.post(positions_url, headers=header, data=data)
		j = results.json()
		if not j: return 0
	# find substring in 'other' group in first iterasion
		substr = j[0]['other']
		dist_pos = substr.find('totalDistance')
		pos1 = substr.find(':',dist_pos) 
		pos2 = substr.find('}',dist_pos)
		start_distance = substr[pos1+1:pos2]
	# trace to last index
		index = 0
		for i in j: index += 1
	# find substring in 'other' group in last iteration
		substr = j[index-1]['other']
		dist_pos = substr.find('totalDistance')
		pos1 = substr.find(':',dist_pos) 
		pos2 = substr.find('}',dist_pos)
		last_distance = substr[pos1+1:pos2]
	# inilah jaraknya!
		return float(last_distance) - float(start_distance)

	def action_recalculate_distance(self, cr, uid, ids, context={}):
		for canvas_data in self.browse(cr, uid, ids, context=context):
			distance = self.calculate_distance(cr, uid, canvas_data)
			self.write(cr, uid, [canvas_data.id], {
				'total_distance': distance,
				})
		return True

	def action_set_finish(self, cr, uid, ids, context={}):
		super(canvassing_canvas, self).action_set_finish(cr, uid, ids, context=context)
		return self.action_recalculate_distance(cr, uid, ids)
	
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
	_inherit = 'canvassing.canvas.invoice.line'
	
	_columns = {
		'bon_number': fields.char('Bon Number', required=True),
	}
	
	def onchange_bon_number(self, cr, uid, ids, bon_number, context=None):
		result = {}
		result['value'] = {}
		if bon_number:
			sale_order = self.pool.get('sale.order')
			sale_order_ids = sale_order.search(cr, uid, [
				('bon_number', '=', bon_number),
			], limit=1, order='date_order DESC')
			sale_order_data = sale_order.browse(cr, uid, sale_order_ids)
			if len(sale_order_data) > 0:
				if len(sale_order_data[0].invoice_ids) > 0:
					result['value'].update({
						'invoice_id': sale_order_data[0].invoice_ids[0].id
					})
				else:
					result['warning'] = {
						'title': 'Bon Number Error',
						'message': 'You must confirm the sales order first.',
					}
			else:
				result['warning'] = {
					'title': 'Bon Number Error',
					'message': 'No sales order found with the given bon number.',
				}
		return result


"""
20170924 JUNED: ditutup karena perhitungan jarak dikondisikan untuk satu perjalanan secara 
keseluruhan, menggunakan API dari service GPS yang dipakai
dengan demikian, perhitungan total_distance di model canvassing.canvas tidak tergantung pada 
nilai field distance di canvas.stock.line

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
"""