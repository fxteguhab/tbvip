import calendar
import csv
import os
from datetime import datetime, date, timedelta

from dateutil.relativedelta import relativedelta
from openerp.models import BaseModel
from openerp.osv import osv, fields


# ==========================================================================================================================

class tbvip_branch(osv.osv):
	_name = 'tbvip.branch'
	_description = 'Store branches'
	
# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'name': fields.char('Branch Name', required=True),
	}


# ==========================================================================================================================

class tbvip_mysql_bridge(osv.osv):
	_name = 'tbvip.mysql.bridge'
	_auto = False
	
	_conn = None
	_cursor = None
	
	def mysql_connect(self):
		self._conn = mysql.connector.connect(user='tbvip', password='hegemoni', database='invent_db',
			host='invent-db.c0rnoufuieno.ap-southeast-1.rds.amazonaws.com')
		self._cursor = self._conn.cursor(dictionary=True)
		return self._cursor
	
	def mysql_close(self):
		self._cursor.close()
		self._conn.close()
	
	def get_old_new_id_map(self, cr, uid, model_name, old_column_name):
		model_obj = self.pool.get(model_name)
		model_ids = model_obj.search(cr, uid, [], context={'active_test': False})
		model_map_old_ids = []
		model_map_ids = []
		for row in model_obj.browse(cr, uid, model_ids):
			eval("model_map_old_ids.append(row.%s)" % old_column_name)
			model_map_ids.append(row.id)
		return model_map_old_ids, model_map_ids
	
	def get_id_from_old_new_map(self, map_old_ids, map_ids, old_key_value):
		try:
			idx = map_old_ids.index(old_key_value)
			return map_ids[idx]
		except ValueError:
			return None
	
	def update_insert(self, cr, uid, model_name, old_key_value, map_old_ids, map_ids, data, context={}):
		if not context: context = {}
		model_obj = self.pool.get(model_name)
		# coba cari codex_id di data yang sudah ada
		try:
			# kalau ketemu, berarti write
			idx = map_old_ids.index(old_key_value)
			model_obj.write(cr, uid, [map_ids[idx]], data, context=context)
			return map_ids[idx]
		except ValueError:
			if context.get('create_defaults'):  # create_defaults berisi field-field default untuk create, bila perlu
				data.update(context.get('create_defaults'))
			# kalau ngga ketemu, bikin baru deh
			return model_obj.create(cr, uid, data)


# ==========================================================================================================================

class tbvip_data_synchronizer(osv.osv):
	_name = 'tbvip.data.synchronizer'
	_description = 'Data synchronizer between AWS database and Odoo'
	_auto = False
	
# CRON --------------------------------------------------------------------------------------------------------------------------
	
	def cron_sync_category_product(self, cr, uid, context=None):
		
		mysql_bridge_obj = self.pool.get('tbvip.mysql.bridge')
		
		category_map_codex_ids, category_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'product.category',
			'codex_id')
		product_map_codex_ids, product_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'product.template', 'codex_id')
		
		def perform_product_data_conversion(product):
			categ_id = mysql_bridge_obj.get_id_from_old_new_map(category_map_codex_ids, category_map_ids,
				product['group_id'])
			result = {
				'name': product['name'],
				'codex_id': product['item_id'],
			}
			datatype = ""
			is_variant = (
			product['type'] == 'g' and (product['name'].find('VARIANT') != -1 or product['name'].find('VARIAN') != -1))
			if product['type'] == 'i' or is_variant:
				datatype = 'product'
				result.update({
					'categ_id': categ_id,
					# 'active': True, DO NOT UNCOMMENT! It took me three days in five dates to add that one # at this line. What a persistent and stubborn bug!
					# dll seperti harga, dsb
				})
			else:
				datatype = 'category'
				result.update({
					'parent_id': categ_id,
					'type': 'normal',
				})
			return datatype, is_variant, result
		
		print '%s start cron sync category product' % datetime.now()
		
