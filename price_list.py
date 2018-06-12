from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.tools.translate import _

import utility

# ==========================================================================================================================

class price_list(osv.osv):
	_inherit = 'price.list'

	def _default_partner_id(self, cr, uid, context=None):
		print "masuk default"
		if context.get('price_list_mode', False) == 'sell':
			model, general_customer_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'tbvip', 'tbvip_customer_general')
			return general_customer_id
		else:
			return None

	_defaults = {
		'partner_id': _default_partner_id,
	}

# METHOD --------------------------------------------------------------------------------------------------------------------
	
	def _create_product_current_price_if_none(self, cr, uid, price_type_id, product_id, uom_id, price, disc, partner_id=None, start_date=None):
		product_current_price_obj = self.pool.get('product.current.price')
		if not start_date:
			start_date = (datetime.now() - timedelta(hours=7)).strftime(DEFAULT_SERVER_DATE_FORMAT)
		domain = [
			('price_type_id', '=', price_type_id),
			('product_id', '=', product_id),
			('start_date','<=',start_date),
		]
		if partner_id:
			domain.append(('partner_id','=',partner_id))
		product_current_price_ids = product_current_price_obj.search(cr, uid, domain, 
			order='start_date DESC', limit=1)
		if len(product_current_price_ids) == 0:
			product_current_price_obj.create(cr, uid, {
				'price_type_id': price_type_id,
				'product_id': product_id,
				'start_date': start_date,
				'partner_id': partner_id,
				'uom_id_1': uom_id,
				'price_1': price,
				#TEGUH@20180501 : tambah field diskon
				'disc_1' : disc,
			})
		else:
			add = True
			field_uom = False
			field_price = False
			product_current_price = product_current_price_obj.browse(cr, uid, product_current_price_ids)[0]
			if product_current_price['uom_id_1'].id == uom_id or \
				product_current_price['uom_id_2'].id == uom_id or \
				product_current_price['uom_id_3'].id == uom_id or \
				product_current_price['uom_id_4'].id == uom_id or \
				product_current_price['uom_id_5'].id == uom_id:
				add = False
			if add:
				if not product_current_price['uom_id_1']:
					field_uom = 'uom_id_1'
					field_price = 'price_1'
					field_disc = 'disc_1'
				elif not product_current_price['uom_id_2']:
					field_uom = 'uom_id_2'
					field_price = 'price_2'
					field_disc = 'disc_2'
				elif not product_current_price['uom_id_3']:
					field_uom = 'uom_id_3'
					field_price = 'price_3'
					field_disc = 'disc_3'
				elif not product_current_price['uom_id_4']:
					field_uom = 'uom_id_4'
					field_price = 'price_4'
					field_disc = 'disc_4'
				elif not product_current_price['uom_id_5']:
					field_uom = 'uom_id_5'
					field_price = 'price_5'
					field_disc = 'disc_5'
				if field_uom and field_price:
					product_current_price_obj.write(cr, uid, [product_current_price.id], {
						'price_type_id': price_type_id,
						'product_id': product_id,
						field_uom: uom_id,
						field_price: price,
						field_disc : disc, #TEGUH@20180501 : tambah field disc
					})
				else:
					pass  # penuh field uomnya
		# tidak ada uom baru yang diperkenalkan untuk price ini
		# tetaplah cari utk uom yang diminta, apakah harganya 0. kalau iya maka 
		# ubah harga itu
			else:
				if price:
					if product_current_price['uom_id_1'].id == uom_id and not product_current_price['price_1']:
						field_price = 'price_1'
					if product_current_price['uom_id_2'].id == uom_id and not product_current_price['price_2']:
						field_price = 'price_2'
					if product_current_price['uom_id_3'].id == uom_id and not product_current_price['price_3']:
						field_price = 'price_3'
					if product_current_price['uom_id_4'].id == uom_id and not product_current_price['price_4']:
						field_price = 'price_4'
					if product_current_price['uom_id_5'].id == uom_id and not product_current_price['price_5']:
						field_price = 'price_5'
					if field_price:
						product_current_price_obj.write(cr, uid, [product_current_price.id], {
							field_price: price,
						})

	def _prepare_product_price_line(self, price_list_line):
		result = super(price_list, self)._prepare_product_price_line(price_list_line)
		result.update({
			'disc_1': price_list_line.disc_1,
			'disc_2': price_list_line.disc_2,
			'disc_3': price_list_line.disc_3,
			'disc_4': price_list_line.disc_4,
			'disc_5': price_list_line.disc_5,
			})
		return result

# ==========================================================================================================================

class price_list_line_product(osv.osv):
	_inherit = 'price.list.line.product'
	
	_columns = {
		'disc_1':fields.char('Discount 1'),
		'disc_2':fields.char('Discount 2'),
		'disc_3':fields.char('Discount 3'),
		'disc_4':fields.char('Discount 4'),
		'disc_5':fields.char('Discount 5'),
	}

# ==========================================================================================================================

class price_list_line_category(osv.osv):
	_inherit = 'price.list.line.category'
	
	_columns = {
		'disc_1':fields.char('Discount 1'),
		'disc_2':fields.char('Discount 2'),
		'disc_3':fields.char('Discount 3'),
		'disc_4':fields.char('Discount 4'),
		'disc_5':fields.char('Discount 5'),
	}

# ==========================================================================================================================

class product_current_price(osv.osv):
	_inherit = 'product.current.price'

	_columns = {
		'disc_1':fields.char('Discount 1'),
		'disc_2':fields.char('Discount 2'),
		'disc_3':fields.char('Discount 3'),
		'disc_4':fields.char('Discount 4'),
		'disc_5':fields.char('Discount 5'),
	}
	
# OVERRIDE ------------------------------------------------------------------------------------------------------------------

	def onchange_product_id(self, cr, uid, ids, product_category_id, context=None):
		res = super(product_current_price, self).onchange_product_id(cr, uid, ids, product_category_id, context)
		res = utility.update_uom_domain_price_list(res)
		return res

