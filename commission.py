from datetime import datetime

from openerp.osv import osv, fields
from openerp.tools.translate import _

_COMMISSION_STATE = [
	('draft', 'Draft'),
	('running', 'Running'),
	('expired', 'Expired'),
]

_COMMISSION_TYPE = [
	('product', 'Product'),
	('category', 'Category'),
]

# ==========================================================================================================================

class commission(osv.osv):
	_name = 'tbvip.commission'
	
	_columns = {
		'name': fields.char('Name', required=True),
		'start_date': fields.date('Start Date', required=True),
		'type': fields.selection(_COMMISSION_TYPE, 'Type', required=True),
		'line_product_ids': fields.one2many('tbvip.commission.line.product', 'commission_id', 'Commission Product Line'),
		'line_category_ids': fields.one2many('tbvip.commission.line.category', 'commission_id', 'Commission Product Category Line'),
		'state': fields.selection(_COMMISSION_STATE, 'State', required=True),
	}
	
	_defaults = {
		'state': 'draft',
		'type': 'product',
	}
	
	def test_cron_commission(self, cr, uid, commission_ids, context=None):
		self.pool.get('product.current.commission').cron_product_current_commission(cr, uid, context)
	
	def copy(self, cr, uid, id, default=None, context=None):
		arr_product_line = []
		arr_category_line = []
		current_commission = self.browse(cr, uid, [id], context)
		for product_line in current_commission.line_product_ids:
			arr_product_line.append((0, False, {
				'product_template_id': product_line.product_template_id.id,
				'commission': product_line.commission
			}))
		default['line_product_ids'] = arr_product_line
		for category_line in current_commission.line_category_ids:
			arr_category_line.append((0, False, {
				'product_category_id': category_line.product_category_id.id,
				'commission': category_line.commission
			}))
		default['line_category_ids'] = arr_category_line
		return super(commission, self).copy(cr, uid, id, default=default, context=context)
	
	def set_to_draft(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {
			'state': 'draft'
		}, context=context)
	
	def set_to_running(self, cr, uid, ids, context=None):
		for commission in self.browse(cr, uid, ids):
			other_running_commission_ids = self.search(cr, uid, [
				('type', '=', commission.type),
				('state', '=', 'running')
			], context=context)
			if other_running_commission_ids and len(other_running_commission_ids) > 0:
				raise osv.except_orm(_('Commission Error'),
					_('There is another commission that is running.'))
			else:
				self.write(cr, uid, commission.id, {
					'state': 'running'
				}, context=context)
		return True
	
	def set_to_expired(self, cr, uid, ids, context=None):
		return self.write(cr, uid, ids, {
			'state': 'expired'
		}, context=context)

	def activate_commission(self, cr, uid, commission_ids, context=None):
		product_current_commission_obj = self.pool.get('product.current.commission')
		for today_commission in self.browse(cr, uid, commission_ids):
			# update previous commission to be expired, set today commission to be running
			commission_to_be_expired_ids = self.search(cr, uid, [
				('type', '=', today_commission.type),
				('state', '=', 'running')
			], context=context)
			self.set_to_expired(cr, uid, commission_to_be_expired_ids, context)
			self.set_to_running(cr, uid, today_commission.id, context)
			
			product_obj = self.pool.get('product.product')
			if today_commission.type == 'product':
				# for every product line in commission
				for product_line in today_commission.line_product_ids:
					product_current_commission_ids = product_current_commission_obj.search(cr, uid, [
						('product_id.product_tmpl_id', '=', product_line.product_template_id.id),
					], context=context)
					# update current price
					updated_product_ids = []
					if product_current_commission_ids and len(product_current_commission_ids) > 0:
						for product_current_commission_id in product_current_commission_obj.browse(cr, uid, product_current_commission_ids):
							updated_product_ids.append(product_current_commission_id.product_id.id)
						product_current_commission_obj._update_product_current_commission(cr, uid, product_current_commission_ids, product_line, context=context)
					# create new current prices with the same template as product line
					product_with_no_current_commission_ids = product_obj.search(cr, uid, [
						('product_tmpl_id', '=', product_line.product_template_id.id),
						('id', 'not in', updated_product_ids),
					], context=context)
					product_current_commission_obj._create_product_current_commission(cr, uid,
						product_with_no_current_commission_ids, product_line, context=context)
			else:
				# for every category line in commission
				for category_line in today_commission.line_category_ids:
					product_current_commission_ids = product_current_commission_obj.search(cr, uid, [
						('product_id.product_tmpl_id.categ_id', '=', category_line.product_category_id.id),
					], context=context)
					# update current price
					updated_product_ids = []
					if product_current_commission_ids and len(product_current_commission_ids) > 0:
						for product_current_commission_id in product_current_commission_obj.browse(cr, uid, product_current_commission_ids):
							updated_product_ids.append(product_current_commission_id.product_id.id)
						product_current_commission_obj._update_product_current_commission(cr, uid,
							product_current_commission_ids, category_line, context=context)
					# create new current prices with the same category as product line
					product_with_no_current_commission_ids = product_obj.search(cr, uid, [
						('product_tmpl_id.categ_id', '=', category_line.product_category_id.id),
						('id', 'not in', updated_product_ids),
					], context=context)
					product_current_commission_obj._create_product_current_commission(cr, uid,
						product_with_no_current_commission_ids, category_line, context=context)
		return True