# SYNC CATEGORY -----------------------------------------------------------------------------------------------------------
		
	# ambil dulu codex2 id category sekarang, untuk menunjukkan id apa saja yang sudah pernah di-sync sebelumnya
		category_obj = self.pool.get('product.category')
		product_template_obj = self.pool.get('product.template')
		
		active_product_codex_ids = []
		nonactive_product_codex_ids = []
	# ambil datanya
		print '%s querying database' % datetime.now()
		cursor = mysql_bridge_obj.mysql_connect()
		cursor.execute("SELECT name, group_id, type, item_id, non_active FROM t_item_codex")
		print '%s start taking care of categories' % datetime.now()
	# untuk category Saleable
		model_obj = self.pool.get('ir.model.data')
		model, categ_saleable_id = model_obj.get_object_reference(cr, uid, 'product', 'product_category_1')
	# inisialisasi
		product_buffer = []
		fails = []
	# masukin category, sekalian ambil product dan taruh di product_buffer
	# kenapa gini? soalnya category harus udah semuanya ada baru product bisa masuk
		for product in cursor.fetchall():
			datatype, is_variant, data = perform_product_data_conversion(product)
			if datatype == 'category':
			# khusus group dengan parent 0, masukkan langsung ke All/ Saleable
				if product['group_id'] == 0:
					data.update({
						'parent_id': categ_saleable_id
					})
				print "Category: %s" % data
				mysql_bridge_obj.update_insert(cr, uid, 'product.category', product['item_id'], category_map_codex_ids,
					category_map_ids, data)
			elif datatype == 'product':
				product_buffer.append({
					'is_variant': is_variant,
					'group_id': product['group_id'],
					'data': data,
				})
			# apakah di aaktif atau tidak
				if product['non_active'] == 0:
					active_product_codex_ids.append(product['item_id'])
				else:
					nonactive_product_codex_ids.append(product['item_id'])
				
# SYNC KEPALA PRODUCT VARIANT ---------------------------------------------------------------------------------------------
				
	# pengambilan mapping juga diulang karena di atas sudah ada perubahan karena write (misal pindah kategori)
	# atau create (ada category baru)
		print '%s start taking care of variants' % datetime.now()
		variant_codex_ids = []
		category_map_codex_ids, category_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'product.category',
			'codex_id')
		for product in product_buffer:
			is_variant = product['is_variant']
			group_id = product['group_id']
			data = product['data']
			if not is_variant: continue
			categ_id = mysql_bridge_obj.get_id_from_old_new_map(category_map_codex_ids, category_map_ids, group_id)
			if categ_id:
				variant_codex_ids.append(data['codex_id'])
				data.update({
					'categ_id': categ_id,
					'type': 'product',
				})
				print "Variant: %s" % data
				mysql_bridge_obj.update_insert(cr, uid, 'product.template', data['codex_id'], product_map_codex_ids,
					product_map_ids, data, context=context)
			else:
				fails.append("Variant %s (%s) missing group_id %s" % (data['name'], data['codex_id'], group_id))
			
# SYNC PRODUCT NON-ANAK VARIANT -------------------------------------------------------------------------------------------
		
		print '%s start taking care of products' % datetime.now()
		for product in product_buffer:
			group_id = product['group_id']
			data = product['data']
			if group_id in variant_codex_ids or data['codex_id'] in variant_codex_ids: continue
			categ_id = mysql_bridge_obj.get_id_from_old_new_map(category_map_codex_ids, category_map_ids, group_id)
			if categ_id:
				data.update({
					'categ_id': categ_id,
					'type': 'product',
				})
				print "Product: %s" % data
				mysql_bridge_obj.update_insert(cr, uid, 'product.template', data['codex_id'], product_map_codex_ids,
					product_map_ids, data, context=context)
			else:
				fails.append("Product %s (%s) missing group_id %s" % (data['name'], data['codex_id'], group_id))
		
		print '%s start taking care of anak variants' % datetime.now()
		
