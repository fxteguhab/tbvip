from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from openerp.tools.translate import _
from openerp import SUPERUSER_ID, api


from mako.lookup import TemplateLookup
import os
tpl_lookup = TemplateLookup(directories=['openerp/addons/tbvip/print_template'])

_INTERBRANCH_STATE = [
	('draft', 'Draft'),
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
		'from_stock_location_id': fields.many2one('stock.location', 'From Location', required=True),
		'to_stock_location_id': fields.many2one('stock.location', 'To Location', required=True),
		'input_user_id': fields.many2one('res.users', 'Input by', required=True),
		'prepare_employee_id':  fields.many2one('hr.employee', 'Prepared by', required=True),
		'move_date': fields.datetime('Move Date', required=True),
		'state': fields.selection(_INTERBRANCH_STATE, 'State', readonly=True),
		'accepted_by_user_id': fields.many2one('res.users', 'Accepted by'),
		'rejected_by_user_id': fields.many2one('res.users', 'Rejected by'),
		'interbranch_stock_move_line_ids': fields.one2many('tbvip.interbranch.stock.move.line', 'header_id', 'Move Lines'),
	}
	
	_defaults = {
		'from_stock_location_id': lambda self, cr, uid, ctx:
			self.pool.get('res.users').browse(cr, uid, uid, ctx).branch_id.default_outgoing_location_id.id,
		'input_user_id': lambda self, cr, uid, ctx: uid,
		'move_date': lambda self, cr, uid, ctx: datetime.now(),
		'state': 'draft',
	}
	
	# OVERRIDES ------------------------------------------------------------------------------------------------------------

	def name_get(self, cr, uid, ids, context=None):
		result = []
		for interbranch_move in self.browse(cr, uid, ids, context):
			result.append((
				interbranch_move.id,
				interbranch_move.move_date + ' | ' + interbranch_move.from_stock_location_id.name + ' -> ' + interbranch_move.to_stock_location_id.name
			))
		return result
	
	# METHODS --------------------------------------------------------------------------------------------------------------
	
	def action_accept(self, cr, uid, ids, context=None):
		for interbranch_stock_move in self.browse(cr, uid, ids):
			self._create_picking_draft(cr, uid, interbranch_stock_move, context=context)
		# accepted by user uid
		self.write(cr, uid, ids, {
			'state': 'accepted',
			'accepted_by_user_id': uid,
		}, context=context)
		return True
	
	def action_reject(self, cr, uid, ids, context=None):
		# rejected by user uid
		self.write(cr, uid, ids, {
			'state': 'rejected',
			'rejected_by_user_id': uid,
		}, context=context)
		return True
	
	def _create_picking_draft(self,cr, uid, interbranch_stock_move, context={}):
		picking_obj = self.pool.get('stock.picking')
		seq_obj = self.pool.get('ir.sequence')
		picking_type_obj = self.pool.get('stock.picking.type')
		stock_move_obj = self.pool.get('stock.move')
		warehouse_obj = self.pool.get('stock.warehouse')
		stock_location_obj = self.pool.get('stock.location')
		if len(interbranch_stock_move.interbranch_stock_move_line_ids)>0:
			#order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship.
			max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
			max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
			
			location_src =  stock_location_obj.browse(cr, uid, interbranch_stock_move.from_stock_location_id.id)
			location_dest = stock_location_obj.browse(cr, uid, interbranch_stock_move.to_stock_location_id.id)
			
			warehouse_id = warehouse_obj.search(cr, uid, [('lot_stock_id', '=', location_src.id)], limit = 1)
			warehouse = warehouse_obj.browse(cr, uid, warehouse_id)
			int_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence internal'), 'prefix': warehouse.code + '/INT/', 'padding': 5}, context=context)
			
			# contoh create dapet dari stock, create_sequences_and_picking_types, baris 3461
			picking_type_id = picking_type_obj.create(cr, uid, vals={
				'name': _('Receipts'),
				'warehouse_id': warehouse.id,
				'code': 'internal',
				'sequence_id': int_seq_id,
				'default_location_src_id': location_src.id,
				'default_location_dest_id': location_dest.id,
				'sequence': max_sequence + 1,
				# 'color': color
			}, context=context)
			
			# contoh create dapet dari point_of_sale, create_picking, baris 843
			picking_id =  picking_obj.create(cr, uid, {
				'picking_type_id': picking_type_id,
				'move_type': 'direct',
				'note': 'Interbranch Stock Move ' + location_src.name + '/' + location_dest.name,
				'location_id': location_src.id,
				'location_dest_id': location_dest.id,
				# 'origin': order.name,
				# 'partner_id': addr.get('delivery',False),
				# 'date_done' : order.date_order,
				# 'invoice_state': 'none',
				# 'company_id': self.pool.get('res.company')._company_default_get(cr, uid, 'stock.location', context=c),
			}, context=context)
			#untuk setiap product, bikin stock movenya
			for line in interbranch_stock_move.interbranch_stock_move_line_ids:
				picking_type_id = stock_move_obj.create(cr, uid, vals={
					'name': _('Stock_move') + ' ' + location_src.name + '/' + location_dest.name,
					'warehouse_id': warehouse.id,
					'location_id': location_src.id,
					'location_dest_id': location_dest.id,
					'sequence': max_sequence + 1,
					'product_id': line.product_id.id,
					'product_uom': line.uom_id.id,
					'picking_id' : picking_id
					# 'color': color
				}, context=context)
				
			#call workflow to make picking transferred
			self._transfer_stock_picking(cr, uid, [picking_id], context = context)
		return
	
	def _transfer_stock_picking(self, cr, uid, ids_picking, context = {}):
		stock_picking_obj = self.pool.get('stock.picking')
		pop_up = stock_picking_obj.do_enter_transfer_details(cr, uid, ids_picking, context)
		if pop_up:
			stock_transfer_detail_id = pop_up['res_id']
			stock_transfer_detail_obj = self.pool.get(pop_up['res_model'])
			stock_transfer_detail_obj.do_detailed_transfer(cr, uid, stock_transfer_detail_id)
	
	# PRINTS ----------------------------------------------------------------------------------------------------------------
	
	def print_interbranch_stock_move(self, cr, uid, ids, context):
		tpl = tpl_lookup.get_template('interbranch_stock_move.txt')
		tpl_line = tpl_lookup.get_template('interbranch_stock_move_line.txt')
		
		for ism in self.browse(cr, uid, ids, context=context):
			company = ism.create_uid.company_id
			company_name = company.name if company.name else ''
			from_location = ism.from_stock_location_id.name if ism.from_stock_location_id.name else ''
			to_location = ism.to_stock_location_id.name if ism.to_stock_location_id.name else ''
			move_date = ism.move_date
			input_by = ism.input_user_id.name if ism.input_user_id.name else ''
			prepare_by = ism.prepare_employee_id.user_id.name if ism.prepare_employee_id.user_id.name else ''
			accepted_by = ism.accepted_by_user_id.user_id.name if ism.accepted_by_user_id.user_id.name else ''
			rejected_by = ism.rejected_by_user_id.user_id.name if ism.rejected_by_user_id.user_id.name else ''
			
			# add lines
			row_number = 0
			ism_line = []
			for line in ism.interbranch_stock_move_line_ids:
				row_number += 1
				row = tpl_line.render(
					no=str(row_number),
					name=str(line.product_id.name),
					qty=str(line.qty),
					uom=str(line.uom_id.name),
					is_changed='v' if line.is_changed else '',
				)
				ism_line.append(row)
			# render account voucher
			account_voucher = tpl.render(
				company_name=company_name,
				from_location=from_location,
				to_location=to_location,
				state=_(dict(_INTERBRANCH_STATE).get(ism.state,'-')),
				move_date=datetime.strptime(move_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d'),
				input_by=input_by,
				prepare_by=prepare_by,
				accepted_by=accepted_by,
				rejected_by=rejected_by,
				lines=ism_line,
			)
			
			# Create temporary file
			path_file = 'openerp/addons/tbvip/tmp/'
			filename = path_file + 'print_kontra_bon ' + datetime.now().strftime('%Y-%m-%d %H%M%S') + '.txt'
			# Put rendered string to file
			f = open(filename, 'w')
			f.write(account_voucher.replace("\r\n", "\n"))
			f.close()
			# Process printing
			os.system('lpr -Pnama_printer %s' % filename)
		# Remove printed file
		# os.remove(filename) #TODO UNCOMMENT
		return True
	
# ==========================================================================================================================

class tbvip_interbranch_stock_move_line(osv.Model):
	_name = 'tbvip.interbranch.stock.move.line'
	_description = 'Detail Stock Move between branches'
	
	# COLUMNS --------------------------------------------------------------------------------------------------------------
	
	_columns = {
		'header_id': fields.many2one('tbvip.interbranch.stock.move', 'Interbranch Stock Move'),
		'product_id': fields.many2one('product.product', 'Product', required=True),
		'qty': fields.float('Quantity', required=True),
		'uom_id': fields.many2one('product.uom', 'Product UoM', required=True),
		'is_changed': fields.boolean('Is Changed?'),
		'move_date': fields.related('header_id', 'move_date', type="datetime", string="Move Date"),
		'notes': fields.text('Notes'),
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
			new_product = product_obj.browse(cr, uid, vals['product_id'], context=context)
			tbvip_interbranch_stock_move_obj.message_post(cr, uid, vals['header_id'],
				body=_("New line added: %s %s %s") % (new_product.name, vals['qty'], vals['uom_id']))
		return new_id
	
	def write(self, cr, uid, ids, vals, context=None):
		# if there are any changes, message post to header
		tbvip_interbranch_stock_move_obj = self.pool.get('tbvip.interbranch.stock.move')
		product_obj = self.pool.get('product.product')
		for line in self.browse(cr, uid, ids, context=context):
			if vals.get('header_id', False):
				product_obj = self.pool.get('product.product')
				new_product = product_obj.browse(cr, uid, vals['product_id'], context=context)
				tbvip_interbranch_stock_move_obj.message_post(cr, uid, vals['header_id'],
					body=_("New line added: %s - %s %s") % (new_product.name, vals['qty'], vals['uom_id']))
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
		return {
			'value': {'uom_id': product.product_tmpl_id.uom_id.id},
			'domain': {'uom_id': [('category_id','=', product.product_tmpl_id.uom_id.category_id.id)]}
		}