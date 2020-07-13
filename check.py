from openerp.osv import osv, fields
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _


# ==========================================================================================================================

class tbvip_check_book(osv.osv):
	_name = "tbvip.check.book"
	_description = "Master Check Book"

# COLUMNS ------------------------------------------------------------------------------------------------------------------

	def _total_sheets(self, cr, uid, ids, field_name, arg, context=None):
		result = dict.fromkeys(ids, 0)
		for check in self.browse(cr, uid, ids):
			result[check.id] = check.end_at - check.start_from + 1
		return result

	
	_columns = {
		'bank': fields.many2one('res.bank', 'Bank'),
		'issue_date': fields.date('Issue Date', required=True, help='Check released date.'),
		'code':fields.char('Code',required = True, size = 2),
		'start_from': fields.integer('Start From', required=True, help='Check starting number.'),
		'end_at': fields.integer('End At', required=True, help='Check ending number.'),
		'total_sheets': fields.function(_total_sheets, string='Total Sheets', type='integer', store={}, help='Total sheets, calculated as End At - Start From + 1.'),
		'total_used': fields.integer('Total Used', help='Total sheets that have been used.'),
		'check_line' : fields.one2many('tbvip.check.line', 'check_id', 'Check Lines'),
	}
	
	_sql_constraints = [
		('start_less_than_end', 'CHECK(end_at >= start_from)', 'Start number should be less than end number.'),
		('number_less_than_zero', 'CHECK(end_at >= 1)', 'Start and end number should be more than 0.'),
	]

	_defaults = {
		'issue_date':  lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'total_used' : 0,
	}

# OVERRIDES ----------------------------------------------------------------------------------------------------------------

	def create(self, cr, uid, vals, context={}):
		vals['code'] = vals.get('code',False).upper()
		check_line_obj = self.pool.get('tbvip.check.line')		
		check_lines = []
		for check_no in range(vals.get('start_from', 0),vals.get('end_at', 0)+1):
			check_lines.append([0, False,{
				'code': vals.get('code', False),
				'no': check_no,
				}])	
		vals['check_line'] = check_lines	
		return super(tbvip_check_book, self).create(cr, uid, vals, context)

class tbvip_check_line(osv.osv):
	_name = "tbvip.check.line"
	_description = "Master Check Book Line"

# COLUMNS ------------------------------------------------------------------------------------------------------------------

	_columns = {
		'check_id': fields.many2one('tbvip.check.book', 'Check Reference', ondelete='cascade', select=True, readonly=True),
		#'payment_id':
		'code':fields.char('Code', size = 8),
		'no': fields.integer('No',help='Check number.'),
		'issue_date': fields.date('Issue Date', help='Check create date.'),
		'paid_date': fields.date('Paid Date', help='Check paid date.'),
		'maturity_date': fields.date('Maturity Date', help='Check maturity date.'),		
		'effective_date': fields.date('Effective Date', help='Check effective date.'),
		'amount': fields.integer('Value', help='Check value.'),
		'partner_id':fields.many2one('res.partner', 'Partner', readonly=True),
		'bank_id': fields.many2one('res.partner.bank', 'Supplier Bank Account'),
	}