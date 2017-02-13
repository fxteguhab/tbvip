from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta

# ==========================================================================================================================

class hr_employee(osv.osv):
	
	_inherit = 'hr.employee'

# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_employee_id': fields.integer('MySQL Employee ID'),
		'address': fields.text('Address'),
	}
	
