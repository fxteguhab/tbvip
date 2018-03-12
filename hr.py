
from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _
from lxml import etree

# ==========================================================================================================================

class hr_employee(osv.osv):
	_inherit = 'hr.employee'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_employee_id': fields.integer('MySQL Employee ID'),
		'address': fields.text('Address'),
		'is_spg': fields.boolean('Is SPG?'),
		'employee_no': fields.char('Employee No.'),
		'fingerprint_id': fields.char('Fingerprint ID'),
		'default_modal_cash': fields.float('Default Modal Cash', help='Only needed when the employee is an administrator.'),
		'wallet_owner_saving_id': fields.many2one('wallet.owner', 'Saving Wallet'),
		'wallet_owner_loan_id': fields.many2one('wallet.owner', 'Loan Wallet'),
	}
	
	def create(self, cr, uid, vals, context=None):
		result = super(hr_employee, self).create(cr, uid, vals, context)
		created_employee = self.browse(cr, uid, result, context)
		wallet_owner_obj = self.pool.get('wallet.owner')
		model_data_obj = self.pool.get('ir.model.data')
		# auto create wallet_owner_saving_id with wallet_owner_group_emp_sav as its wallet.owner.group and
		created_employee.wallet_owner_saving_id = wallet_owner_obj.create(cr, uid, {
			'name': "Saving of {}".format(created_employee.name),
			'owner_group_id': model_data_obj.get_object_reference(cr, uid, 'tbvip', 'wallet_owner_group_emp_sav')[1],
		}, context)
		# auto create wallet_owner_loan_id with wallet_owner_group_emp_loan as its wallet.owner.group
		created_employee.wallet_owner_loan_id = wallet_owner_obj.create(cr, uid, {
			'name': "Loan of {}".format(created_employee.name),
			'owner_group_id': model_data_obj.get_object_reference(cr, uid, 'tbvip', 'wallet_owner_group_emp_loan')[1],
		}, context)
		return result
	
	def _auto_create_empty_wallets(self, cr, uid, context):
		wallet_owner_obj = self.pool.get('wallet.owner')
		model_data_obj = self.pool.get('ir.model.data')
		employee_ids = self.search(cr, uid, [
			'|',
			('wallet_owner_saving_id', '=', False),
			('wallet_owner_loan_id', '=', False)
		])
		for employee in self.browse(cr, uid, employee_ids):
			if not employee.wallet_owner_saving_id:
				# auto create wallet_owner_saving_id with wallet_owner_group_emp_sav as its wallet.owner.group and
				employee.wallet_owner_saving_id = wallet_owner_obj.create(cr, uid, {
					'name': "Saving of {}".format(employee.name),
					'owner_group_id': model_data_obj.get_object_reference(cr, uid, 'tbvip', 'wallet_owner_group_emp_sav')[1],
				}, context)
			if not employee.wallet_owner_loan_id:
				# auto create wallet_owner_loan_id with wallet_owner_group_emp_loan as its wallet.owner.group
				employee.wallet_owner_loan_id = wallet_owner_obj.create(cr, uid, {
					'name': "Loan of {}".format(employee.name),
					'owner_group_id': model_data_obj.get_object_reference(cr, uid, 'tbvip', 'wallet_owner_group_emp_loan')[1],
				}, context)

# ==========================================================================================================================

