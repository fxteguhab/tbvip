from openerp.osv import osv, fields
from datetime import datetime

_MEASURE_ = [
	('tonase', 'Product Weight'),
	('value', 'Product Value'),
	('poin', 'Product Poin'),
]

_REWARD_TYPE_ = [
	('cash', 'Cash'),
	('product_id','Product'),
	('voucher','Voucher'),
	('gold','Gold'),
	('discount', 'Discount'),
	('poin','Poin'),
	('other','Lainnya'),
]

_INVOICE_TYPE_ = [
	('one_invoice', 'In 1 Invoice'),
	('many_invoice', 'Accumulation'),
]

_STATE = [
	('draft', 'Draft'),
	('running', 'Running'),
	('expired', 'Expired'),
]

class tbvip_campign(osv.osv):
	_name = "tbvip.campaign"
	_description = "Promo Campaign"

	_columns = {
		'partner_id':fields.many2one('res.partner', 'Partner', required=True),
		'name': fields.char('Campaign Name', required=True),
		'date_start': fields.date('Start Date', required=True),
		'date_end': fields.date('End Date', required=True),
		'date_reward' : fields.date('Reward Date'),
		'measure': fields.selection(_MEASURE_, 'Measure', required=True),
		'current_amount': fields.float('Current Amount'),
		'current_achievement' : fields.float('Reward Achievement'),
		'invoice_type': fields.selection(_INVOICE_TYPE_, 'Invoice Type', required=True),
		'target_line_ids' : fields.one2many('tbvip.campaign.target.line', 'campaign_id', 'Target Lines'),
		'product_line_ids': fields.one2many('tbvip.campaign.product.line', 'campaign_id', 'Product Lines'),
		'category_line_ids': fields.one2many('tbvip.campaign.category.line', 'campaign_id', 'Category Lines'),
		'invoice_line_ids': fields.one2many('tbvip.campaign.invoice.line', 'campaign_id', 'Invoice Lines'),
		'reward_received' : fields.boolean('Reward Received'),
		'state': fields.selection(_STATE,'State', required=True),
	}

	_defaults = {
		'date_start': lambda *a: datetime.today().strftime('%Y-%m-%d'),
		'date_end': lambda *a: datetime.today().strftime('%Y-%m-%d'),
		'state' : 'draft',
		'invoice_type': 'many_invoice',
	}

	def set_to_running(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {
			'state': 'running'
		}, context=context)
		return True

	def set_to_expired(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {
			'state': 'expired'
		}, context=context)
		return True

	def set_to_draft(self, cr, uid, ids, context=None):
		self.write(cr, uid, ids, {
			'state': 'draft'
		}, context=context)
		return True


	def cron_expired_campaign(self, cr, uid, context={}):
		today = datetime.now()
		today_campaign_ids = self.search(cr, uid, [
			('date_end', '<=', today.strftime("%Y-%m-%d 23:59:59")),
			('state', '=', 'running')
		], context=context)
		for today_campaign_id in today_campaign_ids:
			try:
				# one by one so that if one fails, others can still be updated
				self.set_to_expired(cr, uid, today_campaign_id, context)
			except:
				pass
		return True

	def recalculate_campaign_promo(self, cr, uid, ids, context={}):
		active_campaign = self.browse(cr, uid, ids)
		campaign_id = active_campaign.id
		partner_id = active_campaign.partner_id.id
		date_start = active_campaign.date_start
		date_end = active_campaign.date_end
		targets = active_campaign.target_line_ids
		invoice_line_id = self.pool['tbvip.campaign.invoice.line']
		account_invoice_line_obj = self.pool['account.invoice.line']

		product_campaign_ids = self.pool['tbvip.campaign.product.line'].search(cr, uid, [('campaign_id', '=',campaign_id)])	
		product_template_ids_from_product = self.pool['tbvip.campaign.product.line'].browse(cr, uid, product_campaign_ids)
		product_template_ids = []
		for template_id in product_template_ids_from_product:
			product_template_ids.append(template_id.product_template_id.id)
		product_ids_from_template = self.pool['product.product'].search(cr, uid, [('product_tmpl_id', 'in',product_template_ids)])

		category_campaign_ids = self.pool['tbvip.campaign.category.line'].search(cr, uid, [('campaign_id', '=',campaign_id)])
		category_ids = self.pool['tbvip.campaign.category.line'].browse(cr, uid, category_campaign_ids)
		product_categ_ids = []
		for category_id in category_ids:
			product_categ_ids.append(category_id.product_category_id.id)
		product_template_ids = self.pool['product.template'].search(cr, uid, [('categ_id', 'in',product_categ_ids)])
		product_ids_from_categ = self.pool['product.product'].search(cr, uid, [('product_tmpl_id', 'in',product_template_ids)])
		
		product_str = ''
		for product_id in product_ids_from_template:
			product_str += str(product_id)+', '
		for product_id in product_ids_from_categ:
			product_str += str(product_id)+', '
		product_str += '0'

		#SELECT ONLY INVOICE LINE WITH CAMPAIGN PRODUCT
		cr.execute("""
				SELECT 
					id
				FROM account_invoice_line
				WHERE
					partner_id = '%s' AND
					write_date BETWEEN '%s' AND  '%s' AND
					product_id IN (%s)
				ORDER BY write_date
				""" % (partner_id,date_start,date_end,product_str))

		account_invoice_line = []
		for row in cr.dictfetchall():
			account_invoice_line.append(row['id'])
		account_invoice_line_ids = account_invoice_line_obj.browse(cr, uid, account_invoice_line)

		#RESET CAMPAIGN
		active_campaign.current_amount = 0
		active_campaign.current_achievement = 0
		for target in targets:
			target.achievement_counter = 0

		invoice_line_id_to_delete = invoice_line_id.search(cr, uid, [('campaign_id', '=',campaign_id)])
		invoice_line_id.unlink(cr, uid, invoice_line_id_to_delete)

		#RECALC PER INVOICE LINE
		for campaign_invoice_line in account_invoice_line_ids: 
			invoice_id = campaign_invoice_line.invoice_id.id
			product_id = campaign_invoice_line.product_id.id
			price_unit = campaign_invoice_line.price_unit
			invoice_date = campaign_invoice_line.write_date
			product_name = campaign_invoice_line.name
			invoice_number = campaign_invoice_line.origin
			qty = campaign_invoice_line.quantity
			product_template_id = self.pool['product.product'].browse(cr, uid, product_id).product_tmpl_id
			product_template = self.pool['product.template'].browse(cr, uid, product_template_id.id) 
			categ_id = product_template.categ_id

			qty_min = 0
			poin = 0
			weight = 0

			product_ids = self.pool['tbvip.campaign.product.line'].search(cr, uid, [('campaign_id', '=',campaign_id),('product_template_id', '=',product_template_id.id)])	
			for product in self.pool['tbvip.campaign.product.line'].browse(cr,uid,product_ids) : 
				min_qty = product.min_qty
				poin = product.poin
				weight = product_template.tonnage

			if not product_ids:
				category_ids = self.pool['tbvip.campaign.category.line'].search(cr, uid, [('campaign_id', '=',campaign_id),('product_category_id', '=',categ_id.id)])
				for category in self.pool['tbvip.campaign.category.line'].browse(cr,uid,category_ids): 
					min_qty = category.min_qty
					poin = category.poin
					product_category = self.pool['product.category'].browse(cr,uid,category.product_category_id.id)
					weight = product_category.tonnage

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

			invoice_line_id.create(cr, uid, {
				'campaign_id': campaign_id,
				'invoice_id': invoice_id,
				'invoice_date': invoice_date,
				'invoice_origin':invoice_number,
				'qty':qty,
				'invoice_ref': product_name,
				'amount': current_amount,
			}, context)

		if active_campaign.invoice_type == 'many_invoice':
			remainder = active_campaign.current_amount
			for target in targets:
				if (remainder >= target.target_amount):
					target.achievement_counter =  remainder // target.target_amount
					active_campaign.current_achievement += target.achievement_counter 
					remainder = remainder % target.target_amount