# UPDATE ATRIBUT+VALUE VARIANT BESERTA PRODUK ANAK VARIANT ----------------------------------------------------------------
		
	# ambil dari file anak_variant, produk2 variant beserta atribut2 dan value2 variantnya
		try:
			sep = os.sep
			temp = os.path.abspath(os.path.dirname(__file__)).split(sep)
			basepath = ''
			for slicer in temp[:-1]:
				basepath = basepath + slicer + sep
			fullpath = basepath + '/tbvip/static/anak_variant.csv'
			fullpath = fullpath.replace('/', sep)
			f = open(fullpath, 'rb')
		except:
			raise osv.except_osv("Sync Error", "Source variant file not found.")
		try:
			variant_lines = []
			reader = csv.reader(f)
			for row in reader:
				if row[0] == 'item_id': continue
				variant_lines.append(row)
		except:
			f.close()
			raise osv.except_osv("Sync Error", "Unable to open source variant.")
		finally:
			f.close()
	# bikin variant yang belum ada
		attribute_obj = self.pool.get('product.attribute')
		attributes = {}
		product_group_attributes = {}
		for variant in variant_lines:
			variant1 = variant[4]
			variant2 = variant[6]
			variant_value1 = variant[3]
			variant_value2 = variant[5]
			parent_variant_id = variant[1]
		# urus master atribut beserta kemungkinan value nya
			if variant1 not in attributes: attributes.update({variant1: {'name': variant1, 'value_ids': []}})
			attributes[variant1]['value_ids'].append(variant_value1)
		# pasangkan antara item_id parent variant dengan atribut dan kemungkinan value nya
			if not product_group_attributes.get(parent_variant_id, False):
				product_group_attributes.update({parent_variant_id: {}})
			if not product_group_attributes[parent_variant_id].get(variant1, False):
				product_group_attributes[parent_variant_id].update({variant1: []})
			product_group_attributes[parent_variant_id][variant1].append(variant_value1)
			if not variant2: continue
			if variant2 not in attributes: attributes.update({variant2: {'name': variant2, 'value_ids': []}})
			attributes[variant2]['value_ids'].append(variant_value2)
		# pasangkan antara item_id parent variant dengan atribut variant2 dan kemungkinan valuenya
			if not product_group_attributes[parent_variant_id].get(variant2, False):
				product_group_attributes[parent_variant_id].update({variant2: []})
			product_group_attributes[parent_variant_id][variant2].append(variant_value2)
		for variant in attributes:
			attributes[variant]['value_ids'] = list(set(attributes[variant]['value_ids']))
		for parent_variant_id in product_group_attributes:
			for variant in product_group_attributes[parent_variant_id]:
				product_group_attributes[parent_variant_id][variant] = list(
					set(product_group_attributes[parent_variant_id][variant]))
	# ambil yang udah ada
		existing = []
		attribute_ids = attribute_obj.search(cr, uid, [])
		for row in attribute_obj.browse(cr, uid, attribute_ids):
			existing.append(row.name)
	# untuk yang belum ada
		for key in attributes:
			variant_data = attributes[key]
			if variant_data['name'] in existing: continue
		# create atribut beserta attribute values nya
			value_ids = sorted(variant_data['value_ids'])
			sequence = 1
			values = []
			for value in value_ids:
				values.append([0, False, {
					'sequence': sequence,
					'name': value,
				}])
				sequence += 1
			attribute_obj.create(cr, uid, {
				'name': variant_data['name'],
				'value_ids': values
			})
	# ambil semua atribut, buatlah dictionary pasangan nama atribut - id, beserta pasangan value - id anak2nya
		attribute_ids = attribute_obj.search(cr, uid, [])
		attribute_dict = {}
		for attribute in attribute_obj.browse(cr, uid, attribute_ids):
			if attribute.name not in attribute_dict: attribute_dict.update(
				{attribute.name: {'id': attribute.id, 'values': {}}})
			for value in attribute.value_ids:
				attribute_dict[attribute.name]['values'].update({value.name: value.id})
			
	# update parent variant dengan menambahkan atribut beserta kemungkinan valuenya
		parent_product_item_ids = product_group_attributes.keys()
		product_ids = product_template_obj.search(cr, uid, [('codex_id', 'in', parent_product_item_ids)])
		dummy = []
		for product in product_template_obj.browse(cr, uid, product_ids):
			if product.id in dummy: continue
			print product.name, product.attribute_line_ids
			if len(product.attribute_line_ids) > 0: continue  # hanya update variant yang belum ada saja
			if product.id not in dummy: dummy.append(product.id)
			variant_data = product_group_attributes[str(product.codex_id)]
			attribute_line_ids = []
			for variant_name in variant_data:
				value_ids = []
				for value in variant_data[variant_name]:
					value_ids.append(attribute_dict[variant_name]['values'][value])
				attribute_line_ids.append([0, False, {
					'attribute_id': attribute_dict[variant_name]['id'],
					'value_ids': [[6, False, value_ids]]
				}])
			print "sampe ke mau write product %s" % product.name
			product_template_obj.write(cr, uid, [product.id], {
				'attribute_line_ids': attribute_line_ids
			})
		
		print '%s handle active/nonactive' % datetime.now()
		
	# update aktif/non-aktif product
		for codex_id in active_product_codex_ids:
			cr.execute("UPDATE product_template SET active=True WHERE codex_id='%s'" % codex_id)
			cr.execute("UPDATE product_product SET active=True WHERE variant_codex_id='%s'" % codex_id)
		for codex_id in nonactive_product_codex_ids:
			cr.execute("UPDATE product_template SET active=False WHERE codex_id='%s'" % codex_id)
			cr.execute("UPDATE product_product SET active=False WHERE variant_codex_id='%s'" % codex_id)
		
		print '%s finished' % datetime.now()
	
