from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _
from openerp import SUPERUSER_ID, api


# TEGUH@20180329 : Tambah state otw,delivered
_INTERBRANCH_STATE = [
	('draft', 'Draft'),
	('request', 'Request Transfer'),
	('ready','Ready To Transfer'),
	('otw', 'OnTheWay'),
	('delivered', 'Delivered'),
	('accepted', 'Accepted'),
	('rejected', 'Rejected')
]

# ==========================================================================================================================

class tbvip_interbranch_stock_move(osv.Model):
	_name = 'tbvip.interbranch.stock.move'
	_description = 'Stock Move between branches'
	_inherit = ['mail.thread']
	_order = "move_date DESC, id DESC"
	
	# COLUMNS --------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'from_stock_location_id': fields.many2one('stock.location', 'From Location', domain=[('usage', '=', 'internal')], readonly=True, required=True, states={'draft': [('readonly', False)]}),
		'to_stock_location_id': fields.many2one('stock.location', 'To Location', domain=[('usage', '=', 'internal')], readonly=True,required=True, states={'draft': [('readonly', False)]}),
		'input_user_id': fields.many2one('res.users', 'Input by', required=True, readonly=True, states={'draft': [('readonly', False)]}),
		#TEGUH @20180331 : field prepared by jadi tidak required
		'prepare_employee_id':  fields.many2one('hr.employee', 'Prepared by', readonly=False, states={'accepted': [('readonly', True)],'rejected': [('readonly', True)]}),
		#'prepare_employee_id':  fields.many2one('hr.employee', 'Prepared by', readonly=True, required=True, states={'draft': [('readonly', False)]}),
		#TEGUH @20180331 : field prepared by & check by readonly di state2 tertentu
		'checked_by_id': fields.many2one('hr.employee', 'Checked by', readonly=False, states={'accepted': [('readonly', True)],'rejected': [('readonly', True)]}),
		'move_date': fields.datetime('Move Date', required=True, readonly=True, states={'draft': [('readonly', False)]}),
		'state': fields.selection(_INTERBRANCH_STATE, 'State', readonly=False),
		'accepted_by_user_id': fields.many2one('res.users', 'Accepted by', readonly=True, states={'draft': [('readonly', False)]}),
		'rejected_by_user_id': fields.many2one('res.users', 'Rejected by', readonly=True, states={'draft': [('readonly', False)]}),
		'interbranch_stock_move_line_ids': fields.one2many('tbvip.interbranch.stock.move.line', 'header_id', 'Move Lines', readonly=False, states={'accepted': [('readonly', True)],'rejected': [('readonly', True)]}),
	}
	
	_defaults = {
		'from_stock_location_id': lambda self, cr, uid, ctx:
			self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_outgoing_location_id.id,
		'input_user_id': lambda self, cr, uid, ctx: uid,
		'move_date': lambda *a: datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
		'state': 'draft',
	}
	
	# OVERRIDES ------------------------------------------------------------------------------------------------------------

	def name_get(self, cr, uid, ids, context=None):
		result = []
		for interbranch_move in self.browse(cr, uid, ids, context):
			localized_date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(interbranch_move.move_date,
				DEFAULT_SERVER_DATETIME_FORMAT), context)
			'''
			result.append((
				interbranch_move.id,
				'{} | {} -> {}'.format(
					localized_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
					interbranch_move.from_stock_location_id.name,
					interbranch_move.to_stock_location_id.name
				)
			'''
			result.append((
				interbranch_move.id,
				'{} | {} -> {}'.format(
					interbranch_move.id,
					localized_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
					interbranch_move.from_stock_location_id.name,
					interbranch_move.to_stock_location_id.name
				)
			))
		return result

	def unlink(self, cr, uid, ids, context={}):
	# kalau sudah accepted ga boleh dihapus
		for data in self.browse(cr, uid, ids):
			if data.state in ['accepted']:
				raise osv.except_osv(_('Interbranch Move Error'),_('One or more of selected transfers has been set as Accepted. You cannot delete these anymore.'))
		return super(tbvip_interbranch_stock_move, self).unlink(cr, uid, ids, context=context)
	
	# METHODS --------------------------------------------------------------------------------------------------------------

	# TEGUH@20180329 : tambah fungsi untuk ubah state jadi otw & delivered
	def action_otw(self, cr, uid, ids, context=None):
	# state otw melalui canvassing on the way
		for data in self.browse(cr, uid, ids):
			if data.state not in ['accepted','rejected']:
				self.message_post(cr, uid, ids,body=_("On the way to transfer"))
				self.write(cr, uid, ids, {
				'state': 'otw'
				}, context=context)
		
		return True

	def action_delivered(self, cr, uid, ids, context=None):
	# state delivered melalui canvassing delivered
		for data in self.browse(cr, uid, ids):
			if data.state not in ['accepted','rejected']:
				self.message_post(cr, uid, ids,body=_("Transfer Delivered"))
				self.write(cr, uid, ids, {
				'state': 'delivered'
				}, context=context)
		
		return True

	def action_request(self, cr, uid, ids, context=None):
		self.message_post(cr, uid, ids,body=_("Requested Transfer"))
		# state request dr button
		self.write(cr, uid, ids, {
		'state': 'request'
		}, context=context)
		
		return True

	def action_ready(self, cr, uid, ids, context={}):	
		#set picking state jadi Ready to Transfer
		for interbranch_stock_move in self.browse(cr, uid, ids):
			self._create_picking_draft(cr, uid, interbranch_stock_move, context=context)	
			
		self.message_post(cr, uid, ids,body=_("State change to Ready - Stock picking created"))
		self.write(cr, uid, ids, {
			'state': 'ready'
		}, context=context)

		return True

	def action_accept(self, cr, uid, ids, context={}):
		#for interbranch_stock_move in self.browse(cr, uid, ids):
		# JUNED@20180205: ditutup as per request dari Teguh
		#	"""
		#	if not interbranch_stock_move.checked_by_id:
		#		raise osv.except_osv(_('Warning!'), _("Please Fill field Checked By"))
		#	"""
		#	#self._create_picking_draft(cr, uid, interbranch_stock_move, context=context)
		#

		# tandai semua canvassing untuk interbranch ini is_executed = True
		self._write_is_executed_canvassing(cr, uid, ids, context=context)
		#call workflow to make picking transferred
		picking_obj = self.pool.get('stock.picking')
		for interbranch_stock_move in self.browse(cr, uid, ids):
			picking_ids =  picking_obj.search(cr, uid, [('interbranch_move_id', '=', interbranch_stock_move.id)], limit = 1)
			
			#picking_id = [picking_ids]
			#print "picking id:"+str(picking_id)
			self._transfer_stock_picking(cr, uid, picking_ids, context = context)

		self.message_post(cr, uid, ids,body=_("Transfer Accepted"))
		# accepted by user uid
		self.write(cr, uid, ids, {
			'state': 'accepted',
			'accepted_by_user_id': uid,
		}, context=context)
		return True
	
	def action_reject(self, cr, uid, ids, context=None):

		#call workflow to make picking cancelled
		picking_obj = self.pool.get('stock.picking')
		for interbranch_stock_move in self.browse(cr, uid, ids):
			picking_ids =  picking_obj.search(cr, uid, [('interbranch_move_id', '=', interbranch_stock_move.id)], limit = 1)
			picking_obj.action_cancel(cr, uid, picking_ids, context = context)

		self.message_post(cr, uid, ids,body=_("Transfer Rejected"))
		# rejected by user uid
		self.write(cr, uid, ids, {
			'state': 'rejected',
			'rejected_by_user_id': uid,
		}, context=context)
		return True
	
	def _write_is_executed_canvassing(self, cr, uid, interbranch_ids, context={}):
		canvassing_interbranch_obj = self.pool.get('canvassing.canvas.interbranch.line')
		canvassing_interbranch_ids = canvassing_interbranch_obj.search(cr, uid, [('interbranch_move_id', 'in', interbranch_ids)])
		if len(canvassing_interbranch_ids)>0:
			canvassing_interbranch_obj.write(cr, uid, canvassing_interbranch_ids,  {'is_executed': True})
			
	def _create_picking_draft(self,cr, uid, interbranch_stock_move, context={}):
		picking_obj = self.pool.get('stock.picking')
		stock_move_obj = self.pool.get('stock.move')
		warehouse_obj = self.pool.get('stock.warehouse')
		stock_location_obj = self.pool.get('stock.location')
		model_obj = self.pool.get('ir.model.data')
		if len(interbranch_stock_move.interbranch_stock_move_line_ids)>0:
			#order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship.
			#max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
			#max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
			
			location_src =  stock_location_obj.browse(cr, uid, interbranch_stock_move.from_stock_location_id.id)
			location_dest = stock_location_obj.browse(cr, uid, interbranch_stock_move.to_stock_location_id.id)
			
			warehouse_id = warehouse_obj.search(cr, uid, [('lot_stock_id', '=', location_src.id)], limit = 1)
			warehouse = warehouse_obj.browse(cr, uid, warehouse_id)
			picking_type_id = model_obj.get_object_reference(cr, uid, 'stock', 'picking_type_internal')[1]
			
			# contoh create dapet dari point_of_sale, create_picking, baris 843
			picking_id =  picking_obj.create(cr, uid, {
				'picking_type_id': picking_type_id,
				'move_type': 'direct',
				'note': 'Interbranch Stock Move ' + location_src.name + '/' + location_dest.name,
				'location_id': location_src.id,
				'location_dest_id': location_dest.id,
				'origin' : 'Interbranch Stock Move ' + str(interbranch_stock_move.id),
				'interbranch_move_id': interbranch_stock_move.id,
				'state' :'assigned',
			}, context=context)
			#untuk setiap product, bikin stock movenya
			for line in interbranch_stock_move.interbranch_stock_move_line_ids:
				picking_type_id = stock_move_obj.create(cr, uid, vals={
					#'name': _('Stock_move') + ' ' + location_src.name + '/' + location_dest.name,
					'name' : line.product_id.name_template,
					'warehouse_id': warehouse.id,
					'location_id': location_src.id,
					'location_dest_id': location_dest.id,
					#'sequence': max_sequence + 1,
					'product_id': line.product_id.id,
					'product_uom': line.uom_id.id,
					'picking_id' : picking_id,
					'product_uom_qty' : line.qty,
					'state' :'assigned',
				}, context=context)
				
			#call workflow to make picking transferred
			#self._transfer_stock_picking(cr, uid, [picking_id], context = context)
		return
	
	def _transfer_stock_picking(self, cr, uid, ids_picking, context = {}):
		stock_picking_obj = self.pool.get('stock.picking')
		stock_picking_obj.action_confirm(cr, uid, ids_picking, context = context)
		stock_picking_obj.force_assign(cr, uid, ids_picking, context = context)
		pop_up = stock_picking_obj.do_enter_transfer_details(cr, uid, ids_picking, context)
		if pop_up:
			stock_transfer_detail_id = pop_up['res_id']
			stock_transfer_detail_obj = self.pool.get(pop_up['res_model'])
			stock_transfer_detail_obj.do_detailed_transfer(cr, uid, stock_transfer_detail_id)
	
	# PRINTS ----------------------------------------------------------------------------------------------------------------
	
	def print_interbranch_stock_move(self, cr, uid, ids, context):
		if self.browse(cr,uid,ids)[0].interbranch_stock_move_line_ids:
			return {
				'type' : 'ir.actions.act_url',
				'url': '/tbvip/print/tbvip.interbranch.stock.move/' + str(ids[0]),
				'target': 'self',
			}
		else:
			raise osv.except_osv(_('Print Interbranch Stock Move Error'),_('Interbranch must have at least one line to be printed.'))


	def write(self, cr, uid, ids, vals, context=None):
		result = super(tbvip_interbranch_stock_move, self).write(cr, uid, ids, vals, context)
		picking_obj = self.pool.get('stock.picking')

		for interbranch_stock_move in self.browse(cr, uid, ids):
			if interbranch_stock_move.state != 'accepted':
				picking_ids =  picking_obj.search(cr, uid, [('interbranch_move_id', '=', interbranch_stock_move.id)], limit = 1)
				picking_obj.unlink(cr, uid, picking_ids)
				self._create_picking_draft(cr, uid, interbranch_stock_move, context=context)

		return result