class hr_attendance(osv.osv):
	_inherit = 'hr.attendance'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
	}

	def create(self, cr, uid, vals, context={}):
	# kalau ada absen maka otomatis pindahkan user ke cabang tempat di absen
	# assuming ada data cabangnya ya
		if vals.get('branch_id', False):
			user_obj = self.pool.get('res.users')
			employee_obj = self.pool.get('hr.employee')
			employee_data = employee_obj.browse(cr, uid, vals.get('employee_id'))
			user_obj.write(cr, uid, [employee_data.user_id.id], {
				'branch_id': vals['branch_id']
				})
		return super(hr_attendance, self).create(cr, uid, vals, context=context)

	def save_fingerprint_data(self, cr, uid, branch_id, employee_id, attendance_time, context={}):
	# asumsi: branch id dan employee id dalam fingerprint ID, jadi harus dicari dulu 
	# id Odoo nya
	# ambil odoo id cabang dan pegawai
		branch_obj = self.pool.get('tbvip.branch')
		employee_obj = self.pool.get('hr.employee')
		branch_ids = branch_obj.search(cr, uid, [('fingerprint_id','=',branch_id)])
		if len(branch_ids) == 0:
			raise osv.except_osv(_('Fingerprint Error'),_('ID cabang tidak dikenali.'))
		odoo_branch_id = branch_ids[0]
		employee_ids = employee_obj.search(cr, uid, [('fingerprint_id','=',employee_id)])
		if len(employee_ids) == 0:
			raise osv.except_osv(_('Fingerprint Error'),_('ID pegawai tidak dikenali.'))
		odoo_employee_id = employee_ids[0]
	# konversi waktu menjadi GMT
		try:
			attendance_time = datetime.strptime(attendance_time, DEFAULT_SERVER_DATETIME_FORMAT)
		except:
			raise osv.except_osv(_('Fingerprint Error'),_('Kesalahan format tanggal.'))
		attendance_time = attendance_time - timedelta(hours=7) # sementara difix WIB
		attendance_time = attendance_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
	# tentukan ini sign in atau sign out, sesuai aturan "selang seling"
		prev_att_ids = self.search(cr, uid, [
			('employee_id', '=', odoo_employee_id), ('branch_id','=',odoo_branch_id), 
			('name', '<', attendance_time)], limit=1, order='name DESC')
		if len(prev_att_ids) == 0:
			action = 'sign_in'
		else:
			prev_att_data = self.browse(cr, uid, prev_att_ids[0])
			action = 'sign_in' if prev_att_data.action == 'sign_out' else 'sign_out'
	# insert deh
		return self.create(cr, uid, {
			'branch_id': odoo_branch_id,
			'employee_id': odoo_employee_id,
			'name': attendance_time,
			'action': action,
			})
	
	def fields_view_get(self, cr, uid, view_id=None, view_type='tree', context=None, toolbar=False, submenu=False):
		if context is None:context = {}
		res = super(hr_attendance, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
		group_id_admin = self.pool.get('res.users').has_group(cr, uid, 'tbvip.group_management_administrator')
		group_id_central = self.pool.get('res.users').has_group(cr, uid, 'tbvip.group_management_central')
		doc = etree.XML(res['arch'])
		if not group_id_admin and not group_id_central:
			nodes_tree = doc.xpath("//tree[@string='Employee attendances']")
			nodes_form = doc.xpath("//form[@string='Employee attendances']")
			for node in nodes_tree:
				node.set('create', '0')
			for node in nodes_form:
				node.set('create', '0')
			res['arch'] = etree.tostring(doc)
		
		return res

# ==========================================================================================================================

class hr_payslip(osv.osv):
	_inherit = 'hr.payslip'
	
	_columns = {
		'current_saving': fields.float('Current Saving', help="Saving of this employee in the moment this payslip is generated"),
		'current_loan': fields.float('Current Loan', help="Loan of this employee in the moment this payslip is generated"),
		'loan_action': fields.selection([('inc', 'Pinjam'), ('dec', 'Bayar')], 'Loan Action'),
		'loan_amount': fields.float('Loan Amount'),
		'saving_action': fields.selection([('inc', 'Simpan'), ('dec', 'Ambil')], 'Saving Action'),
		'saving_amount': fields.float('Saving Amount'),
	}
	
	def print_payslip_dot_matrix(self, cr, uid, ids, context):
		return {
			'type' : 'ir.actions.act_url',
			'url': '/tbvip/print/hr.payslip/' + str(ids[0]),
			'target': 'self',
		}

	def compute_sheet(self, cr, uid, ids, context=None):
		result = super(hr_payslip, self).compute_sheet(cr, uid, ids, context=context)
	# simpan current balance saving dan loan pada saat payslip di-compute
		for payslip in self.browse(cr, uid, ids, context=context):
			saving_wallet = payslip.employee_id.wallet_owner_saving_id
			loan_wallet = payslip.employee_id.wallet_owner_loan_id
			self.write(cr, uid, [payslip.id], {
				'current_saving': saving_wallet and saving_wallet.balance_amount or 0,
				'current_loan': loan_wallet and loan_wallet.balance_amount or 0,
				})
		return result

	
	def hr_verify_sheet(self, cr, uid, ids, context=None):
		"""
		Calculate loan and saving
		"""
		wallet_trx_obj = self.pool.get('wallet.transaction')
		result = super(hr_payslip, self).hr_verify_sheet(cr, uid, ids, context)
		for payslip in self.browse(cr, uid, ids, context):
			mnemonic_saving = False
			mnemonic_loan = False
			if payslip.saving_action == 'inc':
				mnemonic_saving = 'SAVING_INC'
			elif payslip.saving_action == 'dec':
				mnemonic_saving = 'SAVING_DEC'
			if payslip.loan_action == 'inc':
				mnemonic_loan = 'LOAN_INC'
			elif payslip.loan_action == 'dec':
				mnemonic_loan = 'LOAN_DEC'
			if mnemonic_saving:
				wallet_trx_obj.post_transaction(cr, uid, payslip.number, mnemonic_saving, payslip.saving_amount,
					owner_id=payslip.employee_id.wallet_owner_saving_id.id)
			if mnemonic_loan:
				wallet_trx_obj.post_transaction(cr, uid, payslip.number, mnemonic_loan, payslip.loan_amount,
					owner_id=payslip.employee_id.wallet_owner_loan_id.id)
		return result