# SUPPLIER -----------------------------------------------------------------------------------------------------------------
	
	def cron_sync_supplier(self, cr, uid, context={}):
		
		mysql_bridge_obj = self.pool.get('tbvip.mysql.bridge')
		partner_map_codex_ids, partner_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'res.partner',
			'mysql_partner_id')
		
		def perform_supplier_data_conversion(partner):
			return {
				'is_company': True,
				'supplier': True,
				'customer': False,
				'mysql_partner_id': partner['supplier_id'],
				'name': partner['name'],
				'street': partner['address'],
				'phone': partner['phone'],
				'fax': partner['fax'],
				'website': partner['website'],
				'email': partner['email'],
				'ref': "%s%s" % (partner['cp'], (partner['cp_phone'] and (" / " + partner['cp_phone']) or "")),
				'comment': partner['description'],
			}
		
	# ambil datanya
		cursor = mysql_bridge_obj.mysql_connect()
		cursor.execute("SELECT * FROM t_supplier")
		
	# insert/update supplier
		for supplier in cursor.fetchall():
			data = perform_supplier_data_conversion(supplier)
			mysql_bridge_obj.update_insert(cr, uid, 'res.partner', data['mysql_partner_id'], partner_map_codex_ids,
				partner_map_ids, data)
		
# EMPLOYEE -----------------------------------------------------------------------------------------------------------------
	
	def cron_sync_employee(self, cr, uid, context={}):
		
		mysql_bridge_obj = self.pool.get('tbvip.mysql.bridge')
		employee_map_codex_ids, employee_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'hr.employee',
			'mysql_employee_id')
		
		def perform_employee_data_conversion(employee):
			return {
				'mysql_employee_id': employee['employee_id'],
				'name': employee['name'],
				'address': employee['address'],
				'mobile_phone': employee['telp'],
				'birthday': employee['dob'] == '0000-00-00' and None or employee['dob'],
				'notes': employee['description'],
			}
		
	# ambil datanya
		cursor = mysql_bridge_obj.mysql_connect()
		cursor.execute("SELECT * FROM t_employee")
		
	# insert/update employee
		for employee in cursor.fetchall():
			data = perform_employee_data_conversion(employee)
			mysql_bridge_obj.update_insert(cr, uid, 'hr.employee', data['mysql_employee_id'], employee_map_codex_ids,
				employee_map_ids, data)
		
		print "selesai sync employee"
	
