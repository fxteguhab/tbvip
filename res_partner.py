from openerp import api
from openerp.osv import osv, fields


# ==========================================================================================================================

class res_partner(osv.osv):
	_inherit = 'res.partner'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_partner_id': fields.integer('MySQL Partner ID'),
		'phone': fields.char('Phone', size=100),
	}
	
	_defaults = {
		'buy_price_type_id': lambda self, cr, uid, ctx:
			self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'tbvip.tbvip_normal_price_buy'),
		'sell_price_type_id': lambda self, cr, uid, ctx:
			self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'tbvip.tbvip_normal_price_sell'),
	}

# ==========================================================================================================================

class res_partner_bank(osv.Model):
	_inherit = 'res.partner.bank'
	
	_defaults = {
		'state': 'bank',
	}
	
	@api.multi
	def name_get(self):
		"""
		Append owner_name to bank name_get
		:return:
		"""
		result = super(res_partner_bank, self).name_get()
		for idx, tuple in enumerate(result):
			bank = self.browse(tuple[0])
			result[idx] = (result[idx][0], result[idx][1] + ' - {}'.format(bank.owner_name))
		return result