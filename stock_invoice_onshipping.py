from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

class stock_invoice_onshipping(osv.osv_memory):

	_inherit = 'stock.invoice.onshipping'

	_defaults = {
		'invoice_date': lambda *a: datetime.today().strftime('%Y-%m-%d'),
	}

	