from openerp.osv import osv, fields
import urllib2
import json
import socket



# ==========================================================================================================================

class fleet_vehicle(osv.osv):
	_inherit = 'fleet.vehicle'

	def _location(self, cr, uid, ids, field_name, arg, context=None):
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['gps_base_url','gps_login_path','gps_latest_position_url','gps_username','gps_password'])])
		baseUrl = ""
		login_url = ""
		position_url = ""
		gps_username = ""
		gps_password = ""
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
					if data.gps_id == position['device']['uniqueId']:
						try:
							result[data.id] = position['address']
						except KeyError:
							result[data.id] = '-'
		return result

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'next_service_date': fields.date('Next Service Date'),
		'next_pkb_date': fields.date('Next PKB Date'),
		'gps_id': fields.char('GPS ID'),
		'gps_sim': fields.char('GPS SIM Number'),
		'gps_renew': fields.date('GPS SIM Renewal'),
		'location': fields.function(_location, type='char', method=True, string='Location', help='Location of the vehicle'),
	}

# ==========================================================================================================================
