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

