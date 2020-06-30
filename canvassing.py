from openerp.osv import osv, fields
from openerp.tools.translate import _
import urllib2
import urllib
import json
import requests
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, date, timedelta


# ==========================================================================================================================

class canvassing_canvas(osv.osv):
	_inherit = 'canvassing.canvas'
	
	def _max_load_time(self, cr, uid, ids, field_name, arg, context=None):
		fmt = '%Y-%m-%d %H:%M:%S'
		result = {}
		for canvass in self.browse(cr, uid, ids, context=context):
			delta_list = []
			for line in canvass.stock_line_ids:
				if line.stock_picking_id:
					sale_order_obj = self.pool('sale.order')
					sale_order_id = sale_order_obj.search(cr,uid,[('name', '=', line.stock_picking_id.origin)], limit=1)
					if len(sale_order_id) > 0:
						sale_order = sale_order_obj.browse(cr, uid, sale_order_id[0])
						sale_time = datetime.strptime(sale_order.delivery_date, fmt)
						delivery_date = datetime.strptime(line.create_date, fmt)
						diff = '00:00:00'
						if delivery_date > sale_time :
							diff =  delivery_date - sale_time
							delta_list.append(diff)	

			for line in canvass.interbranch_move_ids:
				if line.interbranch_move_id:
					interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
					transfer_id = interbranch_stock_move_obj.search(cr,uid,[('id', '=', line.interbranch_move_id.id)], limit=1)
					if len(transfer_id) > 0:
						transfer = interbranch_stock_move_obj.browse(cr, uid, transfer_id[0])
						transfer_time = datetime.strptime(transfer.create_date, fmt)
						delivery_date = datetime.strptime(line.create_date, fmt)
						diff = '00:00:00'
						if delivery_date > transfer_time :
							diff =  delivery_date - transfer_time
							delta_list.append(diff)		

			result[canvass.id] = max(delta_list) if len(delta_list) > 0 else '00:00:00'

		return result

	def _default_branch_id(self, cr, uid, context={}):
	# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.id or None

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		'total_distance': fields.float('Total Distance', readonly=True),
		'is_recalculated': fields.boolean('Is Recalculated?', search=False),
		'interbranch_move_ids': fields.one2many('canvassing.canvas.interbranch.line', 'canvas_id', 'Interbranch Canvas Lines'),
		'max_load_time' : fields.function(_max_load_time, type='char',string='Max Load Time'), 
	}

	_defaults = {
		'is_recalculated': False,
		'max_load_time' : '00:00:00',
		'branch_id': _default_branch_id,
	}
	
	# OVERRIDES --------------------------------------------------------------------------------------------------------------
	
	def calculate_distance(self, cr, uid, canvas_data, context={}):
	# TEGUH@20180328 : fungsi calculate distance yg baru : 
	# ambil parameter2 sistem	
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['gps_base_url','gps_login_path','gps_devices_url','gps_positions_url','gps_username','gps_password'])])
		baseUrl = ""
		login_url = ""
		devices_url = ""
		position_url = ""
		gps_username = ""
		gps_password = ""
				
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'gps_base_url':
				baseUrl = param_data.value
			elif param_data.key == 'gps_login_path':
				login_url = baseUrl + param_data.value 
			elif param_data.key == 'gps_devices_url':
				devices_url = baseUrl + param_data.value
			elif param_data.key == 'gps_positions_url':
				position_url = baseUrl + param_data.value
			elif param_data.key == 'gps_username':
				gps_username = param_data.value
			elif param_data.key == 'gps_password':
				gps_password = param_data.value	

		# coba login ke sistem GPS		
		try:
			request = urllib2.Request(login_url)
			response = urllib2.urlopen(request, urllib.urlencode({'email':gps_username,'password':gps_password}))
			cookie = response.headers.get('Set-Cookie')
		except:
			return -1 # -1 artinya error
		
		# tentukan device id dari vehicle yang melakukan canvassing ini
		vehicle_gps_id = canvas_data.fleet_vehicle_id and canvas_data.fleet_vehicle_id.gps_id or None

		#get all device
		request = urllib2.Request(devices_url)
		request.add_header('Cookie', cookie)
		response = urllib2.urlopen(request)
		devices = json.load(response)
		
		device_id = None
		for device in devices:
			if vehicle_gps_id == device['uniqueId']:
				device_id = device['id']
				break
		
		# ambil jarak antara waktu mulai dan selesai
		# dikasih teloransi 10 menit sebelum dan sesudah, as per request 20170929
		# timedelta -7, karena ga sync database traccar
		date_depart = datetime.strptime(canvas_data.date_depart, DEFAULT_SERVER_DATETIME_FORMAT) - timedelta(minutes=10)
		date_delivered = datetime.strptime(canvas_data.date_delivered, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(minutes=10)

		date_depart = date_depart.isoformat()+'Z'
		date_delivered = date_delivered.isoformat() + 'Z'

		payload = {'deviceId' : device_id, 'from' :date_depart,'to':date_delivered }
		header =  {'cookie':cookie, 'Accept':'application/json'}
		results = requests.get(position_url,headers= header,params=payload)

		summary =  results.json()
		if not summary: return 0
		distance = summary[0]['distance']

		return float(distance)

	"""	
	def calculate_distance(self, cr, uid, canvas_data, context={}):
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
			# if not context.get('cron_mode', False):
			# 	raise osv.except_osv(_('Canvassing Error'),_('This canvassing trip does not have a vehicle or its GPS ID is invalid.'))
			# else:
			return 0
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
			# if not context.get('cron_mode', False):
			# 	raise osv.except_osv(_('Canvassing Error'),_('This canvassing trip does not have a vehicle or its GPS ID is invalid.'))
			# else:
				return 0
	# ambil jarak antara waktu mulai dan selesai
	# dikasih teloransi 10 menit sebelum dan sesudah, as per request 20170929
		date_depart = datetime.strptime(canvas_data.date_depart, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=7) - timedelta(minutes=10)
		date_delivered = datetime.strptime(canvas_data.date_delivered, DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=7) + timedelta(minutes=10)
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
		for i in j:
			index += 1
	# find substring in 'other' group in last iteration
		substr = j[index-1]['other']
		dist_pos = substr.find('totalDistance')
		pos1 = substr.find(':',dist_pos) 
		pos2 = substr.find('}',dist_pos)
		last_distance = substr[pos1+1:pos2]
	# inilah jaraknya!
		return float(last_distance) - float(start_distance)
	"""


	def action_recalculate_distance(self, cr, uid, ids, context={}):
		for canvas_data in self.browse(cr, uid, ids, context=context):
			distance = self.calculate_distance(cr, uid, canvas_data, context=context)
			distance = round(distance / 1000, 2) # dalam km
			self.write(cr, uid, [canvas_data.id], {
				'total_distance': distance,
				'distance': distance,
				'is_recalculated': True,
				})
		return True

	def action_set_finish(self, cr, uid, ids, context={}):
		super(canvassing_canvas, self).action_set_finish(cr, uid, ids, context=context)
		
		# TEGUH@20180329 : set finish canvas mengubah state interbranch jadi delivered
		# set interbranch stock move to deliverred if is_executed
		interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		for canvas in self.browse(cr, uid, ids, context=context):
			for interbranch_canvas_line in canvas.interbranch_move_ids:
				if interbranch_canvas_line.is_executed:
					interbranch_stock_move_obj.action_delivered(cr, uid, [interbranch_canvas_line.interbranch_move_id.id], context=context)

		"""
		# set interbranch stock move to accepted if is_executed
		interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		for canvas in self.browse(cr, uid, ids, context=context):
			for interbranch_canvas_line in canvas.interbranch_move_ids:
				if interbranch_canvas_line.is_executed:
					interbranch_stock_move_obj.action_accept(cr, uid, [interbranch_canvas_line.interbranch_move_id.id], context=context)
		"""
		return self.action_recalculate_distance(cr, uid, ids, context=context)
	
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

	# CRON -------------------------------------------------------------------------------------------------------------------

	def cron_recalculate_distance(self, cr, uid, context={}):
		trip_ids = self.search(cr, uid, [('state','=','finished'),('is_recalculated','=',False)])
		self.action_recalculate_distance(cr, uid, trip_ids, context={'cron_mode': True})

# ==========================================================================================================================

class canvasssing_canvas_stock_line(osv.Model):
	_inherit = 'canvassing.canvas.stock.line'

	_defaults = {
		'is_executed': True,
		'load_time' : '00:00:00',
	}

	def _sales_order_id(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for line in self.browse(cr, uid, ids, context=context):
			if line.stock_picking_id:
				if (line.stock_picking_id.picking_type_id.code == 'outgoing'):
					sale_order_obj = self.pool('sale.order')
					sale_order_id = sale_order_obj.search(cr,uid,[('name', '=', line.stock_picking_id.origin)], limit=1)
					if len(sale_order_id) > 0:
						result[line.id] = sale_order_id[0]
				else:
					result = False
		return result

	def _purchase_order_id(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for line in self.browse(cr, uid, ids, context=context):
			if line.stock_picking_id:
				if (line.stock_picking_id.picking_type_id.code == 'incoming'):
					pruchase_order_obj = self.pool('purchase.order')
					purchase_order_id = pruchase_order_obj.search(cr,uid,[('name', '=', line.stock_picking_id.origin)], limit=1)	
					if len(purchase_order_id) > 0:
						result[line.id] = purchase_order_id[0]
				else:
					result = False
		return result

	def _load_time(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		fmt = '%Y-%m-%d %H:%M:%S'
		for line in self.browse(cr, uid, ids, context=context):
			if line.stock_picking_id:
				sale_order_obj = self.pool('sale.order')
				sale_order_id = sale_order_obj.search(cr,uid,[('name', '=', line.stock_picking_id.origin)], limit=1)
				if len(sale_order_id) > 0:
					sale_order = sale_order_obj.browse(cr, uid, sale_order_id[0])
					sale_time = datetime.strptime(sale_order.delivery_date, fmt)
					delivery_date = datetime.strptime(line.create_date, fmt)
					diff = '00:00:00'
					if delivery_date > sale_time :
						diff =  delivery_date - sale_time
					result[line.id] = diff
				else:
					result[line.id] = '00:00:00'
			else:
				result[line.id] = '00:00:00'
		return result

	_columns = {
		'sales_order_id': fields.function(_sales_order_id, type='many2one', relation='sale.order',string='Sales Order'),
		'purchase_order_id': fields.function(_purchase_order_id, type='many2one', relation='purchase.order',string='Purchase Order'),
		'load_time' :fields.function(_load_time, type='char',string='Load Time'),
	}

	def action_open_sales_order(self, cr, uid, ids, context={}):
		
		line_data = self.browse(cr, uid, ids[0], context=context)
		if (line_data.sales_order_id):
			model_obj = self.pool.get('ir.model.data')
			model, view_id = model_obj.get_object_reference(cr, uid, 'sale', 'view_order_form')
			return {
			'type': 'ir.actions.act_window',
			'name': 'Sale Order Detail',
			'view_mode': 'form',
			'view_type': 'form',
			'view_id': view_id,
			'res_id': line_data.sales_order_id.id,
			'res_model': 'sale.order',
			'nodestroy': True,
			'flags': {'form': {'options': {'mode': 'view'} } },
			'context': {'simple_view': 1},
			'target': 'new',
			}
		elif (line_data.purchase_order_id):
			model_obj = self.pool.get('ir.model.data')
			model, view_id = model_obj.get_object_reference(cr, uid, 'purchase', 'purchase_order_form')
			return {
			'type': 'ir.actions.act_window',
			'name': 'Purchase Order Detail',
			'view_mode': 'form',
			'view_type': 'form',
			'view_id': view_id,
			'res_id': line_data.purchase_order_id.id,
			'res_model': 'purchase.order',
			'nodestroy': True,
			'flags': {'form': {'options': {'mode': 'view'} } },
			'context': {'simple_view': 1},
			'target': 'new',
			}

		


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
# ==========================================================================================================================

class canvassing_canvas_interbranch_line(osv.Model):
	_name = 'canvassing.canvas.interbranch.line'
	_description = 'Interbranch Line for Canvassing'
	
	# COLUMNS --------------------------------------------------------------------------------------------------------------
	
	def _load_time(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		fmt = '%Y-%m-%d %H:%M:%S'
		for line in self.browse(cr, uid, ids, context=context):
			if line.interbranch_move_id:
				interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
				transfer_id = interbranch_stock_move_obj.search(cr,uid,[('id', '=', line.interbranch_move_id.id)], limit=1)
				diff = '00:00:00'
				if len(transfer_id) > 0:
					transfer = interbranch_stock_move_obj.browse(cr, uid, transfer_id[0])
					transfer_time = datetime.strptime(transfer.create_date, fmt)
					diff = datetime.strptime(line.create_date, fmt) - transfer_time
					#time_delta = (diff.days * 24 * 60) + (diff.seconds/60)
					result[line.id] = diff
				else:
					result[line.id] = '00:00:00'
			else:
				result[line.id] = '00:00:00'
		return result

	_columns = {
		'canvas_id': fields.many2one('canvassing.canvas', 'Canvas'),
		'interbranch_move_id': fields.many2one('tbvip.interbranch.stock.move', 'Interbranch Stock Move', required=True),
		'is_executed': fields.boolean('Is Executed'),
		'notes': fields.text('Notes'),
		'canvas_state': fields.related('canvas_id', 'state', type="char", string="Canvas State"),
		'load_time' :fields.function(_load_time, type='char',string='Load Time'),
		# not needed, can see from interbranch_move_id.name
		# 'from_stock_location_id': fields.related('interbranch_move_id', 'from_stock_location_id',
		# 	type="many2one", relation="stock.location", string="Incoming Location"),
		# 'to_stock_location_id': fields.related('interbranch_move_id', 'to_stock_location_id',
		# 	type="many2one", relation="stock.location", string="Outgoing Location"),
	}

	_defaults = {
		'is_executed': True,
		'load_time' : '00:00:00',
	}
	
	def create(self, cr, uid, vals, context={}):
		new_id = super(canvassing_canvas_interbranch_line, self).create(cr, uid, vals, context=context)
		# check if interbranch stock move already rejected, cannot be executed
		if vals.get('is_executed', False):
			interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
			interbranch_move_id = vals['interbranch_move_id']
			interbranch_move = interbranch_stock_move_obj.browse(cr, uid, interbranch_move_id, context=context)
			if interbranch_move.state == 'rejected':
				raise osv.except_osv(_('Warning!'), _("Interbranch Stock Move \"%s\" had already been rejected!") %
					(interbranch_move.move_date + ' | ' + interbranch_move.from_stock_location_id.name + ' -> ' + interbranch_move.to_stock_location_id.name,))
		return new_id
	
	def write(self, cr, uid, ids, vals, context=None):
		result = super(canvassing_canvas_interbranch_line, self).write(cr, uid, ids, vals, context=context)
		# check if interbranch stock move already rejected, cannot be executed
		if vals.get('is_executed', False):
			for line in self.browse(cr, uid, ids, context=context):
				interbranch_move_id = vals['interbranch_move_id'] if vals.get('interbranch_move_id', False) else line.interbranch_move_id.id
				interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
				interbranch_move = interbranch_stock_move_obj.browse(cr, uid, interbranch_move_id, context=context)
				if interbranch_move.state == 'rejected':
					raise osv.except_osv(_('Warning!'), _("Interbranch Stock Move \"%s\" had already been rejected!") %
						(interbranch_move.move_date + ' | ' + interbranch_move.from_stock_location_id.name + ' -> ' + interbranch_move.to_stock_location_id.name,))
		return result

	def action_open_interbrach_move(self, cr, uid, ids, context={}):
		model_obj = self.pool.get('ir.model.data')
		model, view_id = model_obj.get_object_reference(cr, uid, 'tbvip', 'tbvip_interbranch_stock_move_form')
		line_data = self.browse(cr, uid, ids[0], context=context)

		return {
			'type': 'ir.actions.act_window',
			'name': 'Interbranch Transfer',
			'view_mode': 'form',
			'view_type': 'form',
			'view_id': view_id,
			'res_id': line_data.interbranch_move_id.id,
			'res_model': 'tbvip.interbranch.stock.move',
			'nodestroy': True,
			'flags': {'form': {'options': {'mode': 'view'} } },
			'context': {'simple_view': 1},
			'target': 'new',
		}