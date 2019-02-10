from datetime import datetime, timedelta
from openerp import api
from openerp.osv import osv, fields
from openerp.tools.translate import _

# ==========================================================================================================================

class account_journal_edc(osv.osv):
	_inherit = 'account.journal.edc'

# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'current_branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}
	
# ==========================================================================================================================

class account_invoice(osv.osv):
	_inherit = 'account.invoice'
	
	# FIELD FUNCTION METHOD ----------------------------------------------------------------------------------------------------
	
	def _qty_sum(self, cr, uid, ids, field_name, arg, context):
		result = {}
		for invoice_data in self.browse(cr, uid, ids, context):
			result[invoice_data.id] = 0
			for invoice_line_data in invoice_data.invoice_line:
				result[invoice_data.id] += invoice_line_data.quantity
		return result
	
	def _row_count(self, cr, uid, ids, field_name, arg, context):
		result = {}
		for invoice_data in self.browse(cr, uid, ids, context):
			result[invoice_data.id] = len(invoice_data.invoice_line)
		return result
	
# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'qty_sum': fields.function(_qty_sum, type="integer", string="Qty Sum"),
		'row_count': fields.function(_row_count, type="integer", string="Row Count"),
		'related_sales_bon_number': fields.char("Nomor Bon", readonly=True),
	}
	
	def invoice_auto_done(self, cr, uid, ids, context=None):
		for invoice in self.browse(cr, uid, ids):
			invoice.signal_workflow('invoice_open')
	
	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		"""
		Update name_search (like in m2o search) domain to search with sale bon number for today (in infix):
		('number', '=', name)
			OR (('related_sales_bon_number', '=', name)
				AND (date_invoice', '>=', today.strftime('%Y-%m-%d'))
				AND ('date_invoice', '<', tommorow.strftime('%Y-%m-%d'))
			)
		"""
		args = args or []
		recs = self.browse()
		if name:
			today = datetime.today()
			tommorow = datetime.today() + timedelta(1)
			recs = self.search([
					'|',
					('number', '=', name),
					'&', ('related_sales_bon_number', '=', name),
					'&', ('date_invoice', '>=', today.strftime('%Y-%m-%d')),
					('date_invoice', '<', tommorow.strftime('%Y-%m-%d'))] + args, limit=limit)
		if not recs:
			recs = self.search([('name', operator, name)] + args, limit=limit)
		return recs.name_get()
	
	def _campaign_promo_watcher(self, cr, uid, ids, context={}):
		invoice_id = context.get('invoice_id',0)
		product_id = context.get('product_id',0)
		partner_id = context.get('partner_id',0)
		price_unit = context.get('price_unit',0)
		invoice_date = context.get('invoice_date',0)
		product_name = context.get('name',0)
		invoice_number = context.get('origin',0)
		qty = context.get('qty',0)

		product_template_id = self.pool['product.product'].browse(cr, uid, product_id).product_tmpl_id
		product_template = self.pool['product.template'].browse(cr, uid, product_template_id.id) 
		categ_id = product_template.categ_id
		
		campaign_list = []
		campaign_ids = self.pool['tbvip.campaign'].search(cr, uid, ['&','&',('state','=','running'),('partner_id', '=',partner_id),'&',('date_start','<=',invoice_date),('date_end','>=',invoice_date)])

		qty_min = 0
		poin = 0
		weight = 0

		if len(campaign_ids) > 0:
			product_ids = self.pool['tbvip.campaign.product.line'].search(cr, uid, [('campaign_id', 'in',campaign_ids),('product_template_id', '=',product_template_id.id)])	
			for product in self.pool['tbvip.campaign.product.line'].browse(cr,uid,product_ids) : 
				campaign_list.append(product.campaign_id.id)
				min_qty = product.min_qty
				poin = product.poin
				weight = product_template.tonnage

			if not product_ids:
				category_ids = self.pool['tbvip.campaign.category.line'].search(cr, uid, [('campaign_id', 'in',campaign_ids),('product_category_id', '=',categ_id.id)])
				for category in self.pool['tbvip.campaign.category.line'].browse(cr,uid,category_ids): 
					campaign_list.append(category.campaign_id.id)
					min_qty = category.min_qty
					poin = category.poin
					product_category = self.pool['product.category'].browse(cr,uid,category.product_category_id.id)
					weight = product_category.tonnage

		if len(campaign_list) > 0:
			active_campaign_ids = self.pool['tbvip.campaign'].browse(cr, uid, campaign_list)
			invoice_line_id = self.pool['tbvip.campaign.invoice.line']

			for active_campaign in active_campaign_ids:
				targets = active_campaign.target_line_ids

				current_amount = 0
				if active_campaign.measure == 'value': current_amount = (qty * price_unit)
				elif active_campaign.measure == 'poin': current_amount = ((qty // min_qty) * poin)
				elif active_campaign.measure == 'tonase': current_amount = (qty * weight)

				active_campaign.current_amount += current_amount 

				if active_campaign.invoice_type == 'one_invoice':
					remainder = current_amount
					for target in targets:
						if (remainder >= target.target_amount):
							target.achievement_counter += remainder // target.target_amount
							active_campaign.current_achievement += remainder // target.target_amount
							remainder = remainder % target.target_amount

				if active_campaign.invoice_type == 'many_invoice':
					remainder = active_campaign.current_amount
					active_campaign.current_achievement = 0
					for target in targets:
						if (remainder >= target.target_amount):
							target.achievement_counter =  remainder // target.target_amount
							active_campaign.current_achievement += target.achievement_counter 
							remainder = remainder % target.target_amount	

				invoice_line_id.create(cr, uid, {
				'campaign_id': active_campaign.id,
				'invoice_id': invoice_id,
				'invoice_date': invoice_date,
				'invoice_origin':invoice_number,
				'qty':qty,
				'invoice_ref': product_name,
				'amount': current_amount,
			}, context)

				

	def _cost_price_watcher(self, cr, uid, ids, context={}):
		price_unit_nett = context.get('price_unit_nett',0)
		price_unit_nett_old = context.get('price_unit_nett_old',0)
		product_id = context.get('product_id',0)
		name = context.get('name','')
		invoice_id = context.get('invoice_id',0)
		invoice_type = context.get('type',0)
		price_unit = context.get('price_unit',0)

		if (price_unit_nett_old > 0) and (round(price_unit_nett_old) != round(price_unit_nett)):
			account_invoice_obj = self.pool.get('account.invoice')
			message="There is a change on cost price for %s in Invoice %s. From: %s to %s." % (name,invoice_id,price_unit_nett_old,price_unit_nett)		
			account_invoice_obj.message_post(cr, uid, invoice_id, body=message)				

			if (invoice_type == 'in_invoice'): #buy
				self.pool.get('product.product')._set_price(cr,uid,product_id,price_unit_nett,'standard_price') #catet last buy di standard_buy
			if (invoice_type == 'out_invoice'): #sell
				self.pool.get('product.product')._set_price(cr,uid,product_id,price_unit,'list_price')#catet last sell di list_price

	def invoice_validate(self, cr, uid, ids, context=None):
		result = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
		
		model, general_customer_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')

		invoice = self.browse(cr,uid,ids)
		invoice_line_ids = invoice.invoice_line
		for invoice_line_id in invoice_line_ids:
			invoice_line = self.pool.get('account.invoice.line').browse(cr,uid, invoice_line_id.id,context)
						
			price_type_id = invoice_line.price_type_id.id
			product_id = invoice_line.product_id.id
			product_uom = invoice_line.uos_id.id
			categ_id = invoice_line.product_id.categ_id.name

			price_unit = invoice_line.price_unit
			price_unit_old = invoice_line.price_unit_old
			price_unit_nett = invoice_line.price_unit_nett
			price_unit_nett_old = invoice_line.price_unit_nett_old
			discount_string = invoice_line.discount_string
			discount_string_old = invoice_line.discount_string_old

			invoice_id = invoice_line.invoice_id.id
			sell_price_unit = invoice_line.sell_price_unit
			buy_price_unit = invoice_line.buy_price_unit
			name = invoice_line.name
			partner_name = invoice_line.invoice_id.partner_id.display_name
			partner_id =  invoice_line.invoice_id.partner_id.id
			origin = invoice_line.origin
			quantity = invoice_line.quantity
			invoice_date = invoice_line.write_date

			invoice_type = invoice.type
			invoice_number = ''
			if invoice.type in ['in_invoice']: #if "buy"
				#invoice_type = 'in_invoice'
				self.pool.get('price.list')._create_product_current_price_if_none(cr, uid, price_type_id, product_id, product_uom, price_unit, discount_string,partner_id=partner_id)

			elif invoice.type in ['out_invoice']:	
				#invoice_type = 'out_invoice'
				self.pool.get('price.list')._create_product_current_price_if_none(cr, uid, price_type_id, product_id, product_uom, price_unit, discount_string,partner_id=general_customer_id)

			ctx = {
				'price_unit_nett_old' : price_unit_nett_old,
				'price_unit_nett' : price_unit_nett,
				'price_unit' : price_unit,
				'price_unit_old' : price_unit_old,
				'product_id' :  product_id,
				'price_type_id' : price_type_id,
				'partner_name' : partner_name,
				'partner_id' : partner_id,
				'product_uom' : product_uom,
				'discount_string' : discount_string,
				'discount_string_old' : discount_string_old,
				'name' : name,
				'invoice_id' : invoice_id,
				'sell_price_unit' : sell_price_unit,
				'buy_price_unit' : buy_price_unit,
				'type' : invoice_type,
				'categ_id' : categ_id,
				'origin' : origin,
				'qty' : quantity,
				'invoice_date' : invoice_date,
				}

				#check for changes and send notif
			self._cost_price_watcher(cr, uid, ids,  context=ctx)
			self._campaign_promo_watcher(cr, uid, ids,  context=ctx)

		return result
# =========================================================================================================================

class account_invoice_line(osv.osv):
	_inherit = 'account.invoice.line'

	_columns = {
		'price_type_id': fields.many2one('price.type', 'Price Type', ondelete='restrict'),
		'price_unit_old': fields.float(string = 'Price Old'),
		'price_unit_nett_old': fields.float(string = 'Nett Old'),
		'discount_string_old': fields.char(string = 'Disc Old'),
		'sell_price_unit': fields.float('Sales Price'),
		'buy_price_unit': fields.float('Buy Price'),
		'sale_line_id': fields.many2one('sale.order.line', 'Sale Order Line'),
	}

'''	
	#def create(self, cr, uid, vals, context={}):		
	#	new_id = super(account_invoice_line, self).create(cr, uid, vals, context=context)		
		
		# otomatis create current price kalo belum ada 
		#if vals.get('price_type_id', False) and vals.get('uos_id', False):
			#new_data = self.browse(cr, uid, new_id)		
			
			#discount_string = vals['discount_string'] if 'discount_string' in vals else "0"
			#invoice_type = ''
			#if new_data.invoice_id.type in ['in_invoice']: #if "buy"	
			#	invoice_type = 'in_invoice'	
			#elif vals.get('sale_line_id',False): #if "sell"
			#	invoice_type = 'out_invoice'
				
			################################### SET NEW PRICE LIST, #####################################################################
			#self.pool.get('price.list')._create_product_current_price_if_none(cr, uid,
			#		vals['price_type_id'], vals['product_id'], vals['uos_id'], vals['price_unit'],
			#		discount_string, partner_id=new_data.invoice_id.partner_id.id)
			#############################################################################################################################

			#check for changes and send notif
			#ctx = {
			#	'price_unit_nett_old' : vals['price_unit_nett_old'] if 'price_unit_nett_old' in vals else 0,
			#	'price_unit_nett' : vals['price_unit_nett'] if 'price_unit_nett' in vals else 0,
			#	'price_unit' : vals['price_unit'],
			#	'price_unit_old' : vals['price_unit_old'] if 'price_unit_old' in vals else 0,
			#	'product_id' : vals['product_id'],
			#	'price_type_id' : vals['price_type_id'],
			#	'partner_name' : new_data.invoice_id.partner_id.display_name,
			#	'partner_id' : new_data.invoice_id.partner_id.id,
			#	'product_uom' : vals['uos_id'],
			#	'discount_string' : vals['discount_string'] if 'discount_string' in vals else "0",
			#	'discount_string_old' : vals['discount_string_old'] if 'discount_string_old' in vals else "0",
			#	'name' : vals['name'],
			#	'invoice_id' : vals['invoice_id'] if 'invoice_id' in vals else 0,
			#	'sell_price_unit' : vals['sell_price_unit'] if 'sell_price_unit' in vals else 0,
			#	'buy_price_unit' : vals['buy_price_unit'] if 'buy_price_unit' in vals else 0,
			#	'type' : invoice_type,
			#	'origin': vals['origin'] if 'origin' in vals else "",
			#	'categ_id' : new_data.product_id.categ_id.name,
			#	}			

			#self._cost_price_watcher(cr, uid, vals,  context=ctx)

	#	return new_id
'''
'''
	def write(self, cr, uid, ids, vals, context={}):
		result = super(account_invoice_line, self).write(cr, uid, ids, vals, context=context)	
		# bila user mengubah salah satu dari empat field di bawah ini, cek dan update
		# current price bila perlu
		if any(field in vals.keys() for field in ['product_id','price_type_id','uos_id','price_unit','discount_string']):		
			for invoice_line in self.browse(cr, uid, ids):
			# gunakan price_type_id yang di line
				price_type_id = invoice_line.price_type_id.id
			# kalau ngga ada, pakai yang di vals
				if not price_type_id:
					price_type_id = vals.get('price_type_id', None)
			# kalau price_type_id masih kosong, pakai default sesuai type invoice ybs
				if not price_type_id:
					if invoice_line.invoice_id.type in ['in_invoice']:
						price_type = 'buy'
					else:
						price_type = 'sell'
					
					price_type_ids = self.pool.get('price.type').search(cr, uid, [
						('type','=',price_type),
						('is_default','=',True),
						])
				# give up, next record please!
					if len(price_type_ids) == 0: continue
					price_type_id = price_type_ids[0]
			# bikin product current price baru bila belum ada 
				product_id = invoice_line.product_id.id
				product_uom = invoice_line.uos_id.id
				categ_id = invoice_line.product_id.categ_id.name

				price_unit = invoice_line.price_unit
				price_unit_old = invoice_line.price_unit_old
				price_unit_nett = invoice_line.price_unit_nett
				price_unit_nett_old = invoice_line.price_unit_nett_old
				discount_string = invoice_line.discount_string
				discount_string_old = invoice_line.discount_string_old

				invoice_id = invoice_line.invoice_id.id
				sell_price_unit = invoice_line.sell_price_unit
				buy_price_unit = invoice_line.buy_price_unit
				name = invoice_line.name

				if vals.get('product_id', False): 
					product_id = vals['product_id']
					categ_id = vals['product_id'].categ_id.name
				if vals.get('uos_id', False): product_uom = vals['product_uom']
				if vals.get('price_unit', False): price_unit = vals['price_unit']
				if vals.get('price_unit_old', False): price_unit_old = vals['price_unit_old']
				if vals.get('price_unit_nett', False): price_unit_nett = vals['price_unit_nett']
				if vals.get('price_unit_nett_old', False): price_unit_nett_old = vals['price_unit_nett_old']				
				if vals.get('discount_string', False): discount_string = vals['discount_string']	
				if vals.get('discount_string_old', False): discount_string_old = vals['discount_string_old']
				if vals.get('invoice_id', False): invoice_id = vals['invoice_id']
				if vals.get('sell_price_unit', False): sell_price_unit = vals['sell_price_unit']
				if vals.get('buy_price_unit', False): buy_price_unit = vals['buy_price_unit']
				if vals.get('name', False): name = vals['name']

				#self.pool.get('price.list')._create_product_current_price_if_none(
				#		cr, uid, price_type_id, product_id, product_uom, price_unit, discount_string,
				#		partner_id=invoice_line.invoice_id.partner_id.id)
				
				if invoice_line.invoice_id.type in ['in_invoice']: #if "buy"
					invoice_type = 'in_invoice'
				elif invoice_line.invoice_id.type in ['out_invoice']:	
					invoice_type = 'out_invoice'
				ctx = {
					'price_unit_nett_old' : price_unit_nett_old,
					'price_unit_nett' : price_unit_nett,
					'price_unit' : price_unit,
					'price_unit_old' : price_unit_old,
					'product_id' :  product_id,
					'price_type_id' : price_type_id,
					'partner_name' : invoice_line.invoice_id.partner_id.display_name,
					'partner_id' : invoice_line.invoice_id.partner_id.id,
					'product_uom' : product_uom,
					'discount_string' : discount_string,
					'discount_string_old' : discount_string_old,
					'name' : name,
					'invoice_id' : invoice_id,
					'sell_price_unit' : sell_price_unit,
					'buy_price_unit' : buy_price_unit,
					'type' : invoice_type,
					'categ_id' : categ_id,
					}

				#check for changes and send notif
				#self._cost_price_watcher(cr, uid, vals,  context=ctx)
				
		return result
'''
# ==========================================================================================================================

class account_move_line(osv.osv):
	_inherit = 'account.move.line'
	_description = 'Modifikasi untuk menambah amount di SO'
	
	#def create(self, cr, uid, vals, context={}):
	#	new_id = super(account_move_line, self).create(cr, uid, vals, context=context)
	#	#if context.get('payment_method_type', False) and context.get('sale_order_id', False):
	#		#sale_order_obj = self.pool.get('sale.order')
	#		#payment_method_type = context['payment_method_type']
	#		#sale_order_id = context['sale_order_id']
	#		#sale_order_data = sale_order_obj.browse(cr, uid, sale_order_id)
	#		#if payment_method_type and vals.get('debit', False):
	#		#	if payment_method_type == 'transfer' or payment_method_type == 'receivable':
	#		#		sale_order_obj.write(cr, uid, sale_order_id, {
	#		#			'is_complex_payment': True
	#		#		})
	#	return new_id

	def name_get(self, cr, uid, ids, context=None):
		if not ids: return []
		result = []
	# name invoice line mengacu ke supplier invoice number (disimpan di name)
	# note: supplier invoice number harus diisi sebelum invoice divalidate, kalau tidak 
	# maka yang terismpan di name ini adalah nomor invoice (EXJ/....)
		for line in self.browse(cr, uid, ids, context=context):
			if line.ref:
				result.append((line.id, line.name or line.move_id.name))
			else:
				result.append((line.id, line.move_id.name))
		return result


# ==========================================================================================================================

class tbvip_day_end(osv.osv):
	_name = 'tbvip.day.end'
	_description = 'Ending Day'
	
	def calculate_omzet_cash(self, cr, uid, kas_id, context={}):
		# kas balance
		if kas_id:
			account_account_obj = self.pool.get('account.account')
			if isinstance(kas_id, int):
				return account_account_obj.browse(cr, uid, kas_id, context).balance
			else:
				return kas_id.balance
		else:
			return 0
	
	def calculate_amend_number(self, cr, uid, kas_id, day_end_date, context={}):
		day_end_date_datetime = datetime.strptime(day_end_date, '%Y-%m-%d %H:%M:%S')
		day_end_ids = self.search(cr, uid, [
			('kas_id', '=', kas_id),
			('day_end_date', '>=', day_end_date_datetime.strftime("%Y-%m-%d 00:00:00")),
			('day_end_date', '<', (day_end_date_datetime + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")),
		], context=context)
		return len(day_end_ids)
	
	def _default_modal_cash(self, cr, uid, context={}):

		user_data = self.pool['res.users'].browse(cr, uid, uid)
		branch_id = user_data.branch_id.id
		branch_data = self.pool['tbvip.branch'].browse(cr,uid,branch_id)
		branch_employee = branch_data.employee_list
		default_modal_cash = 0
		for employee in branch_employee:
			if employee.user_id.id == uid:
				default_modal_cash =  employee.default_modal_cash
		return default_modal_cash

		'''
		# default from employee setting
		employee_obj = self.pool.get('hr.employee')
		employee_ids = employee_obj.search(cr, uid, [
			('user_id', '=', uid),
		], limit=1, context=context)
		if employee_ids and len(employee_ids) == 1:
			return employee_obj.browse(cr, uid, employee_ids[0], context=context).default_modal_cash
		else:
			return 0
		'''
	
	def _default_branch_id(self, cr, uid, context={}):
		# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.id or None

	def _default_kas_id(self, cr, uid, context={}):
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		branch_id = user_data.branch_id.id
		branch_data = self.pool['tbvip.branch'].browse(cr,uid,branch_id)
		branch_employee = branch_data.employee_list
		default_account_cash = None
		for employee in branch_employee:
			if employee.user_id.id == uid:
				default_account_cash =  employee.default_account_cash.id
		return default_account_cash

	def _default_account_cash(self, cr, uid, context={}):
		#default pool cash vault collector
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		if user_data.branch_id.default_account_cash:
			return user_data.branch_id.default_account_cash.id
		else:
			return None

	def _default_partner_id(self, cr, uid, context={}):
		# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.partner_id.id or None
	
	_columns = {
		'day_end_date': fields.datetime('Date', required=True),
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		'amend_number': fields.integer('Amend Number'),
		'kas_id': fields.many2one('account.account', 'Kas', required=True, readonly=True, domain=[('is_tbvip_kas', '=', True)]),

		'qty_100': fields.integer('100', help='A Hundred Quantity'),
		'qty_200': fields.integer('200', help='Two Hundred Quantity'),
		'qty_500': fields.integer('500', help='Five Hundred Quantity'),
		'qty_1000': fields.integer('1000', help='A Thousand Quantity'),
		'qty_2000': fields.integer('2000', help='Two Thousand Quantity'),
		'qty_5000': fields.integer('5000', help='Five Thousand Quantity'),
		'qty_10000': fields.integer('10000', help='Ten Thousand Quantity'),
		'qty_20000': fields.integer('20000', help='Twenty Thousand Quantity'),
		'qty_50000': fields.integer('50000', help='Fifty Thousand Quantity'),
		'qty_100000': fields.integer('100000', help='A Hundred Thousand Quantity'),
		'amount_100': fields.integer('A Hundred Amount', help='A Hundred Amount'),
		'amount_200': fields.integer('Two Hundred Amount', help='Two Hundred Amount'),
		'amount_500': fields.integer('Five Hundred Amount', help='Five Hundred Amount'),
		'amount_1000': fields.integer('A Thousand Amount', help='A Thousand Amount'),
		'amount_2000': fields.integer('Two Thousand Amount', help='Two Thousand Amount'),
		'amount_5000': fields.integer('Five Thousand Amount', help='Five Thousand Amount'),
		'amount_10000': fields.integer('Ten Thousand Amount', help='Ten Thousand Amount'),
		'amount_20000': fields.integer('Twenty Thousand Amount', help='Twenty Thousand Amount'),
		'amount_50000': fields.integer('Fifty Thousand Amount', help='Fifty Thousand Amount'),
		'amount_100000': fields.integer('A Hundred Thousand Amount', help='A Hundred Thousand Amount'),
		'subtotal_cash': fields.float('Subtotal Cash'),
		
		'extra_desc_1': fields.char('Extra Desc 1'),
		'extra_amount_1': fields.integer('Extra Amount 1', help='Can be positive or negative'),
		'extra_desc_2': fields.char('Extra Desc 2'),
		'extra_amount_2': fields.integer('Extra Amount 2', help='Can be positive or negative'),
		'extra_desc_3': fields.char('Extra Desc 3'),
		'extra_amount_3': fields.integer('Extra Amount 3', help='Can be positive or negative'),
		
		'total_cash': fields.float('Total Cash'),
		'omzet_cash': fields.float('Omzet Cash (-)', help='Input in positive, but calculated as negative.'),
		'modal_cash': fields.float('Modal Cash (-)', help='Input in positive, but calculated as negative.'),
		
		'balance': fields.float('Balance'),
		'desc': fields.text('Description'),

		'default_account_cash' : fields.many2one('account.account', 'Default Cash Account'),
		'partner_id' : fields.many2one('res.partner','Partner Id Counterpart')
	}
	
	_defaults = {
		'day_end_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'branch_id': _default_branch_id,
		'modal_cash': _default_modal_cash,
		'default_account_cash' : _default_account_cash,
		'partner_id' : _default_partner_id,
		'kas_id': _default_kas_id,
	}
	
	def create(self, cr, uid, vals, context=None):
		vals['branch_id'] = self._default_branch_id(cr, uid, context=context)
		
		account_account_obj = self.pool.get('account.account')
		now = datetime.today().strftime('%Y-%m-%d %H:%M:%S.%f')
		#kas_id = vals['kas_id']
		kas_id = self._default_kas_id(cr, uid, context=context)
		kas = account_account_obj.browse(cr, uid, kas_id, context=context)
		journal_entry_obj = self.pool.get('account.move')
		vals.update({
			'amend_number': self.calculate_amend_number(cr, uid, kas_id, vals['day_end_date'], context=context),
			'amount_100': vals['qty_100'] * 100,
			'amount_200': vals['qty_200'] * 200,
			'amount_500': vals['qty_500'] * 500,
			'amount_1000': vals['qty_1000'] * 1000,
			'amount_2000': vals['qty_2000'] * 2000,
			'amount_5000': vals['qty_5000'] * 5000,
			'amount_10000': vals['qty_10000'] * 10000,
			'amount_20000': vals['qty_20000'] * 20000,
			'amount_50000': vals['qty_50000'] * 50000,
			'amount_100000': vals['qty_100000'] * 100000,
		})
		vals['subtotal_cash'] = \
			vals['amount_100'] + vals['amount_200'] + vals['amount_500'] + \
			vals['amount_1000'] + vals['amount_2000'] + vals['amount_5000'] + \
			vals['amount_10000'] + vals['amount_20000'] + vals['amount_50000'] + vals['amount_100000']
		vals['omzet_cash'] = self.calculate_omzet_cash(cr, uid, kas, context=context)
		vals['modal_cash'] = self._default_modal_cash(cr, uid, context=context)
		vals['default_account_cash'] = self._default_account_cash(cr,uid, context =context)
		vals['partner_id'] = self._default_partner_id(cr,uid, context =context)
		vals['total_cash'] = vals['subtotal_cash'] + vals['extra_amount_1'] + vals['extra_amount_2'] + vals['extra_amount_3']
		vals['balance'] = vals['total_cash'] - vals['omzet_cash'] - vals['modal_cash']
		
		# update to kas if not balanced
		if vals['balance'] != 0:
			#kas_id = vals['kas_id']	
			name = 'BALANCING :'+str(kas.name)+' (' + datetime.today().strftime('%Y-%m-%d %H:%M:%S')+')'
			acount_from = self.pool.get('account.account').search(cr, uid, [('code', '=', '122000')], limit=1)[0]
			entry_data = journal_entry_obj.account_move_prepare(cr, uid, self.pool.get('account.journal').search(cr, uid, [('type', 'in', ['cash'])], limit=1)[0], date=vals.get('journal_date'), ref=name)
			entry_data['line_id'] = [
				[0, False, {
					'name': name,
					'account_id': kas_id,#vals['kas_id'],
					'debit': vals['balance'] if vals['balance'] > 0 else 0,
					'credit': -vals['balance'] if vals['balance'] < 0 else 0,
					'partner_id': vals['partner_id'],
				}],
				[0, False, {
					'name': name,
					'account_id': acount_from,
					'debit': -vals['balance'] if vals['balance'] < 0 else 0,
					'credit': vals['balance'] if vals['balance'] > 0 else 0,
					'partner_id': vals['partner_id'],
				}],
			]
			new_entry_id = journal_entry_obj.create(cr, uid, entry_data, context=context)
			journal_entry_obj.post(cr, uid, [new_entry_id], context=context)

		#sisanya ditarik ke default account cash cabang tsb
		name = 'DAY END :'+str(kas.name)+' (' + datetime.today().strftime('%Y-%m-%d %H:%M:%S')+')'
		entry_data = journal_entry_obj.account_move_prepare(cr, uid, self.pool.get('account.journal').search(cr, uid, [('type', 'in', ['cash'])], limit=1)[0], date=vals.get('journal_date'), ref=name)
		entry_data['line_id'] = [
			[0, False, {
				'name': name,
				'account_id': kas_id,#vals['kas_id'],
				'debit': 0,
				'credit': vals['omzet_cash'] + vals['balance'],
				'partner_id': vals['partner_id'],
				#'to_check' : True,
			}],
			[0, False, {
				'name': name,
				'account_id': vals['default_account_cash'],
				'debit': vals['omzet_cash'] + vals['balance'],
				'credit': 0,
				'partner_id': vals['partner_id'],
				#'to_check' : True,
			}],
		]
		new_entry_id = journal_entry_obj.create(cr, uid, entry_data, context=context)	
		journal_entry_obj.post(cr, uid, [new_entry_id], context=context)
		
		return super(tbvip_day_end, self).create(cr, uid, vals, context)
	
	def onchange_day_end_kas_date(self, cr, uid, ids, kas_id, day_end_date, context=None):
		return {
			'value': {
				'omzet_cash': self.calculate_omzet_cash(cr, uid, kas_id, context=context),
				'amend_number': self.calculate_amend_number(cr, uid, kas_id, day_end_date, context=context)
			}
		}
	
	def onchange_qty(self, cr, uid, ids, qty_100, qty_200, qty_500, qty_1000, qty_2000, qty_5000, qty_10000,
			qty_20000, qty_50000, qty_100000, context=None):
		result = {'value': {
			'amount_100': qty_100 * 100,
			'amount_200': qty_200 * 200,
			'amount_500': qty_500 * 500,
			'amount_1000': qty_1000 * 1000,
			'amount_2000': qty_2000 * 2000,
			'amount_5000': qty_5000 * 5000,
			'amount_10000': qty_10000 * 10000,
			'amount_20000': qty_20000 * 20000,
			'amount_50000': qty_50000 * 50000,
			'amount_100000': qty_100000 * 100000,
		}}
		result['value']['subtotal_cash'] = \
			result['value']['amount_100'] + result['value']['amount_200'] + \
			result['value']['amount_500'] + result['value']['amount_1000'] + \
			result['value']['amount_2000'] + result['value']['amount_5000'] + \
			result['value']['amount_10000'] + result['value']['amount_20000'] + \
			result['value']['amount_50000'] + result['value']['amount_100000']
		return result
	
	def onchange_cash(self, cr, uid, ids, subtotal_cash, extra_amount_1, extra_amount_2, extra_amount_3, context=None):
		return {'value': {
			'total_cash': subtotal_cash + extra_amount_1 + extra_amount_2 + extra_amount_3,
		}}
	
	def onchange_balance_cash(self, cr, uid, ids, total_cash, omzet_cash, modal_cash, context=None):
		return {'value': {
			'balance': total_cash - omzet_cash - modal_cash,
		}}


# ==========================================================================================================================

class account_account(osv.osv):
	_inherit = 'account.account'
	
	_columns = {
		'is_tbvip_kas': fields.boolean('Kas'),
	}
	

# ==========================================================================================================================
class account_invoice_report(osv.osv):
	_inherit = "account.invoice.report"

	def _select(self):
		select_str = """
			SELECT sub.id, sub.date, sub.product_id, sub.partner_id, sub.country_id,
				sub.payment_term, sub.period_id, sub.uom_name, sub.currency_id, sub.journal_id,
				sub.fiscal_position, sub.user_id, sub.company_id, sub.nbr, sub.type, sub.state,
				sub.categ_id, sub.date_due, sub.account_id, sub.account_line_id, sub.partner_bank_id,
				sub.product_qty, sub.price_total as price_total, sub.price_average as price_average,
				cr.rate as currency_rate, sub.residual as residual, sub.commercial_partner_id as commercial_partner_id
		"""
		return select_str