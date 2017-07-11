from openerp.osv import osv, fields


# ==========================================================================================================================

class hr_employee(osv.osv):
	_inherit = 'hr.employee'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_employee_id': fields.integer('MySQL Employee ID'),
		'address': fields.text('Address'),
		'type': fields.selection([('is_spg', "SPG"), ('is_non_spg', "Non-SPG")], 'Type'),
		'employee_no': fields.char('Employee No.')
	}

class hr_attendance(osv.osv):
	_inherit = 'hr.attendance'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}