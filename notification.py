from openerp.osv import osv, fields

from datetime import datetime
from datetime import timedelta

try:
	from pyfcm import FCMNotification
	import firebase_admin
	from firebase_admin import credentials
	from firebase_admin import firestore
	has_notification_lib = True
except:
	has_notification_lib = False

# ==========================================================================================================================
SALES_SOUND_IDX = 0
PURCHASE_SOUND_IDX = 2
PRODUCT_SOUND_IDX = 1

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
	if has_notification_lib:
		cred = None
		cred = credentials.Certificate('tokobesiVIP-ade097b8b6e5.json')
		
		if cred:
			firebase_admin.initialize_app(cred)
		else:
			cred = credentials.ApplicationDefault()
			firebase_admin.initialize_app(cred, {'projectId': 'awesome-beaker-150403',})
	else:
		cred = None

	def send_notification(self,cr,uid,message_title,message_body,context={}): #context : is_stored,branch,category,sound_idx,lines
		if not has_notification_lib: return
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

			if context.get('is_stored',True):
				branch = context.get('branch','VIP')
				category = context.get('category','BASE')
				lines = context.get('lines','')
				now = datetime.now() + timedelta(hours = 7)
				alert = context.get('alert','!!')
				db = firestore.client()
				doc_ref = db.collection(u'notification').document()
				doc_ref.set({
					u'branch':unicode(branch),
					u'category':unicode(category),
					u'date':unicode(now.strftime("%d/%m/%Y %H:%M:%S")),
					u'timestamp':datetime.now(),
					u'title':unicode(message_title),
					u'message':unicode(message_body),
					u'lines':unicode(lines),
					u'state':u'unread',
					u'alert':unicode(alert)
				})



class sale_order(osv.osv):
	_inherit = 'sale.order'

	def action_button_confirm(self, cr, uid, ids, context=None):
		result = super(sale_order, self).action_button_confirm(cr, uid, ids, context)
		#Get Param Value
		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['notification_sale_limit'])])
		sale_limit = 0
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'notification_sale_limit':
				sale_limit = float(param_data.value)
		
		for sale in self.browse(cr, uid, ids):
			value = sale.amount_total
			row_count = len(sale.order_line)
			branch = sale.branch_id.name
			cust_name = sale.partner_id.display_name
			bon_number = sale.bon_number
			desc = sale.client_order_ref
			employee = sale.employee_id.name
			line_str = ''
			product_name = ''
			product_watch = ''
			for line in sale.order_line:
				product_name = line.product_id.name_template
				if line.product_id.sale_notification: 
					product_watch = '[!!]'
					product_name += product_watch
				
				line_str += str(line.product_uos_qty)+':'+product_name + '\n'
				'''
				if line.product_id.sale_notification: 
					message_title = 'PRODUCT SALE NOTIFICATION'
					message_body = 'Cust :'+ cust_name + '\n'  + str(line.product_uos_qty)+':' + line.product_id.name_template
					context = {
						'branch' : branch,
						'category':'PRODUCT',
						'sound_idx':PRODUCT_SOUND_IDX,
						}
					self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)				
				'''
		#message_body = sale.employee_id.name+'/'+str(row_count)+' items(s)/'+str("{:,.0f}".format(value))		

		if ((value >= sale_limit) or (product_watch == '[!!]')):
			message_title = 'SALES('+branch+')'+product_watch+':'+cust_name
			message_body = employee+'('+str(bon_number)+'):'+str(row_count)+' row(s):'+str("{:,.0f}".format(value))# +'\n'+'Cust:'+cust_name
			if (desc):
					message_body = message_body +'\n'+ 'Desc:'+ str(desc)
			
			context = {
				'branch' : branch,
				'category':'SALES',
				'sound_idx':SALES_SOUND_IDX,
				'lines' : line_str,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result

class purchase_order(osv.osv):
	_inherit = 'purchase.order'

	def wkf_confirm_order(self, cr, uid, ids, context=None):
		result = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)

		param_obj = self.pool.get('ir.config_parameter')
		param_ids = param_obj.search(cr, uid, [('key','in',['notification_purchase_limit'])])
		purchase_limit = 0
		
		for param_data in param_obj.browse(cr, uid, param_ids):
			if param_data.key == 'notification_purchase_limit':
				purchase_limit = float(param_data.value)

		for purchase in self.browse(cr, uid, ids, context=context):
			value = purchase.amount_total
			supplier_name = purchase.partner_id.display_name
			row_count = len(purchase.order_line)
			line_str = ''
			product_watch = ''
			for line in purchase.order_line:
				qty_available = line.product_id.qty_available
				product_name = line.product_id.name_template
				if line.product_id.sale_notification: 
					product_watch = '[!!]'
					product_name += product_watch

				line_str += str(line.product_qty)+':'+product_name + '\n'+'     Stock:'+str(qty_available)+'\n'
				
				'''
				if line.product_id.purchase_notification: 
					message_title = 'PRODUCT PURCHASE NOTIFICATION'
					message_body = 'Supplier :'+ supplier_name + '\n'  + str(line.product_qty)+':' + line.product_id.name_template +'\n'+'     Stock:'+str(qty_available)
					context = {
						'category':'PRODUCT',
						'sound_idx':PRODUCT_SOUND_IDX,
						}
					self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)
				'''
		if ((value >= purchase_limit) or (product_watch == '[!!]')):
			message_title = 'PURCHASE'+product_watch+':'+str(supplier_name)
			message_body = str(row_count)+' row(s):'+str("{:,.0f}".format(value)) 

			context = {
				'category':'PURCHASE',
				'sound_idx':PURCHASE_SOUND_IDX,
				'lines' : line_str,
				}

			self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return result

class product_template(osv.osv):
	_inherit = 'product.template'
	_columns = {
		'sale_notification' : fields.boolean('Sale Notification'),
		'purchase_notification' : fields.boolean('Purchase Notification'),
	}

	# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	def create(self, cr, uid, vals, context={}):
		new_id = super(product_template, self).create(cr, uid, vals, context)
		
		name = ''
		for product in self.browse(cr, uid, new_id, context=context):
			name = product.name
			create_by = product.create_uid.name

		message_title = 'NEW ITEM CREATION'
		message_body = 'NAME:'+str(name) +'\n'+'Created by :' +str(create_by)
		context = {
				'category':'PRODUCT',
				'sound_idx':PRODUCT_SOUND_IDX,
				}
		self.pool.get('tbvip.fcm_notif').send_notification(cr,uid,message_title,message_body,context=context)

		return new_id


class product_category(osv.osv):
	_inherit = 'product.category'
	_columns = {
		'sale_notification' : fields.boolean('Sale Notification'),
		'purchase_notification' : fields.boolean('Purchase Notification'),
	}


	def write(self, cr, uid, ids, data, context=None):
		result = super(product_category, self).write(cr, uid, ids, data, context)
		for category_id in ids:
			product_obj = self.pool.get('product.template')
			product_ids = product_obj.search(cr, uid, [
				('categ_id', '=', category_id),
			])
			#if data.get('sale_notification', False):
			product_obj.write(cr, uid, product_ids, {
				'sale_notification': data['sale_notification'],
			})
			#if data.get('purchase_notification', False):
			product_obj.write(cr, uid, product_ids, {
				'purchase_notification': data['purchase_notification'],
			})
		return result
