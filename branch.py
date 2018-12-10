from openerp.osv import osv, fields
from openerp.tools.translate import _

# ==========================================================================================================================
class tbvip_branch(osv.osv):
	_name = 'tbvip.branch'
	_description = 'Store branches'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'name': fields.char('Branch Name', required=True),
		'default_incoming_location_id': fields.many2one('stock.location', 'Default Incoming Location'),
		'default_outgoing_location_id': fields.many2one('stock.location', 'Default Outgoing Location'),
		'default_stock_location_id': fields.many2one('stock.location', 'Default Stock Location'),
		'default_account_cash' : fields.many2one('account.account', 'Default Cash Vault Account'),
		'default_account_bank' : fields.many2one('account.account', 'Default Bank Vault Account'), 
		'default_journal_sales_bank' : fields.many2one('account.journal', 'Default Sale non-Cash Journal '),
		'address': fields.text('Address', required=True),
		'default_open_hour': fields.float('Default Open Hour'),
		'default_closed_hour': fields.float('Default Closed Hour'),
		'fingerprint_id': fields.char('Fingerprint ID'),
		'employee_list': fields.one2many('tbvip.branch.employee', 'branch_id', 'Employee List'),
	}


# ==========================================================================================================================
class tbvip_branch_employee(osv.osv):
	_name = 'tbvip.branch.employee'
	_description = 'Store branches Employee'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'name': fields.char('Reference', required = True),
		'user_id': fields.many2one('res.users', 'Employee'),
		'default_modal_cash': fields.float('Capital'),
		'default_account_cash' : fields.many2one('account.account', 'Sale Cash Account'),
		#'default_journal_purchase_override': fields.many2one('account.journal', 'Purchase Cash Journal'),
		'default_journal_sales_override': fields.many2one('account.journal', 'Sale Cash Journal'),
		'default_journal_sales_retur_override': fields.many2one('account.journal', 'Sale Retur Cash Journal'),
	}

	def create(self, cr, uid, vals, context=None):
		user_id = vals['user_id']
		branch_id = vals['branch_id']
		
		if (user_id):
			#2 nama sama di branch sama
			#if (self.search(cr, uid, [('user_id', '=', user_id),('branch_id','=',branch_id)], limit=1, context=context)):
			#	raise osv.except_osv(_('Warning!'), _("This employee already in that branch"))
			
			#hapus data employee di branch lain
			employee_id = self.search(cr, uid, [('user_id', '=', user_id),('branch_id','!=',branch_id)], limit=1, context=context)
			if (employee_id):
				self.write(cr, uid, employee_id, {'user_id': False,})

			#ubah branch_id do res_users
			user_obj = self.pool.get('res.users')
			user_obj.write(cr, uid, user_id, {
				'branch_id': branch_id,
			})

		return super(tbvip_branch_employee, self).create(cr, uid, vals, context)

	def write(self, cr, uid, ids, vals, context=None):

		for employee_list in self.browse(cr, uid, ids):
			user_id = employee_list.user_id.id
			old_user_id = user_id
			branch_id = employee_list.branch_id.id

		if vals.get('user_id', False): user_id = vals['user_id']
		if vals.get('branch_id', False): branch_id = vals['branch_id']

		#hapus branch di old_user
		if (old_user_id):
			#hapus branch id res_user yg lama
			user_obj = self.pool.get('res.users')
			user_obj.write(cr, uid, old_user_id, {
				'branch_id': False,
			})
			
		if (user_id):
			#2 nama sama di branch sama
			#if (self.search(cr, uid, [('user_id', '=', user_id),('branch_id','=',branch_id)], limit=1, context=context)):
			#	raise osv.except_osv(_('Warning!'), _("This employee already in that branch"))

			#hapus data employee di branch lain
			employee_id = self.search(cr, uid, [('user_id', '=', user_id),('branch_id','!=',branch_id)], limit=1, context=context)
			if (employee_id):
				self.write(cr, uid, employee_id, {'user_id': False,})

			#ubah branch id res_user
			user_obj = self.pool.get('res.users')
			user_obj.write(cr, uid, user_id, {
				'branch_id': branch_id,
			})

		
		return super(tbvip_branch_employee, self).write(cr, uid, ids, vals, context)
# ==========================================================================================================================