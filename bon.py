from openerp.osv import osv, fields
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _

# ==========================================================================================================================

class tbvip_bon_book(osv.osv):
	_name = "tbvip.bon.book"
	_description = "Master Bon Book"
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	def _total_sheets(self, cr, uid, ids, field_name, arg, context=None):
		result = dict.fromkeys(ids, 0)
		for bon in self.browse(cr, uid, ids):
			result[bon.id] = bon.end_at - bon.start_from + 1
		return result
	
	def _default_branch_id(self, cr, uid, context={}):
		# default branch adalah tempat user sekarang ditugaskan
		user_data = self.pool['res.users'].browse(cr, uid, uid)
		return user_data.branch_id.id or None
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
		'issue_date': fields.date('Issue Date', required=True, help='Book released date.'),
		'employee_id': fields.many2one('hr.employee', 'Employee', required=True, help='Whom the book is given to.'),
		'start_from': fields.integer('Start From', required=True, help='Bon starting number.'),
		'end_at': fields.integer('End At', required=True, help='Bon ending number.'),
		'total_sheets': fields.function(_total_sheets, string='Total Sheets', type='integer', store={},
			help='Total sheets, calculated as End At - Start From + 1.'),
		'total_used': fields.integer('Total Used', help='Total sheets that have been used.'),
		'used_numbers': fields.text('Used Numbers', help='All invoice number(s) that have been used.'),
	}
	
	_sql_constraints = [
		('start_less_than_end', 'CHECK(end_at >= start_from)', 'Start number should be less than end number.'),
		('number_less_than_zero', 'CHECK(end_at >= 1)', 'Start and end number should be more than 0.'),
	]

	_defaults = {
		'branch_id': _default_branch_id,
		'issue_date':  lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
	}
	
# METHOD -------------------------------------------------------------------------------------------------------------------
	
	def _cek_crossing_bon_number(self, cr, uid, cek_bon_id, issue_date, start_from, end_at, branch_id):
		bon_book_ids = self.search(cr, uid,
			['&',('branch_id','=',branch_id),'&',('id','!=',cek_bon_id),'&',('issue_date','=',issue_date),'|','&',('end_at', '>=', start_from),('end_at', '<=', end_at),
				'|','&',('start_from', '>=', start_from),('start_from', '<=', end_at),
				'&', ('start_from', '<=', start_from),('end_at', '>=', end_at)
			])
		
		if len(bon_book_ids) > 0:
			bon = self.browse(cr, uid, bon_book_ids[0])
			raise osv.except_orm(_('Bon book number error'),
				_('Bon book with number %s - %s at issue date %s has been used' % (bon.start_from, bon.end_at, issue_date)))

# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		id = super(tbvip_bon_book, self).create(cr, uid, vals, context)
		# Cek apakah ada bon yang saling bersilangan untuk issue date yang sama
		branch_id = vals['branch_id']
		self._cek_crossing_bon_number(cr, uid, id, vals.get('issue_date', False), vals.get('start_from', False), vals.get('end_at', False), branch_id)
		return id
	
	def write(self, cr, uid, ids, vals, context=None):
		# Cek apakah ada bon yang saling bersilangan untuk issue date yang sama
		user_obj = self.pool.get('res.users')
		for bon in self.browse(cr, uid, ids):
			start_from = bon.start_from
			end_at = bon.end_at
			issue_date = bon.issue_date
			branch_id = bon.branch_id.id
			
			branch_id_temp = self._default_branch_id(cr, uid, context)
			
			if vals.get('start_from', False):
				start_from = vals.get('start_from', False)
			if vals.get('end_at', False):
				end_at = vals.get('end_at', False)
			if vals.get('issue_date', False):
				issue_date = vals.get('issue_date', False)
			if vals.get('branch_id', False):
				branch_id = vals.get('branch_id', False)
				
			self._cek_crossing_bon_number(cr, uid, bon.id, issue_date, start_from, end_at, branch_id)
		
		return super(tbvip_bon_book, self).write(cr, uid, ids, vals, context)
	
	def unlink(self, cr, uid, ids, context=None):
		bon_books = self.browse(cr, uid, ids)
		for bon in bon_books:
			if bon.total_used > 0:
				raise osv.except_orm(_('Deleting bon book error'), _('You cannot delete any bon book that has been used.'))
		return super(tbvip_bon_book, self).unlink(cr, uid, ids, context)

	def _cek_last_book_residual(self,cr,uid,employee_id,branch_id):
		bon_book_ids = self.search(cr, uid,[('employee_id','=',employee_id),('branch_id','=',branch_id)],order = "id desc")
		if len(bon_book_ids) > 1:
			last_id = bon_book_ids[1]
			bon = self.browse(cr, uid, last_id)
			residual = (bon.end_at - bon.start_from + 1)-bon.total_used
		else:
			residual = 0
		return residual