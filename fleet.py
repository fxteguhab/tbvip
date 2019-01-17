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
		devices_url = ""
		position_url = ""
		gps_username = ""
		gps_password = ""
		result = {}

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

		# coba login ke sistem GPS		
		try:
			request = urllib2.Request(login_url)
			response = urllib2.urlopen(request, urllib.urlencode({'email':gps_username,'password':gps_password}))
			cookie = response.headers.get('Set-Cookie')
		except:
			return -1 # -1 artinya error

		#get all device
		request = urllib2.Request(devices_url)
		request.add_header('Cookie', cookie)
		response = urllib2.urlopen(request)
		devices = json.load(response)

		device_id = None
		for data in self.browse(cr, uid, ids, context=context):
			vehicle_gps_id = data.gps_id

			for device in devices:
				if vehicle_gps_id == device['uniqueId']:
					gps_id = device['id']
					#print "gps_id: "+str(gps_id)
					break
			payload = {'id' : gps_id}
			header =  {'cookie':cookie, 'Accept':'application/json'}	
			results = requests.get(position_url,headers= header,params=payload)
			summary =  results.json()
			if not summary: return 0
			#print "address: "+str(summary[0]['address'])
			result[data.id] = (summary[0]['address'])

		return result
		'''
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
		
		result = {}
		if (baseUrl != ''):
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
				
			
			for data in self.browse(cr, uid, ids, context=context):
				result[data.id] = ''
				#get device id FROM IMEI
				deviceId = ''
				for device in devices:
					if data.gps_id == device['uniqueId']:
						for position in positions:
							if device['id'] == position['deviceId']:
								result[data.id] = position.get("address","-")
		'''
		
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
