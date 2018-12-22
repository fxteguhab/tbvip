from openerp.osv import osv, fields

_CAMPAIGN_TYPE_ = [
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
]

class tbvip_campign(osv.osv):
	_name = "tbvip.campaign"
	_description = "Promo Campaign"

	_columns = {
		'name': fields.char('Campaign Name', required=True),
		'partner_id':fields.many2one('res.partner', 'Supplier', readonly=True, states={'draft':[('readonly',False)]}),
		'date_start': fields.datetime('Start Date', required=True),
		'date_end': fields.datetime('End Date', required=True),
		'campaign_type': fields.selection(_CAMPAIGN_TYPE_, 'Campaign Type', required=True),
		'target_amount': fields.float('Target Amount'),
		'reward_type': fields.selection(_REWARD_TYPE_, 'Reward Type', required=True),
		'discount_str':fields.char('Extra Discount'),
		'product_line_ids': fields.one2many('tbvip.campaign.product.line', 'campaign_id', 'Product Lines'),
		'purchase_list':

	}

class tbvip_campign_product_line(osv.osv):
	_name = "tbvip.campaign.product.line"
	_description = "Detail Product Line"

	_columns = {
		'campaign_id': fields.many2one('tbvip.campaign', 'Campaign', required=True, ondelete="cascade"),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'poin' : fields.float('Poin'),
		'discount_str':fields.char('Extra Discount'),
	}