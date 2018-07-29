from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import api
from openerp.osv import osv,fields
from openerp.tools.translate import _

import utility
import openerp.addons.purchase_sale_discount.discount_utility as discount_utility

# ==========================================================================================================================

class price_list(osv.osv):
	_inherit = 'price.list'

	def _default_partner_id(self, cr, uid, context=None):
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
			#start_date = (datetime.now() - timedelta(hours=7)).strftime(DEFAULT_SERVER_DATE_FORMAT)
			start_date = (datetime.now()).strftime(DEFAULT_SERVER_DATE_FORMAT)
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

#============== OVERIDE ===================================================================================================	
#OVERIDE spy bisa ganti price list secara category 
	def activate_price_list(self, cr, uid, price_list_ids, context=None):
		product_current_price_obj = self.pool.get('product.current.price')
		product_obj = self.pool.get('product.product')
	# this price list is applied
		self.set_to_applied(cr, uid, price_list_ids, context)
		for today_price_list in self.browse(cr, uid, price_list_ids):
		
			if today_price_list.type == 'product':
				# for every product line in price list
				for product_line in today_price_list.line_product_ids:
					product_ids = product_obj.search(cr, uid, [('product_tmpl_id','=',product_line.product_template_id.id)])

					# delete previous product price with the same start date, partner, and  price type
					product_current_price_ids = product_current_price_obj.search(cr, uid, [
						('product_id','in',product_ids),
						('price_type_id','=',product_line.price_list_id.price_type_id.id),
						('start_date','=',product_line.price_list_id.start_date),
						('partner_id','=',product_line.price_list_id.partner_id and product_line.price_list_id.partner_id.id or None),
						], order="id DESC", context=context)
					product_current_price_obj.unlink(cr, uid, product_current_price_ids)
					# create new product price records
					# each product under this product template gets its own product price record
					for product_id in product_ids:
						new_price = {
							'product_id': product_id,
							'price_type_id': today_price_list.price_type_id.id,
							'start_date': today_price_list.start_date,
							'partner_id': today_price_list.partner_id and today_price_list.partner_id.id or None,
							}
						new_price.update(self._prepare_product_price_line(product_line))
						product_current_price_obj.create(cr, uid, new_price, context=context)

			elif today_price_list.type == 'category':
				# for every category line in price list
				for category_line in today_price_list.line_category_ids:
					product_ids = product_obj.search(cr, uid, [('product_tmpl_id.categ_id','=',category_line.product_category_id.id)])

					# delete previous product price with the same start date, partner, and  price type
					product_current_price_ids = product_current_price_obj.search(cr, uid, [
						('product_id','in',product_ids),
						('price_type_id','=',category_line.price_list_id.price_type_id.id),
						('start_date','=',category_line.price_list_id.start_date),
						('partner_id','=',category_line.price_list_id.partner_id and category_line.price_list_id.partner_id.id or None),
						], order="id DESC", context=context)
					product_current_price_obj.unlink(cr, uid, product_current_price_ids)
					# create new product price records
					# each product under this product template gets its own product price record
					for product_id in product_ids:
						new_price = {
							'product_id': product_id,
							'price_type_id': today_price_list.price_type_id.id,
							'start_date': today_price_list.start_date,
							'partner_id': today_price_list.partner_id and today_price_list.partner_id.id or None,
							}
						new_price.update(self._prepare_product_price_line(category_line))
						product_current_price_obj.create(cr, uid, new_price, context=context)

		return True
# ==========================================================================================================================

class price_list_line_product(osv.osv):
	_inherit = 'price.list.line.product'

	_max_discount = 3

	_columns = {
		'disc_1':fields.char('Disc 1'),
		'disc_2':fields.char('Disc 2'),
		'disc_3':fields.char('Disc 3'),
		'disc_4':fields.char('Disc 4'),
		'disc_5':fields.char('Disc 5'),

		#TEGUH@20180718 : tambah field nett1 - nett 3
		'nett_1':fields.float('Nett 1', compute="_compute_nett_1"),
		'nett_2':fields.float('Nett 2', compute="_compute_nett_2"),
		'nett_3':fields.float('Nett 3', compute="_compute_nett_3"),
	}
	
	# METHODS ---------------------------------------------------------------------------------------------------------------	
	@api.model
	def _calculate_discounts(self, price_unit, valid_discount_string):
		total_discount = 0
		for discount in discount_utility.calculate_discount(valid_discount_string, price_unit, self._max_discount):
			total_discount += discount
		return total_discount

	@api.one
	@api.depends('price_1', 'disc_1','product_template_id')
	def _compute_nett_1(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_1, self.price_1, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_1,valid_discount_string)
		self.nett_1 = self.price_1 - self.discount_amount_line

	@api.one
	@api.depends('price_2', 'disc_2','product_template_id')
	def _compute_nett_2(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_2, self.price_2, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_2,valid_discount_string)
		self.nett_2 = self.price_2 - self.discount_amount_line	

	@api.one
	@api.depends('price_3', 'disc_3','product_template_id')
	def _compute_nett_3(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_3, self.price_3, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_3,valid_discount_string)
		self.nett_3 = self.price_3 - self.discount_amount_line	