class tbvip_campign_product_line(osv.osv):
	_name = "tbvip.campaign.product.line"
	_description = "Detail Product Line"

	_columns = {
		'campaign_id': fields.many2one('tbvip.campaign', 'Campaign', required=True, ondelete="cascade"),
		'product_template_id': fields.many2one('product.template', 'Product', required=True, ondelete='restrict'),
		'min_qty' : fields.float('Min Qty'),
		'poin' : fields.float('Poin'),
		'discount_str':fields.char('Extra Discount'),
	}

	_defaults = {
		'min_qty' : 1,
	}

class tbvip_campign_product_line(osv.osv):
	_name = "tbvip.campaign.category.line"
	_description = "Detail category Line"

	_columns = {
		'campaign_id': fields.many2one('tbvip.campaign', 'Campaign', required=True, ondelete="cascade"),
		'product_category_id': fields.many2one('product.category', 'Product Category', required=True, ondelete='restrict'),
		'min_qty' : fields.float('Min Qty'),
		'poin' : fields.float('Poin'),
		'discount_str':fields.char('Extra Discount'),
	}

	_defaults = {
		'min_qty' : 1,
	}


class tbvip_campign_target_line(osv.osv):
	_name = "tbvip.campaign.target.line"
	_description = "Target Campaign Line"
	_order = 'target_amount desc'

	_columns = {
		'campaign_id': fields.many2one('tbvip.campaign', 'Campaign', required=True, ondelete="cascade"),
		'target_amount': fields.float('Target Amount', required=True), 
		'reward_type': fields.selection(_REWARD_TYPE_, 'Reward Type', required=True),
		'reward_amount' : fields.char('Reward Amount', required=True), 
		'reward_desc':fields.char('Reward Desc'),
		'achievement_counter' : fields.float('Reward Achievement'),
	}

class tbvip_campign_invoice_line(osv.osv):
	_name = "tbvip.campaign.invoice.line"
	_description = "Invoice Campaign Line"
	_order = 'amount desc'

	_columns = {
		'campaign_id': fields.many2one('tbvip.campaign', 'Campaign', required=True, ondelete="cascade"),
		'invoice_id': fields.many2one('account.invoice', 'Invoice(s)', required=True, ondelete='restrict'),
		'invoice_date' : fields.date('Invoice Date', required=True),
		'invoice_origin':fields.char('Origin'),
		'qty' : fields.float('Qty'),
		'invoice_ref' : fields.char('Product'),
		'amount' : fields.float('Total Amount'),
	}
