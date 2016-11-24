from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta
import mysql.connector
import csv
import os

class tbvip_mysql_bridge(osv.osv):
	
	_name = 'tbvip.mysql.bridge'
	_auto = False
	
	_conn = None
	_cursor = None
	
	def mysql_connect(self):
		self._conn = mysql.connector.connect(user='tbvip', password='hegemoni', database='invent_db', host='invent-db.c0rnoufuieno.ap-southeast-1.rds.amazonaws.com')
		self._cursor = self._conn.cursor(dictionary=True)
		return self._cursor
	
	def mysql_close(self):
		self._cursor.close()
		self._conn.close()
		
	def get_old_new_id_map(self, cr, uid, model_name, old_column_name):
		model_obj = self.pool.get(model_name)
		model_ids = model_obj.search(cr, uid, [])
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
		if not context: context={}
		model_obj = self.pool.get(model_name)
	# coba cari codex_id di data yang sudah ada
		try:
		# kalau ketemu, berarti write
			idx = map_old_ids.index(old_key_value)
			model_obj.write(cr, uid, [map_ids[idx]], data, context=context)
			return map_ids[idx]
		except ValueError:
			if context.get('create_defaults'): # create_defaults berisi field-field default untuk create, bila perlu
				data.update(context.get('create_defaults'))
		# kalau ngga ketemu, bikin baru deh
			return model_obj.create(cr, uid, data)

class tbvip_data_synchronizer(osv.osv):
	
	_name = 'tbvip.data.synchronizer'
	_description = 'Data synchronizer between AWS database and Odoo'
	_auto = False
	
# CRON --------------------------------------------------------------------------------------------------------------------------
	
	def cron_sync_category_product(self, cr, uid, context=None):
		
		mysql_bridge_obj = self.pool.get('tbvip.mysql.bridge')
		
		category_map_codex_ids, category_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'product.category', 'codex_id')
		product_map_codex_ids, product_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'product.product', 'codex_id')
		
		def perform_product_data_conversion(product):
			categ_id = mysql_bridge_obj.get_id_from_old_new_map(category_map_codex_ids, category_map_ids, product['group_id'])
			result = {
				'name': product['name'],
				'codex_id': product['item_id'],
			}
			datatype = ""
			is_variant = (product['type'] == 'g' and (product['name'].find('VARIANT') != -1 or product['name'].find('VARIAN') != -1))
			if product['type'] == 'i' or is_variant:
				datatype = 'product'
				result.update({
					'categ_id': categ_id,
					'active': True,
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
		product_obj = self.pool.get('product.product')
	# ambil datanya
		cursor = mysql_bridge_obj.mysql_connect()
		cursor.execute("SELECT name, group_id, type, item_id FROM t_item_codex WHERE non_active=0")
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
				mysql_bridge_obj.update_insert(cr, uid, 'product.category', product['item_id'], category_map_codex_ids, category_map_ids, data)
			elif datatype == 'product':
				product_buffer.append({
					'is_variant': is_variant,
					'group_id': product['group_id'],
					'data': data,
				})
				
	# SYNC KEPALA PRODUCT VARIANT ---------------------------------------------------------------------------------------------
	
	# pengambilan mapping juga diulang karena di atas sudah ada perubahan karena write (misal pindah kategori) 
	# atau create (ada category baru)
		print '%s start taking care of variants' % datetime.now()
		variant_codex_ids = []
		category_map_codex_ids, category_map_ids = mysql_bridge_obj.get_old_new_id_map(cr, uid, 'product.category', 'codex_id')
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
				print "Kepala variant: %s" % data
				mysql_bridge_obj.update_insert(cr, uid, 'product.product', data['codex_id'], product_map_codex_ids, product_map_ids, data, context=context)
			else:
				fails.append("Variant %s (%s) missing group_id %s" % (data['name'],data['codex_id'],group_id))
	
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
				mysql_bridge_obj.update_insert(cr, uid, 'product.product', data['codex_id'], product_map_codex_ids, product_map_ids, data, context=context)
			else:
				fails.append("Product %s (%s) missing group_id %s" % (data['name'],data['codex_id'],group_id))
		
		print '%s start taking care of anak variants' % datetime.now()

	# UPDATE ATRIBUT+VALUE VARIANT BESERTA PRODUK ANAK VARIANT ----------------------------------------------------------------

	# ambil dari file anak_variant, produk2 variant beserta atribut2 dan value2 variantnya
		try:
			sep = os.sep
			temp = os.path.abspath(os.path.dirname(__file__)).split(sep)
			basepath = ''
			for slicer in temp[:-1]:
				basepath = basepath + slicer + sep
			fullpath = basepath+'/tbvip/static/anak_variant.csv'
			fullpath = fullpath.replace('/',sep)
			f = open(fullpath,'rb')
		except:
			raise osv.except_osv("Sync Error","Source variant file not found.")
		try:
			variant_lines = []
			reader = csv.reader(f)
			for row in reader:
				if row[0] == 'item_id': continue
				variant_lines.append(row)
		except:
			f.close()
			raise osv.except_osv("Sync Error","Unable to open source variant.")
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
				product_group_attributes[parent_variant_id][variant] = list(set(product_group_attributes[parent_variant_id][variant]))
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
				values.append([0,False,{
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
			if attribute.name not in attribute_dict: attribute_dict.update({attribute.name: {'id': attribute.id, 'values': {}}})
			for value in attribute.value_ids:
				attribute_dict[attribute.name]['values'].update({value.name: value.id})
		for key in attribute_dict:
			print "========================================================================"
			print attribute_dict[key]

	# update parent variant dengan menambahkan atribut beserta kemungkinan valuenya
		parent_product_item_ids = product_group_attributes.keys()
		product_obj = self.pool.get('product.product')
		product_tmpl_obj = self.pool.get('product.template')
		product_ids = product_obj.search(cr, uid, [('codex_id','in',parent_product_item_ids)])
		dummy = []
		for product in product_obj.browse(cr, uid, product_ids):
			product_id = product.product_tmpl_id.id
			if product_id in dummy: continue
			if len(product.attribute_line_ids) > 0: continue # hanya update variant yang belum ada saja
			if product_id not in dummy: dummy.append(product_id)
			variant_data = product_group_attributes[str(product.codex_id)]
			attribute_line_ids = []
			for variant_name in variant_data:
				value_ids = []
				for value in variant_data[variant_name]:
					value_ids.append(attribute_dict[variant_name]['values'][value])
				attribute_line_ids.append([0,False,{
					'attribute_id': attribute_dict[variant_name]['id'], 
					'value_ids': [[6,False,value_ids]]
				}])
			print attribute_line_ids
			product_tmpl_obj.write(cr, uid, [product_id], {
				'attribute_line_ids': attribute_line_ids
			})
			
		print '%s finished' % datetime.now()
		
		# mysql_bridge_obj.mysql_close()
		