# ==========================================================================================================================

class price_list_line_category(osv.osv):
	_inherit = 'price.list.line.category'

	_max_discount = 3
	
	_columns = {
		'disc_1':fields.char('Disc 1'),
		'disc_2':fields.char('Disc 2'),
		'disc_3':fields.char('Disc 3'),
		'disc_4':fields.char('Disc 4'),
		'disc_5':fields.char('Disc 5'),

		#TEGUH@20180718 : tambah field nett1 - nett 3
		'nett_1':fields.float('Nett 1', compute="_compute_nett_1"),
		'nett_2':fields.float('Nett 2', compute="_compute_nett_2"),
		'nett_3':fields.float('Nett 3', compute="_compute_nett_3"),
	}

	# METHODS ---------------------------------------------------------------------------------------------------------------	
	@api.model
	def _calculate_discounts(self, price_unit, valid_discount_string):
		total_discount = 0
		for discount in discount_utility.calculate_discount(valid_discount_string, price_unit, self._max_discount):
			total_discount += discount
		return total_discount

	@api.one
	@api.depends('price_1', 'disc_1','product_category_id')
	def _compute_nett_1(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_1, self.price_1, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_1,valid_discount_string)
		self.nett_1 = self.price_1 - self.discount_amount_line

	@api.one
	@api.depends('price_2', 'disc_2','product_category_id')
	def _compute_nett_2(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_2, self.price_2, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_2,valid_discount_string)
		self.nett_2 = self.price_2 - self.discount_amount_line	

	@api.one
	@api.depends('price_3', 'disc_3','product_category_id')
	def _compute_nett_3(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_3, self.price_3, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_3,valid_discount_string)
		self.nett_3 = self.price_3 - self.discount_amount_line	
# ==========================================================================================================================

class product_current_price(osv.osv):
	_inherit = 'product.current.price'

	_max_discount = 3

	_columns = {
		'disc_1':fields.char('Disc 1'),
		'disc_2':fields.char('Disc 2'),
		'disc_3':fields.char('Disc 3'),
		'disc_4':fields.char('Disc 4'),
		'disc_5':fields.char('Disc 5'),

		#TEGUH@20180718 : tambah field nett1 - nett 3
		'nett_1':fields.float('Nett 1', compute="_compute_nett_1"),
		'nett_2':fields.float('Nett 2', compute="_compute_nett_2"),
		'nett_3':fields.float('Nett 3', compute="_compute_nett_3"),
	}
	
	# METHODS ---------------------------------------------------------------------------------------------------------------	
	@api.model
	def _calculate_discounts(self, price_unit, valid_discount_string):
		total_discount = 0
		for discount in discount_utility.calculate_discount(valid_discount_string, price_unit, self._max_discount):
			total_discount += discount
		return total_discount

	@api.one
	@api.depends('price_1', 'disc_1','product_id')
	def _compute_nett_1(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_1, self.price_1, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_1,valid_discount_string)
		self.nett_1 = self.price_1 - self.discount_amount_line

	@api.one
	@api.depends('price_2', 'disc_2','product_id')
	def _compute_nett_2(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_2, self.price_2, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_2,valid_discount_string)
		self.nett_2 = self.price_2 - self.discount_amount_line	

	@api.one
	@api.depends('price_3', 'disc_3','product_id')
	def _compute_nett_3(self):
		try:
			valid_discount_string = discount_utility.validate_discount_string(self.disc_3, self.price_3, self._max_discount)
		except discount_utility.InvalidDiscountException as exception:
			raise osv.except_orm(_('Warning!'), exception.message)
		
		self.discount_amount_line = self._calculate_discounts(self.price_3,valid_discount_string)
		self.nett_3 = self.price_3 - self.discount_amount_line	

# OVERRIDE ------------------------------------------------------------------------------------------------------------------

	def onchange_product_id(self, cr, uid, ids, product_category_id, context=None):
		res = super(product_current_price, self).onchange_product_id(cr, uid, ids, product_category_id, context)
		res = utility.update_uom_domain_price_list(res)
		return res
# OVERRIDE ------------------------------------------------------------------------------------------------------------------
class product_template(osv.osv):
	_inherit = 'product.template'
	
	def _price_ids(self, cr, uid, ids, field_name, arg, context={}):
		current_pricelist_obj = self.pool.get('product.current.price')
		result = {}
		for product in self.browse(cr, uid, ids):
			variants = product.product_variant_ids
			if len(variants) > 0:
				variant = variants[0]
				result[product.id] = {
					'buy_prices': current_pricelist_obj.search(cr, uid, [
						('product_id', '=', variant.id),
						#('price_type_id.type','=','buy'),
						('start_date','=','current'),
						]),
					'sell_prices': current_pricelist_obj.search(cr, uid, [
						('product_id', '=', variant.id),
						#('price_type_id.type','=','sell'),
						('start_date','=','current'),
						]),
				}
		return result


