from openerp.osv import osv, fields
import urllib2
import json
import socket



# ==========================================================================================================================

class fleet_vehicle(osv.osv):
	_inherit = 'fleet.vehicle'

	def _location(self, cr, uid, ids, field_name, arg, context=None):
		baseUrl = 'http://35.187.150.104:8082'
		login_url = baseUrl + '/traccar/rest/login'
		position_url = baseUrl + '/traccar/rest/getLatestPositions'
		gps_username = 'tokobesivip'
		gps_password = 'tokobesivip'
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
