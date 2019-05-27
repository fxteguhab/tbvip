from openerp import api
from openerp.osv import osv, fields


# ==========================================================================================================================

class res_partner(osv.osv):
	_inherit = 'res.partner'
	
	#---------- OVERIDES--------------------------------
	def _invoice_total2(self, cr, uid, ids, field_name, arg, context=None):
		result = {}
		account_invoice_report = self.pool.get('account.invoice.report')
		user = self.pool['res.users'].browse(cr, uid, uid, context=context)
		user_currency_id = user.company_id.currency_id.id
		for partner_id in ids:
			all_partner_ids = self.pool['res.partner'].search(
				cr, uid, [('id', 'child_of', partner_id)], context=context)

			# searching account.invoice.report via the orm is comparatively expensive
			# (generates queries "id in []" forcing to build the full table).
			# In simple cases where all invoices are in the same currency than the user's company
			# access directly these elements

			# generate where clause to include multicompany rules
			where_query = account_invoice_report._where_calc(cr, uid, [
				('partner_id', 'in', all_partner_ids), ('state', 'not in', ['draft', 'cancel'])
			], context=context)
			account_invoice_report._apply_ir_rules(cr, uid, where_query, 'read', context=context)
			from_clause, where_clause, where_clause_params = where_query.get_sql()


			query = """ WITH currency_rate (currency_id, rate, date_start, date_end) AS (
								SELECT r.currency_id, r.rate, r.name AS date_start,
									(SELECT name FROM res_currency_rate r2
									 WHERE r2.name > r.name AND
										   r2.currency_id = r.currency_id
									 ORDER BY r2.name ASC
									 LIMIT 1) AS date_end
								FROM res_currency_rate r
								)
					  SELECT SUM(price_total) as total
						FROM account_invoice_report account_invoice_report, currency_rate cr
					   WHERE %s
						 AND cr.currency_id = %%s
						 AND (COALESCE(account_invoice_report.date, NOW()) >= cr.date_start)
						 AND (COALESCE(account_invoice_report.date, NOW()) < cr.date_end OR cr.date_end IS NULL)
						 AND account_invoice_report.type in ('out_invoice', 'out_refund')
					""" % where_clause

			# price_total is in the currency with rate = 1
			# total_invoice should be displayed in the current user's currency
			
			cr.execute(query, where_clause_params + [user_currency_id])
			result[partner_id] = cr.fetchone()[0]

		return result

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_partner_id': fields.integer('MySQL Partner ID'),
		'phone': fields.char('Phone', size=100),
		'total_invoiced': fields.function(_invoice_total2, string="Total Invoiced", type='float', groups='account.group_account_invoice'),
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