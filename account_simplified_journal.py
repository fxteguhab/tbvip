from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime, date, timedelta


class account_journal_simplified(osv.osv):
	_inherit = 'account.journal.simplified'
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch'),
		'preset_id': fields.many2one('account.journal.preset', 'Transaction Type', required=True, domain="['|', ('branch_id', '=', branch_id), ('branch_id', '=', False)]"),
	}
	
	_defaults = {
		'branch_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id,
	}
	

class account_journal_preset(osv.osv):
	_inherit = 'account.journal.preset'
	
	_columns = {
		'branch_id': fields.many2one('tbvip.branch', 'Branch', help="Empty for global preset."),
	}
	
	_defaults = {
		'branch_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context).branch_id.id,
	}
