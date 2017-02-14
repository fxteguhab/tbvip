from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.osv.osv import osv_memory
from datetime import datetime
from openerp.report import report_sxw
from openerp import SUPERUSER_ID
from openerp import http
from openerp.http import request
import re
import xlwt
import StringIO
import base64
import os

_PURCHASE_NEEDS_STATE = (
	('draft', 'Draft'),
	('partial', 'Partial'),
	('fulfilled', 'Fulfilled'),
	('canceled', 'Canceled'),
)

_PURCHASE_NEEDS_LINE_SOURCE = (
	('manual', 'Manual'),
	('generate', 'Generate'),
)

class purchase_needs_algorithm(osv.osv):

	_inherit = 'mail.thread'
	_name = 'tbvip.purchase.needs.algorithm'
	_description = 'Purchase Needs Algorithm'

	def create(self, cr, uid, vals, context={}):
		result = super(purchase_needs_algorithm, self).create(cr, uid, vals, context)
		data = self.browse(cr, uid, result)
		print data
	
	_columns = {
		'name': fields.char('Name', required=True, track_visibility='onchange'),
		'is_used': fields.boolean('Is Used', track_visibility='onchange'),
		'algorithm': fields.text('Address', required=True),
	}
	
	_defaults = {
		'is_used': False,
	}
	
# ======================================================================================================================

class purchase_needs(osv.osv):

	_inherit = 'mail.thread'
	_name = 'tbvip.purchase.needs'
	_description = 'Purchase Needs'
	
	def get_fullfilment_rate(self, cr, uid, ids, field_name, arg, context=None):
		return 0
	
	_columns = {
		'supplier_id': fields.many2one('res.partner', required=True, string='Supplier', domain=[('supplier', '=', 'True')], ondelete='restrict'),
		'target_date': fields.date('Target Date', required=True),
		'algorithm_id': fields.many2one('tbvip.purchase.needs.algorithm', string='Algorithm', ondelete='SET NULL', visible=False),
		'need_line_ids' : fields.one2many('tbvip.purchase.needs.line', 'purchase_needs_id', 'Need Line'),
		'state' : fields.selection(_PURCHASE_NEEDS_STATE, 'State', readonly=True),
		'fullfilment_rate' : fields.function(get_fullfilment_rate, string="Fullfilment Rate", type='float', store=True),
	}
	
	_defaults = {
		'state': 'draft',
	}
	
# ======================================================================================================================

class purchase_needs_line(osv.osv):

	_inherit = 'mail.thread'
	_name = 'tbvip.purchase.needs.line'
	_description = 'Purchase Needs Line'
	
	_columns = {
		'purchase_needs_id': fields.many2one('tbvip.purchase.needs', string='Purchase Needs'),
		'product_id': fields.many2one('product.product', required=True, string='Product', domain=[('purchase_ok', '=', 'True')], ondelete='restrict'),
		'qty': fields.float('Quantity'),
		'source' : fields.selection(_PURCHASE_NEEDS_LINE_SOURCE, 'Source', required=True, readonly=True, visible=False),
		'is_fulfilled': fields.boolean('Is Fulfilled'),
	}
	
	_defaults = {
		'source': 'manual',
		'is_fulfilled': False,
	}