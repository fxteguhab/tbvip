from openerp.osv import osv, fields
from datetime import datetime, date, timedelta



from mako.lookup import TemplateLookup
import os
tpl_lookup = TemplateLookup(directories=['openerp/addons/tbvip/print_template'])


# ==========================================================================================================================


class account_voucher(osv.osv):
	_inherit = 'account.voucher'
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
		result = super(account_voucher, self).onchange_partner_id(
			cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context)
		
		partner_obj = self.pool.get('res.partner')
		partner = partner_obj.browse(cr, uid, [partner_id])
		# if not result.get('domain', False):
		# 	result['domain'] = {}
		# result['domain'].update({
		# 	'bank_id': [('id', 'in', partner.bank_ids.ids)],
		# })
		
		return result
	
	# FIELD FUNCTION METHODS ------------------------------------------------------------------------------------------------
	
	def _bank_ids(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for account_voucher_data in self.browse(cr, uid, ids, context=context):
			res_partner_obj = self.pool.get('res.partner')
			for partner_data in res_partner_obj.browse(cr, uid, account_voucher_data.partner_id.id):
				if len(partner_data.bank_ids) > 0:
					result[account_voucher_data.id] = partner_data.bank_ids[0].id
				else:
					result[account_voucher_data.id] = None
		return result
	
	def _is_ready(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for account_voucher_data in self.browse(cr, uid, ids, context=context):
			result[account_voucher_data.id] = True if account_voucher_data.reference and account_voucher_data.reference != '' else False
		return result
				
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'check_maturity_date': fields.date(string='Check Maturity Date',
			readonly=True, states={'draft': [('readonly', False)]}),
		# 'bank_id': fields.function(_bank_ids, string="Bank Account", type='many2one', relation="res.partner.bank", readonly=False),
		'bank_id': fields.many2one('res.partner.bank', 'Bank Account'),
		'is_ready': fields.function(_is_ready, type="boolean", string="Is Ready", store=True),
	}
	
	# PRINTS ----------------------------------------------------------------------------------------------------------------
	
	def print_kontra_bon(self, cr, uid, ids, context):
		if self.browse(cr,uid,ids)[0].line_dr_ids:
			return {
				'type' : 'ir.actions.act_url',
				'url': '/tbvip/print/account.voucher/' + str(ids[0]),
				'target': 'self',
			}
		else:
			raise osv.except_osv(_('Print Kontra Bon Error'),_('Kontra Bon must have at least one line to be printed.'))


# ==========================================================================================================================


class account_voucher_line(osv.osv):
	_inherit = 'account.voucher.line'
	
	def _purchase_order_id(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		for line in self.browse(cr, uid, ids, context=context):
			invoice_id = line.move_line_id.invoice.id
			if invoice_id:
				cr.execute("""
					SELECT purchase_id
					FROM purchase_invoice_rel
					WHERE invoice_id = {}
				""".format(invoice_id))
				res = cr.fetchone()
				if res and len(res) > 0:
					result[line.id] = res[0]
		return result

	_columns = {
		'purchase_order_id': fields.function(_purchase_order_id, type='many2one', relation='purchase.order',
			store=True, string='Purchase Order'),
	}
