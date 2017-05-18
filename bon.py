from openerp.osv import osv, fields
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
	
	_columns = {
		'issue_date': fields.date('Issue Date', required=True, help='Book released date.'),
		'user_id': fields.many2one('res.users', 'User', required=True, ondelete='restrict', help='Whom the book is given to.'),
		'start_from': fields.integer('Start From', required=True, help='Bon starting number.'),
		'end_at': fields.integer('End At', required=True, help='Bon ending number.'),
		'total_sheets': fields.function(_total_sheets, string='Total Sheets', type='float', store={},
			help='Total sheets, calculated as End At - Start From + 1.'),
		'total_used': fields.integer('Total Used', help='Total sheets that have been used.'),
		'used_numbers': fields.text('Used Numbers', help='All bon numbers that have been used.'),
	}
	
	_sql_constraints = [
		('start_less_than_end', 'CHECK(end_at >= start_from)', 'Start number should be less than end number.'),
		('number_less_than_zero', 'CHECK(end_at >= 1)', 'Start and end number should be more than 0.'),
	]
	
# OVERRIDES ----------------------------------------------------------------------------------------------------------------
	
	def unlink(self, cr, uid, ids, context=None):
		bon_books = self.browse(cr, uid, ids)
		for bon in bon_books:
			if bon.total_used > 0:
				raise osv.except_orm(_('Deleting bon book error'), _('You cannot delete any bon book that has been used.'))
		return super(tbvip_bon_book, self).unlink(cr, uid, ids, context)