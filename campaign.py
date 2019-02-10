from openerp.osv import osv, fields
from datetime import datetime

_MEASURE_ = [
	('tonase', 'Product Weight'),
	('value', 'Product Value'),
	('poin', 'Product Poin'),
]

_REWARD_TYPE_ = [
	('cash', 'Cash'),
	('cn', 'Invoice Discount'),
	('product_id','Product'),
	('discount', 'Discount per Product'),
	('poin','Poin per Product'),
	('voucher','Voucher'),
	('gold','Gold'),
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

class tbvip_campign_target_line(osv.osv):
	_name = "tbvip.campaign.target.line"
	_description = "Target Reward Line"
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
	_description = "Invoice Reward Line"
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
