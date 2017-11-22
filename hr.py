import os
from mako.lookup import TemplateLookup
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
		'default_modal_cash': fields.float('Default Modal Cash', help='Only needed when the employee is an administrator.')
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


class hr_payslip(osv.osv):
	_inherit = 'hr.payslip'
	
	def print_payslip_dot_matrix(self, cr, uid, ids, context):
		# Mendefinisikan path dari modul report terkait
		tpl_lookup = TemplateLookup(directories=['openerp/addons/tbvip/print_template'])
		
		# Mendefinikan template report berdasarkan path modul terkait
		template = tpl_lookup.get_template('payslip.txt')
		
		for payslip in self.browse(cr, uid, ids, context=context):
			# Prepare worked days data
			worked_days = {'masuk': 0, 'full': 0, 'full_minggu': 0}
			for worked_day in payslip.worked_days_line_ids:
				if worked_day.code == 'MASUK':
					worked_days['masuk'] = worked_day.number_of_days
				elif worked_day.code == 'FULL':
					worked_days['full'] = worked_day.number_of_days
				elif worked_day.code == 'FULL_MINGGU':
					worked_days['full_minggu'] = worked_day.number_of_days
			
			bonus = {}
			for input_line in payslip.input_line_ids:
				bonus.update({input_line.code: input_line.amount})
			
			line = {}
			for payslip_line in payslip.line_ids:
				line.update({payslip_line.code: payslip_line.total})
			
			total_bonus_point = bonus.get('POIN_XTRA_POINT', 0) \
					+ bonus.get('POIN_PENALTY_POINT', 0) \
					+ bonus.get('POIN_TOP_POINT', 0) \
					+ bonus.get('POIN_MOBIL_POINT', 0) \
					+ bonus.get('POIN_MOTOR_POINT', 0) \
					+ bonus.get('POIN_SO_POINT', 0) \
					+ bonus.get('POIN_SALES_POINT', 0) \
					+ bonus.get('POIN_ADM_POINT', 0)
			
			total_bonus_value = bonus.get('POIN_XTRA_BONUS', 0) \
					+ bonus.get('POIN_PENALTY_BONUS', 0) \
					+ bonus.get('POIN_TOP_BONUS', 0) \
					+ bonus.get('POIN_MOBIL_BONUS', 0) \
					+ bonus.get('POIN_MOTOR_BONUS', 0) \
					+ bonus.get('POIN_SO_BONUS', 0) \
					+ bonus.get('POIN_SALES_BONUS', 0) \
					+ bonus.get('POIN_ADM_BONUS', 0)
			
			payslip_print = template.render(
				print_date=str(datetime.now()),
				from_date=str(payslip.date_from),
				name=str(payslip.employee_id.name),
				masuk=str(worked_days.get('masuk', 0)),
				pokok=str(bonus.get('MASUK_BONUS_BASIC', 0)),
				full=str(worked_days.get('full', 0)),
				makan=str(bonus.get('FULL_BONUS_BASIC', 0)),
				full_minggu=str(worked_days.get('full_minggu', 0)),
				mingguan=str(bonus.get('FULL_MINGGU_BONUS_BASIC', 0)),
				total_pokok=str(line.get('BASIC', 0)),
				
				to_date=str(payslip.date_to),
				
				total_minggu=str(total_bonus_value + line.get('BASIC', 0)),
				
				potongan=str(0),
				
				point_mobil=str(bonus.get('POIN_MOBIL_POINT', 0)),
				lvl_mobil=str(bonus.get('POIN_MOBIL_LEVEL', 0)),
				bonus_mobil=str(bonus.get('POIN_MOBIL_BONUS', 0)),
				nabung=str(0),
				
				point_motor=str(bonus.get('POIN_MOTOR_POINT', 0)),
				lvl_motor=str(bonus.get('POIN_MOTOR_LEVEL', 0)),
				bonus_motor=str(bonus.get('POIN_MOTOR_BONUS', 0)),
				
				point_so=str(bonus.get('POIN_SO_POINT', 0)),
				lvl_so=str(bonus.get('POIN_SO_LEVEL', 0)),
				bonus_so=str(bonus.get('POIN_SO_BONUS', 0)),
				gaji=str(line.get('NET', 0)),
				
				point_sales=str(bonus.get('POIN_SALES_POINT', 0)),
				lvl_sales=str(bonus.get('POIN_SALES_LEVEL', 0)),
				bonus_sales=str(bonus.get('POIN_SALES_BONUS', 0)),
				
				point_adm=str(bonus.get('POIN_ADM_POINT', 0)),
				lvl_adm=str(bonus.get('POIN_ADM_LEVEL', 0)),
				bonus_adm=str(bonus.get('POIN_ADM_BONUS', 0)),
				tabungan=str(0),
								
				point_xtra=str(bonus.get('POIN_XTRA_POINT', 0)),
				lvl_xtra=str(bonus.get('POIN_XTRA_LEVEL', 0)),
				bonus_xtra=str(bonus.get('POIN_XTRA_BONUS', 0)),
				pinjaman=str(0),
				
				point_penalti=str(bonus.get('POIN_PENALTY_POINT', 0)),
				lvl_penalti=str(bonus.get('POIN_PENALTY_LEVEL', 0)),
				bonus_penalti=str(bonus.get('POIN_PENALTY_BONUS', 0)),
				level=str(bonus.get('CURRENT_LEVEL_BASIC', 0)),
				
				point_top=str(bonus.get('POIN_TOP_POINT', 0)),
				lvl_top=str(bonus.get('POIN_TOP_LEVEL', 0)),
				bonus_top=str(bonus.get('POIN_TOP_BONUS', 0)),
				total_poin=str(bonus.get('TOTAL_POINT_BASIC', 0)),
				
				total_bonus_point=str(total_bonus_point),
				total_bonus_value=str(total_bonus_value),
				target_poin=str(bonus.get('NEXT_LEVEL_POINT_BASIC', 0)),
			)
			
			# Create temporary file
			path_file = 'openerp/addons/tbvip/tmp/'
			filename = path_file + 'print_payslip ' + datetime.now().strftime('%Y-%m-%d %H%M%S') + '.txt'
			# Put rendered string to file
			f = open(filename, 'w')
			f.write(payslip_print.replace("\r\n", "\n"))
			f.close()
			# Process printing
			os.system('lpr -Pnama_printer %s' % filename)
			# Remove printed file
			# os.remove(filename) #TODO UNCOMMENT
			return True