# PURCHASE ORDER DAN SUPPLIER INVOICE --------------------------------------------------------------------------------------
	
	def cron_sync_purchase(self, cr, uid, context={}):
		
		mysql_bridge_obj = self.pool.get('tbvip.mysql.bridge')
		
		employee_map_codex_ids, employee_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'hr.employee',
			'mysql_employee_id')
		product_map_codex_ids, product_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'product.product',
			'variant_codex_id')
		partner_map_codex_ids, partner_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'res.partner',
			'mysql_partner_id')
		
		vehicle_obj = self.pool.get('fleet.vehicle')
		vehicle_ids = vehicle_obj.search(cr, uid, [])
		vehicle_map = {}
		for vehicle in vehicle_obj.browse(cr, uid, vehicle_ids):
			vehicle_map.update({vehicle.license_plate: vehicle.id})
		
	# ambil term 30 hari
		model_obj = self.pool.get('ir.model.data')
		model, payment_30_id = model_obj.get_object_reference(cr, uid, 'account', 'account_payment_term_net')
	# ambil id buat cabang 22 dan cabang 49
		model, branch_22_id = model_obj.get_object_reference(cr, uid, 'tbvip', 'tbvip_branch_22')
		model, branch_49_id = model_obj.get_object_reference(cr, uid, 'tbvip', 'tbvip_branch_49')
	# ambil default stock location WH/Stock
		model, wh_stock_id = model_obj.get_object_reference(cr, uid, 'stock', 'stock_location_stock')
		
	# ambil semua pricelist_id setiap supplier. ini dibutuhkan ketika create PO
		pricelist_ids = {}
		partner_obj = self.pool.get('res.partner')
		partner_ids = partner_obj.search(cr, uid, [('supplier', '=', True)])
		for partner in partner_obj.browse(cr, uid, partner_ids):
			pricelist_ids.update({partner.id: partner.property_product_pricelist_purchase.id})
		
		def perform_purchase_data_conversion(purchase):
			partner_id = mysql_bridge_obj.get_id_from_old_new_map(partner_map_codex_ids, partner_map_ids,
				purchase['supplier_id'])
			driver_id = mysql_bridge_obj.get_id_from_old_new_map(employee_map_codex_ids, employee_map_ids,
				purchase['driver'])
			try:
				discount = float(purchase['disc'])
			except ValueError:
				discount = 0
			date_order = (purchase['input_date'] == '0000-00-00' or not purchase['input_date']) and purchase[
				'invoice_date'] or purchase['input_date']
			result = {
				'mysql_purchase_id': purchase['mysql_purchase_id'],
				'location_id': wh_stock_id,
				'partner_ref': purchase['invoice'],
				'partner_id': partner_id and partner_id or None,
				'pricelist_id': pricelist_ids.get(partner_id, None),
				'date_order': date_order,
				'payment_term_id': payment_30_id,
				'cashier': purchase['cashier'],
				'general_discount': discount,
				'notes': purchase['keterangan'],
				'adm_point': purchase['poin'],
				'pickup_vehicle_id': vehicle_map.get(purchase['mobil'], None),  # mapping ke vehicle map
				'driver_id': driver_id and driver_id or None,
				'order_line': [],
			}
			order_lines = []
			for line in purchase['purchase_lines']:
				product_id = mysql_bridge_obj.get_id_from_old_new_map(product_map_codex_ids, product_map_ids,
					line['item_id'])
				try:
					discount1 = float(line['disc'])
					if discount1 > 0:
						discount_mode = 'amount'
					else:
						discount_mode = None
				except ValueError:
					discount1 = line['cost'] - line['nett']
					discount_mode = line['disc']
				order_lines.append([0, False, {
					'mysql_purchase_det_id': line['mysql_purchase_det_id'],
					'name': '-',
					'date_planned': date_order,
					'product_id': product_id,
					'product_qty': line['qty'],
					'price_unit': line['cost'],
					'discount_mode': discount_mode,
					'disc1': discount1,
					'alert': line['alert']
				}])
			result['order_line'] = order_lines
			return result
		
		print "start syncing purchases: %s" % datetime.now()
		
	# ambil semua mysql_id yang sudah ada di odoo. hal ini untuk mencegah purchase data yang sama diimport > 1 kali
	# asumsikan bahwa data yang ada di AWS sudah fixed alias ngga diedit2 lagi
		existing_ids = []
		cr.execute("SELECT mysql_purchase_id FROM purchase_order")
		for row in cr.dictfetchall():
			if row['mysql_purchase_id'] == 0: continue
			existing_ids.append(str(row['mysql_purchase_id']))
		
	# ambil datanya
	# tabel sumber ada dua di mysql nya, jadi di sini kita ambil gabungan dulu
		purchase_data = []
		existing_join = ",".join(existing_ids)
		from_date = '2014-01-01'
		cursor = mysql_bridge_obj.mysql_connect()
		cursor.execute("""
			SELECT * 
			FROM t_detail_purchase22 det, t_master_purchase22 mst 
			WHERE 
				det.purchase_id = mst.purchase_id AND 
				mst.invoice_date >= '%s' %s
			ORDER BY invoice_date DESC
		""" % (from_date, (existing_ids and 'AND mst.purchase_id NOT IN (%s)' % existing_join or "")))
		for row in cursor.fetchall():
			row.update({'branch_id': branch_22_id})
			purchase_data.append(row)
		
	# convert data sehingga satu purchase punya satu baris data saja, dengan di dalamnya ada purchase detail
		purchase_data_convert = {}
		master_keys = ['invoice', 'branch_id', 'supplier_id', 'input_date', 'invoice_date', 'validity', 'invoice', 'cashier',
			'payment', 'pay_id', 'disc', 'total', 'keterangan', 'alert', 'lunas', 'sisa_total', 'poin', 'mobil', 'driver']
		detail_keys = ['item_id', 'qty', 'cost', 'disc', 'nett', 'total', 'minute', 'alert']
		for row in purchase_data:
			key = int(row['purchase_id'])
			if not purchase_data_convert.get(key, False):
				purchase_data_convert.update({key: {
					'mysql_purchase_id': key,
					'purchase_lines': []
				}})
				for master in master_keys:
					purchase_data_convert[key].update({master: row[master]})
			detail_data = {
				'mysql_purchase_det_id': int(row['d_purchase_id']),
			}
			for detail in detail_keys:
				detail_data.update({detail: row[detail]})
			purchase_data_convert[key]['purchase_lines'].append(detail_data)
		
	# convert menjadi data yang siap diinsert ke odoo
		purchase_obj = self.pool.get('purchase.order')
		i = 1
		total = len(purchase_data_convert.keys())
		for purchase in purchase_data_convert:
			print "%s of %s" % (i, total)
			data = perform_purchase_data_conversion(purchase_data_convert[purchase])
			purchase_obj.create(cr, uid, data, context={
				'direct_confirm': True,
				'direct_receive': True,
			})
			i += 1
		
	# ambil kontra bon yang sudah ada
		
		print "selesai sync purchase: %s" % datetime.now()


