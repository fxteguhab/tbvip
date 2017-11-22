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
		tpl = tpl_lookup.get_template('kontra_bon.txt')
		tpl_line = tpl_lookup.get_template('kontra_bon_line.txt')
		
		for acc_vou in self.browse(cr, uid, ids, context=context):
			company = acc_vou.create_uid.company_id
			company_name = company.name if company.name else ''
			branch_name = acc_vou.create_uid.branch_id.name if acc_vou.create_uid.branch_id.name else ''
			supplier_name = acc_vou.partner_id.name if acc_vou.partner_id.name else ''
			
			# add lines
			row_number = 0
			account_voucher_line = []
			for line in acc_vou.line_dr_ids:
				row_number += 1
				row = tpl_line.render(
					no=str(row_number),
					reference_number=line.move_line_id.invoice.name if line.move_line_id and line.move_line_id.invoice else '-',
					delivery_date=datetime.strptime(line.date_original, '%Y-%m-%d').strftime('%Y-%m-%d'),
					total=str(line.amount),
				)
				account_voucher_line.append(row)
			# render account voucher
			account_voucher = tpl.render(
				branch_name=branch_name,
				company_name=company_name,
				supplier_name=supplier_name,
				payment_date=datetime.strptime(acc_vou.date, '%Y-%m-%d').strftime('%Y-%m-%d'),
				lines=account_voucher_line,
				subtotal=str(acc_vou.amount),
				discount=str(0),
				total=str(acc_vou.amount),
			)
			
			# Create temporary file
			path_file = 'openerp/addons/tbvip/tmp/'
			filename = path_file + 'print_kontra_bon ' + datetime.now().strftime('%Y-%m-%d %H%M%S') + '.txt'
			# Put rendered string to file
			f = open(filename, 'w')
			f.write(account_voucher.replace("\r\n", "\n"))
			f.close()
			# Process printing
			os.system('lpr -Pnama_printer %s' % filename)
		# Remove printed file
		# os.remove(filename) #TODO UNCOMMENT
		return True


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
