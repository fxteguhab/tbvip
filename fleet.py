from openerp.osv import osv, fields
import urllib2
import urllib
import json
import socket
import requests

# ==========================================================================================================================

class fleet_vehicle(osv.osv):
	_inherit = 'fleet.vehicle'

	def _location(self, cr, uid, ids, field_name, arg, context=None):
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['gps_base_url','gps_login_path','gps_devices_url','gps_latest_position_url','gps_username','gps_password'])])
		baseUrl = ""
		login_url = ""
		#add new device url
		devices_url = ""
		position_url = ""
		gps_username = ""
		gps_password = ""

		#---------------start new code
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'gps_base_url':
				baseUrl = param_data.value
			elif param_data.key == 'gps_login_path':
				login_url = baseUrl + param_data.value 
			elif param_data.key == 'gps_devices_url':
				devices_url = baseUrl + param_data.value
			elif param_data.key == 'gps_latest_position_url':
				position_url = baseUrl + param_data.value
			elif param_data.key == 'gps_username':
				gps_username = param_data.value
			elif param_data.key == 'gps_password':
				gps_password = param_data.value	
	
		#login
		request = urllib2.Request(login_url)
		login = urllib2.urlopen(request, urllib.urlencode({'email':gps_username,'password':gps_password}))

		#get all device
		request = urllib2.Request(devices_url)
		request.add_header('Cookie', login.headers.get('Set-Cookie'))
		response = urllib2.urlopen(request)
		devices = json.load(response)
				
		#get all position
		request = urllib2.Request(position_url)
		request.add_header('Cookie', login.headers.get('Set-Cookie'))
		response = urllib2.urlopen(request)
		positions = json.load(response)
			
		result = {}
		for data in self.browse(cr, uid, ids, context=context):
			result[data.id] = ''
			#get device id FROM IMEI
			deviceId = ''
			for device in devices:
				if data.gps_id == device['uniqueId']:
					for position in positions:
						if device['id'] == position['deviceId']:
							result[data.id] = position.get("address","-")
		return result
		#--------------end new code

		"""	
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'gps_base_url':
				baseUrl = param_data.value
			elif param_data.key == 'gps_login_path':
				login_url = baseUrl + param_data.value
			elif param_data.key == 'gps_latest_position_url':
				position_url = baseUrl + param_data.value
			elif param_data.key == 'gps_username':
				gps_username = param_data.value
			elif param_data.key == 'gps_password':
				gps_password = param_data.value
		request = urllib2.Request(login_url + '?payload=["'+gps_username+'","'+gps_password+'"]')
		login = urllib2.urlopen(request)
		request = urllib2.Request(position_url)
		request.add_header('Cookie', login.headers.get('Set-Cookie'))
		response = urllib2.urlopen(request)
		positions = json.load(response)
		result = {}
		for data in self.browse(cr, uid, ids, context=context):
				result[data.id] = ''
				for position in positions:
					if position.get('device', False) and data.gps_id == position['device']['uniqueId']:
						result[data.id] = position.get("address","-")
		return result
		"""
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'next_service_date': fields.date('Next KIR Date'),
		'next_pkb_date': fields.date('Next Tax Date'),
		'gps_id': fields.char('GPS IMEI'),
		'gps_sim': fields.char('GPS SIM No'),
		'gps_renew': fields.date('GPS SIM Renewal'),
		'location': fields.function(_location, type='char', method=True, string='Location', help='Location of the vehicle'),
	}

# ==========================================================================================================================