# ==========================================================================================================================

class tbvip_interbranch_stock_move_line(osv.Model):
	_name = 'tbvip.interbranch.stock.move.line'
	_description = 'Detail Stock Move between branches'
	
	# COLUMNS --------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'header_id': fields.many2one('tbvip.interbranch.stock.move', 'Interbranch Stock Move', ondelete="cascade"),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'qty': fields.float('Quantity', required=True),
		'uom_id': fields.many2one('product.uom', 'Product UoM', required=True),
		'is_changed': fields.boolean('Is Changed?'),
		'move_date': fields.related('header_id', 'move_date', type="datetime", string="Move Date"),
		'notes': fields.text('Notes'),
		'uom_category_filter_id': fields.related('product_id', 'product_tmpl_id', 'uom_id', 'category_id', relation='product.uom.categ', type='many2one',
			string='UoM Category', readonly=True)
	}
	
	_defaults = {
		'is_changed': False,
	}
	
	# OVERRIDES ------------------------------------------------------------------------------------------------------------
	
	def create(self, cr, uid, vals, context={}):
		new_id = super(tbvip_interbranch_stock_move_line, self).create(cr, uid, vals, context)
		# when created, message post to header
		tbvip_interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		if vals.get('header_id', False):
			product_obj = self.pool.get('product.product')
			uom_obj = self.pool.get('product.uom')
			new_product = product_obj.browse(cr, uid, vals['product_id'], context=context)
			tbvip_interbranch_stock_move_obj.message_post(cr, uid, vals['header_id'],
				body=_("New line added: %s | %s %s") % (new_product.name, vals['qty'], uom_obj.browse(cr, uid, vals['uom_id'], context=context).name))
		return new_id
	
	def write(self, cr, uid, ids, vals, context=None):
		# if there are any changes, message post to header
		tbvip_interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		product_obj = self.pool.get('product.product')
		for line in self.browse(cr, uid, ids, context=context):
			if vals.get('header_id', False):
				product_obj = self.pool.get('product.product')
				uom_obj = self.pool.get('product.uom')
				new_product = product_obj.browse(cr, uid, vals['product_id'], context=context)
				tbvip_interbranch_stock_move_obj.message_post(cr, uid, vals['header_id'],
					body=_("New line added: %s | %s %s") % (new_product.name, vals['qty'], uom_obj.browse(cr, uid, vals['uom_id'], context=context).name))
			if vals.get('product_id', False):
				new_product = product_obj.browse(cr, uid, vals['product_id'], context=context)
				tbvip_interbranch_stock_move_obj.message_post(cr, uid, line.header_id.id,
					body=_("Product \"%s\" changed into \"%s\"") % (line.product_id.name, new_product.name))
			if vals.get('qty', False):
				tbvip_interbranch_stock_move_obj.message_post(cr, uid, line.header_id.id,
					body=_("There is a change on quantity for product \"%s\" from %s to %s") %
						 (line.product_id.name, line.qty, vals['qty']))
			# any changes, if uid not the same as header_id.input_user_id.id, then set is_changed to True
			if not vals.get('is_changed', False):
				if uid != line.header_id.input_user_id.id:
					self.write(cr, uid, line.id, {
						'is_changed': True,
					}, context=context)
		return super(tbvip_interbranch_stock_move_line, self).write(cr, uid, ids, vals, context)
	
	def unlink(self, cr, uid, ids, context=None):
		# when deleted, message post to header
		tbvip_interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		for line in self.browse(cr, uid, ids, context=context):
			tbvip_interbranch_stock_move_obj.message_post(cr, uid, line.header_id.id,
				body=_("Line removed: %s - %s %s") % (line.product_id.name, line.qty, line.uom_id.name))
		return super(tbvip_interbranch_stock_move_line, self).unlink(cr, uid, ids, context)
	
	# METHODS --------------------------------------------------------------------------------------------------------------
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		result = {
			'value': {'uom_id': product.product_tmpl_id.uom_id.id},
			'domain': {'uom_id': [('category_id','=', product.product_tmpl_id.uom_id.category_id.id)]}
		}
		result = self._update_uom_domain_custom_conversion(result)
		return result
	
	def onchange_product_uom(self, cr, uid, ids, product_id, uom_id, context = {}):
		product_conversion_obj = self.pool.get('product.conversion')
		product_obj = self.pool.get('product.product')
		product = product_obj.browse(cr, uid, product_id)
		uom_record = product_conversion_obj.get_conversion_auto_uom(cr, uid, product_id, uom_id)
		result = {
			'value': {'uom_id': uom_record.id},
			'domain': {'uom_id': [('category_id','=', product.product_tmpl_id.uom_id.category_id.id)]}
		}
		result = self._update_uom_domain_custom_conversion(result)
		return result
	
	def _update_uom_domain_custom_conversion(self, onchange_result):
		if onchange_result.get('domain', False):
			if onchange_result['domain'].get('uom_id', False):
				onchange_result['domain']['uom_id'].append(('is_auto_create', '=', False))
			else:
				onchange_result['domain']['uom_id'] = [('is_auto_create', '=', False)]
		else:
			onchange_result.update({'domain': {'uom_id': [('is_auto_create', '=', False)]}})
		return onchange_result
