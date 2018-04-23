from openerp.osv import osv, fields

from datetime import datetime
from datetime import timedelta

from pyfcm import FCMNotification

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# ==========================================================================================================================
class tbvip_fcm_notif(osv.osv):
	_name = 'tbvip.fcm_notif'
	_description = 'Notification via Firestore Cloud Messaging'
	_auto = False

	#push_service = None

	'''
	def __init__(self):
		#init Firestore DB			
		cred = credentials.ApplicationDefault()
		firebase_admin.initialize_app(cred, {'projectId': 'awesome-beaker-150403',})

		#FCM Notification Server cred
		self.push_service = FCMNotification(api_key="AAAAl1iYTeo:APA91bHp-WiAzZxjiKa93znVKsD1N2AgtgwB1azuEYyvpWHyFR2WfZRj3UPXMov9PzbCBpOCScz8YN_Ki2kEVf_5V43bgUDjJmHSh78NOK0KLWOU2cgYUe9KClTkTTwpTzUcaBB2hVqT")
	'''

	#init Firestore DB			
	cred = credentials.ApplicationDefault()
	firebase_admin.initialize_app(cred, {'projectId': 'awesome-beaker-150403',})

	def send_notification(self,cr,uid,message_title,message_body,context={}): #contet : is_stored,branch,category,sound_idx,
		#FCM Notification Server cred
		
		#Get Param Value
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['notification_topic'])])
		notification_topic = ''
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'notification_topic':
				notification_topic = param_data.value

		if (notification_topic != ''):
			push_service = FCMNotification(api_key="AAAAl1iYTeo:APA91bHp-WiAzZxjiKa93znVKsD1N2AgtgwB1azuEYyvpWHyFR2WfZRj3UPXMov9PzbCBpOCScz8YN_Ki2kEVf_5V43bgUDjJmHSh78NOK0KLWOU2cgYUe9KClTkTTwpTzUcaBB2hVqT")		
			
			#SELECT SOUND FOR NOTIFICATION
			sound_index = context.get('sound_idx',0)
			sound = 'notification'+str(sound_index)+'.mp3'
			
			#push notification
			push_service.notify_topic_subscribers(topic_name=notification_topic, message_title=message_title,message_body=message_body, sound=sound)

			if context.get('is_stored',False):
				branch = context.get('branch','VIP')
				category = context.get('category','BASE')
				now = datetime.now() + timedelta(hours = 7)
				db = firestore.client()
				doc_ref = db.collection(u'notification').document()
				doc_ref.set({
					u'branch':unicode(branch),
					u'category':unicode(category),
					u'date':unicode(now.strftime("%d/%m/%Y %H:%M:%S")),
					u'timestamp':datetime.now(),
					u'title':unicode(message_title),
					u'message':unicode(message_body),
					u'state':u'unread'
				})



class sale_order(osv.osv):
	_inherit = 'sale.order'

	def action_button_confirm(self, cr, uid, ids, context=None):
		result = super(sale_order, self).action_button_confirm(cr, uid, ids, context)

		for sale in self.browse(cr, uid, ids):
			value = sale.amount_total
			row_count = len(sale.order_line)
			branch = sale.branch_id.name
			cust_name = sale.partner_id.display_name
			bon_number = sale.bon_number
			desc = sale.client_order_ref
			employee = sale.employee_id.name

		#message_body = sale.employee_id.name+'/'+str(row_count)+' items(s)/'+str("{:,.0f}".format(value))
		message_body = employee+'/'+str(row_count)+' row(s)/'+str("{:,.0f}".format(value))
		
		if ((value >= 500000) or (desc) or (cust_name == 'TOKOPEDIA') or (cust_name == 'BUKALAPAK')):
			stored = True
			message_title = 'SALES ('+branch+'):'+str(bon_number)
			sound_idx = 1
			if (cust_name == 'TOKOPEDIA' or (cust_name == 'BUKALAPAK')):
				message_body = message_body + '/Cust:'+ cust_name

			if (desc):
				message_body = message_body + '/Desc:'+ str(desc)

		else:
			stored = False
			message_title = 'YOU GOT COIN!'
			sound_idx = 0
		
		context = {
			'is_stored' : stored,
			'branch' : branch,
			'category':'SALES',
			'sound_idx':sound_idx,
			}

		self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result

class purchase_order(osv.osv):
	_inherit = 'purchase.order'

	def wkf_confirm_order(self, cr, uid, ids, context=None):
		result = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)

		for purchase in self.browse(cr, uid, ids, context=context):
			value = purchase.amount_total
			supplier = purchase.partner_id.display_name
			row_count = len(purchase.order_line)

		message_title = 'PURCHASE:'+str(supplier)
		message_body = str(row_count)+' row(s)/'+str("{:,.0f}".format(value))
		
		if value >= 5000000:
			stored = True
		else:
			stored = False
		
		context = {
			'is_stored' : stored,
			'category':'PURCHASE',
			'sound_idx':2,
			}

		self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result