class tbvip_website_handler(osv.osv):
	_name = 'tbvip.website.handler'
	_description = 'Model for handling website-based requests'
	_auto = False
	
	def load_kontra_bon(self, domain, context={}):
	# TIMTBVIP: DONE
	# untuk filter draft masih salah, dalam artian kalaupun ada untuk supplier tertentu
	# yang statusnya draft dan reference nya kosong, ketika difilter kok ngga keluar?
		args = []
	# Pool domains
		args.extend(self._kontra_bon_pool_supplier(domain))
		args.extend(self._kontra_bon_pool_state(domain))
		args.extend(self._kontra_bon_pool_date(domain))
		
		account_voucher = self.env['account.voucher']
		vouchers = account_voucher.search(args)
		result = []
		for voucher in vouchers:
			line_dr_ids = []
			included_line_counter = 0
			for line_dr in voucher.line_dr_ids:
				line = {}
				line_total_amount = 0
				if line_dr.amount > 0:
					line.update({'move_line_id': line_dr.move_line_id.name})
					line.update({'date_due': self._format_date(line_dr.date_due)})
					line.update({'amount': line_dr.amount})
					line_dr_ids.append(line)
					line_total_amount += line_dr.amount
					included_line_counter += 1
			if voucher.reference == False:
				reference = ''
			else:
				reference = voucher.reference
			if voucher.state != 'draft':
				style_button = 'display: none;'
				style_input = 'pointer-events: none;'
			else:
				style_button = ''
				style_input = ''
			record = {'id': voucher.id,
				'partner_id': voucher.partner_id.name,
				'date': self._format_date(voucher.date),
				'line_dr_ids': line_dr_ids,
				'line_dr_ids_length': included_line_counter,
				'amount': voucher.amount,
				'journal_id': voucher.journal_id.name,
				'reference': reference,
				'check_maturity_date': voucher.check_maturity_date if voucher.check_maturity_date else '',
				'style_button': style_button,
				'style_input': style_input
			}
			result.append(record)
		return result
	
	def _format_date(self, date_string):
		if date_string:
			return datetime.strptime(date_string, '%Y-%m-%d').strftime('%d-%m-%Y')
		else:
			return '-'
	
	def _kontra_bon_pool_supplier(self, domain):
		args = []
		supplier = domain.get('supplier', '').strip()
		supplier = supplier.encode('ascii', 'ignore')
		if supplier.isdigit():
			args.append(['partner_id.id', '=', supplier]);
		return args
	
	def _kontra_bon_pool_state(self, domain):
		args = []
		state = domain.get('state', '').strip()
		if state == 'draft':
			args.append(['state', '=', 'draft'])
			args.append(['reference', '=', False])
		elif state == 'giro':
			args.append(['state', '=', 'draft'])
			args.append(['reference', '!=', False])
		elif state == 'posted':
			args.append(['state', '=', 'posted'])
		return args
	
	def _kontra_bon_pool_date(self, domain):
		args = []
		time_range = domain.get('time_range', '').strip()
		if time_range != '':
			date_start = ''
			date_end = date.today().strftime('%Y-%m-%d')
			if time_range == 'this_month':
				date_start = date.today().strftime('%Y-%m-01')
			elif time_range == 'last_month':
				date_start = (date.today() + relativedelta(months=-1)).strftime('%Y-%m-%d')
			elif time_range == 'last_3month':
				date_start = (date.today() + relativedelta(months=-3)).strftime('%Y-%m-%d')
			if date_start:
				args.append(['date', '>=', date_start])
			if date_end:
				args.append(['date', '<=', date_end])
		return args
	
	def save_kontra_bon(self, domain, context={}):
		account_voucher = self.env['account.voucher']
		vouchers = account_voucher.search([('id', '=', domain.get('id', ''))])
		return vouchers.write(domain)
		
	# def load_kontra_bon(self, env, domain, context={}):
	# 	uid = env.uid
	#
	# # direct mysql query
	#
	# # ambil filter dari domain
	# 	supplier = domain.get('supplier','').strip()
	# 	if supplier == '-': supplier = ''
	# 	state = domain.get('state','all')
	# 	time_range = domain.get('time_range','all')
	# 	print supplier, state, time_range
	# # bikin string buat WHERE clause
	# 	wherestr = []
	# 	if state != 'all':
	# 		if state == 'draft':
	# 			wherestr.append("paid = 0")
	# 			wherestr.append("(no_giro IS NULL OR no_giro = '')")
	# 		elif state == 'giro':
	# 			wherestr.append("paid = 0")
	# 			wherestr.append("(no_giro IS NOT NULL AND no_giro <> '')")
	# 		elif state == 'paid':
	# 			wherestr.append("paid = 1")
	# 	if time_range != 'all':
	# 		now = datetime.now()
	# 		if time_range == 'this_month':
	# 			date = now.strftime('%Y-%m-01')
	# 			wherestr.append("tanggal_kontra >= '%s'" % date)
	# 		elif time_range == 'last_month':
	# 			date_from = (now - timedelta(days=30)).strftime('%Y-%m-01')
	# 			date_to = (datetime.strptime(now.strftime('%Y-%m-01'),"%Y-%m-%d") - timedelta(minute=1)).strftime('%Y-%m-%d')
	# 			wherestr.append("tanggal_kontra >= '%s'" % date_from)
	# 			wherestr.append("tanggal_kontra <= '%s'" % date_to)
	# 		elif time_range == 'last_3month':
	# 			date_from = (now - timedelta(days=90)).strftime('%Y-%m-01')
	# 			date_to = (datetime.strptime(now.strftime('%Y-%m-01'),"%Y-%m-%d") - timedelta(minute=1)).strftime('%Y-%m-%d')
	# 			wherestr.append("tanggal_kontra >= '%s'" % date_from)
	# 			wherestr.append("tanggal_kontra <= '%s'" % date_to)
	#
	# # ambil datanya
	# 	mysql_bridge_obj = env['tbvip.mysql.bridge']
	# 	cursor = mysql_bridge_obj.mysql_connect()
	# 	print """
	# 		SELECT
	# 			mst.kontra_bon_id,
	# 			(SELECT invoice FROM t_master_purchase22 purchase WHERE purchase.purchase_id = det.purchase_id) AS invoice,
	# 			(SELECT total FROM t_master_purchase22 purchase WHERE purchase.purchase_id = det.purchase_id) AS total_purchase,
	# 			tanggal_kontra,
	# 			(SELECT name FROM t_supplier supplier WHERE supplier.supplier_id = mst.supplier_id) AS supplier,
	# 			mst.total AS total_kontra,
	# 			bank,
	# 			no_giro,
	# 			tanggal_giro,
	# 			value_giro,
	# 			paid,
	# 			keterangan
	# 		FROM t_detail_kontra_bon det, t_master_kontra_bon mst
	# 		WHERE
	# 			det.kontra_bon_id = mst.kontra_bon_id AND %s
	# 		ORDER BY
	# 			supplier, tanggal_kontra DESC
	# 	""" % " AND ".join(wherestr)
	# 	cursor.execute("""
	# 		SELECT
	# 			mst.kontra_bon_id,
	# 			(SELECT invoice FROM t_master_purchase22 purchase WHERE purchase.purchase_id = det.purchase_id) AS invoice,
	# 			(SELECT total FROM t_master_purchase22 purchase WHERE purchase.purchase_id = det.purchase_id) AS total_purchase,
	# 			tanggal_kontra,
	# 			(SELECT name FROM t_supplier supplier WHERE supplier.supplier_id = mst.supplier_id) AS supplier,
	# 			mst.total AS total_kontra,
	# 			bank,
	# 			no_giro,
	# 			tanggal_giro,
	# 			value_giro,
	# 			paid,
	# 			keterangan
	# 		FROM t_detail_kontra_bon det, t_master_kontra_bon mst
	# 		WHERE
	# 			det.kontra_bon_id = mst.kontra_bon_id AND %s
	# 		ORDER BY
	# 			supplier, tanggal_kontra DESC
	# 	""" % " AND ".join(wherestr))
	#
	# # convert datanya supaya satu kontra bon = satu baris,
	# 	result = {}
	# 	for kontra in cursor.fetchall():
	# 		key = kontra['kontra_bon_id']
	# 		if key not in result:
	# 			result.update({key : {
	# 				'id': key,
	# 				'tanggal_kontra': kontra['tanggal_kontra'] and kontra['tanggal_kontra'].strftime("%d/%m/%Y") or "",
	# 				'supplier': kontra['supplier'],
	# 				'total_kontra': kontra['total_kontra'],
	# 				'bank': kontra['bank'],
	# 				'no_giro': kontra['no_giro'],
	# 				'tanggal_giro': kontra['tanggal_giro'] and kontra['tanggal_giro'].strftime("%d/%m/%Y") or "",
	# 				'value_giro': kontra['value_giro'],
	# 				'paid': kontra['paid'],
	# 				'keterangan': kontra['keterangan'],
	# 				'kontra_lines': []
	# 				}
	# 				})
	# 		result[key]['kontra_lines'].append({
	# 			'invoice': kontra['invoice'],
	# 			'total_purchase': kontra['total_purchase'],
	# 			})
	# 	return sorted(result.values(), key=lambda kontra: kontra['supplier'])
	
		"""
		domain = []
		if state != 'all':
			domain.append(('state','=',state))
		if time_range:
			now = datetime.now()
			if time_range == 'this_month':
				date = now.strftime('%Y-%m-01')
				domain.append(('date','>=',date))
			elif time_range == 'last_month':
				date_from = (now - timedelta(days=30)).strftime('%Y-%m-01')
				date_to = (datetime.strptime(now.strftime('%Y-%m-01'),"%Y-%m-%d") - timedelta(minute=1)).strftime('%Y-%m-%d')
				domain.append(('date','>=',date_from))
				domain.append(('date','<=',date_to))
			elif time_range == 'last_3month':
				date_from = (now - timedelta(days=90)).strftime('%Y-%m-01')
				date_to = (datetime.strptime(now.strftime('%Y-%m-01'),"%Y-%m-%d") - timedelta(minute=1)).strftime('%Y-%m-%d')
				domain.append(('date','>=',date_from))
				domain.append(('date','<=',date_to))
	# ambil data vouchernya
		voucher_obj = env['account.voucher']
		vouchers = voucher_obj.sudo().search(domain,order="date desc")
	# pisahkan jadi draft, posted, canceled
		draft = []
		posted = []
		canceled = []
		for row in vouchers:
			single_voucher = {
				'date': row.date,
				'supplier_id': row.partner_id.id,
				'supplier_name': row.partner_id.name,
				'amount': row.amount,
				'reference': row.reference,
				'name': row.name,
				'state': row.state,
			}
			if row.state == 'draft':
				draft.append(single_voucher)
			elif row.state == 'cancel':
				canceled.append(single_voucher)
			else:
				posted.append(single_voucher)
	# gabungin jadi satu lagi dengna urutan draft, posted, canceled
		voucher_list = []
		for row in draft: voucher_list.append(row)
		for row in posted: voucher_list.append(row)
		for row in canceled: voucher_list.append(row)
		"""