# ==========================================================================================================================

class commission_line_product(osv.osv):
	_name = 'tbvip.commission.line.product'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission_id': fields.many2one('tbvip.commission', 'Commission', required=True),
		'product_template_id': fields.many2one('product.template', 'Product', required=True, ondelete='restrict'),
		'commission': fields.char('Commission', help="Commission String"),
	}

# ==========================================================================================================================

class commission_line_category(osv.osv):
	_name = 'tbvip.commission.line.category'
	
	# COLUMNS ------------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'commission_id': fields.many2one('tbvip.commission', 'Commission', required=True),
		'product_category_id': fields.many2one('product.category', 'Product Category', required=True, ondelete='restrict'),
		'commission': fields.char('Commission', help="Commission String"),
	}

# ==========================================================================================================================

class product_current_commission(osv.osv):
	_name = 'product.current.commission'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='restrict'),
		'commission': fields.char('Commission', help="Commission String"),
	}
	
	_sql_constraints = [
		('unique_product','UNIQUE(product_id)',_('Same product has existed')),
	]
	
	def get_current_commission(self, cr, uid, product_id=False, context=None):
		if product_id:
			product_current_commission_ids = self.search(cr, uid, [
				('product_id', '=', product_id),
			], context=context)
			current_commission = 0
			if len(product_current_commission_ids) > 0:
				product_current_commission = self.browse(cr, uid, product_current_commission_ids[0])
				current_commission = product_current_commission.commission
			return current_commission
		else:
			return False
	
	def _update_product_current_commission(self, cr, uid, ids, commission_line, context=None):
		return self.write(cr, uid, ids, {
			'commission': commission_line.commission,
		}, context=context)
	
	def _create_product_current_commission(self, cr, uid, product_ids, commission_line, context=None):
		new_ids = []
		for product_id in product_ids:
			new_product_current_commission_id = self.create(cr, uid, {
				'product_id': product_id,
				'commission': commission_line.commission,
			}, context=context)
			new_ids.append(new_product_current_commission_id)
		return new_ids
	
	def cron_product_current_commission(self, cr, uid, context={}):
		commission_obj = self.pool.get('tbvip.commission')
		today = datetime.now()
		today_commission_ids = commission_obj.search(cr, uid, [
			('start_date', '>=', today.strftime("%Y-%m-%d 00:00:00")),
			('start_date', '<=', today.strftime("%Y-%m-%d 23:59:59")),
			('state', '=', 'draft')
		], context=context)
		for today_commission_id in today_commission_ids:
			try:
				# one by one so that if one fails, others can still be updated
				commission_obj.activate_commission(cr, uid, today_commission_id, context)
			except:
				pass
		return True