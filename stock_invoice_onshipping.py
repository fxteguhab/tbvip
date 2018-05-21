from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

class stock_invoice_onshipping(osv.osv_memory):

	_inherit = 'stock.invoice.onshipping'

	_defaults = {
		'invoice_date': lambda *a: datetime.today().strftime('%Y-%m-%d'),
	}

	def open_invoice(self, cr, uid, ids, context=None):
	# setelah create invoice, pindah ke detail invoice tsb, bukan list invoicenya
		result = super(stock_invoice_onshipping, self).open_invoice(cr, uid, ids, context=context)
		if isinstance(result, dict):
		# ambil invoice yang udah digenerate dari super. asumsi hasil generate hanya satu,
		# so ambil yang pertama aja
			try:
				form_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'account.invoice_supplier_form')
				exec("action_domain = %s" % result['domain'])
				invoice_ids = action_domain[0][2]
				invoice_id = invoice_ids[0]
				result = {
					'type': 'ir.actions.act_window',
					'name': 'Invoice Details',
					'view_mode': 'form',
					'view_type': 'form',
					'views': [(form_id,'form')],
					'view_id': form_id,
					'res_model': 'account.invoice',
					'res_id': invoice_id,
				}
			except KeyError as e:
				return result
		return result

	