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
		tpl_lookup = TemplateLookup(directories=['E:/Workstation/Odoo Addons/v8/Christian Juniady and Associates/tbvip/print_template']) # 'openerp/addons/tbvip/print_template

		# Mendefinikan template report berdasarkan path modul terkait
		template = tpl_lookup.get_template('payslip.txt')
		
		for payslip in self.browse(cr, uid, ids, context=context):
			payslip_print = template.render(
				print_date=str(datetime.now()),
				from_date=str(payslip.date_from),
				name=str(payslip.employee_id.name),
				masuk=str(123),
				pokok=str(123),
				full=str(123),
				makan=str(123),
				full_minggu=str(123),
				mingguan=str(123),
				total_pokok=str(123),
				
				to_date=str(payslip.date_to),
				
				total_minggu=str(123),
				
				potongan=str(123),
				
				point_mobil=str(123),
				lvl_mobil=str(123),
				bonus_mobil=str(123),
				nabung=str(123),
				
				point_motor=str(123),
				lvl_motor=str(123),
				bonus_motor=str(123),
				
				point_so=str(123),
				lvl_so=str(123),
				bonus_so=str(123),
				gaji=str(123),
				
				point_sales=str(123),
				lvl_sales=str(123),
				bonus_sales=str(123),
				
				point_adm=str(123),
				lvl_adm=str(123),
				bonus_adm=str(123),
				tabungan=str(123),
								
				point_xtra=str(123),
				lvl_xtra=str(123),
				bonus_xtra=str(123),
				pinjaman=str(123),
				
				point_penalti=str(123),
				lvl_penalti=str(123),
				bonus_penalti=str(123),
				level=str(123),
				
				point_top=str(123),
				lvl_top=str(123),
				bonus_top=str(123),
				total_poin=str(123),
				
				total_bonus_point=str(123),
				total_bonus_value=str(123),
				target_poin=str(123),
			)
			
			# Create temporary file
			path_file = 'D:/' # 'openerp/addons/tbvip/tmp/'
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
