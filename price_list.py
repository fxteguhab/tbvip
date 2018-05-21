from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.tools.translate import _

import utility

# ==========================================================================================================================

class product_current_price(osv.osv):
	_inherit = 'product.current.price'
	
# OVERRIDE ------------------------------------------------------------------------------------------------------------------
	def onchange_product_id(self, cr, uid, ids, product_category_id, context=None):
		res = super(product_current_price, self).onchange_product_id(cr, uid, ids, product_category_id, context)
		res = utility.update_uom_domain_price_list(res)
		return res

# ==========================================================================================================================

class price_list(osv.osv):
	_inherit = 'price.list'
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
