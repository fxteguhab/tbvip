from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _

# ==========================================================================================================================

class hr_employee(osv.osv):
	_inherit = 'hr.employee'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'mysql_employee_id': fields.integer('MySQL Employee ID'),
		'address': fields.text('Address'),
		'type': fields.selection([('is_spg', "SPG"), ('is_non_spg', "Non-SPG")], 'Type'),
		'employee_no': fields.char('Employee No.'),
		'fingerprint_id': fields.char('Fingerprint ID'),
	}

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
