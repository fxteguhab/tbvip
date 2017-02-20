from openerp.osv import osv, fields

class purchase_needs(osv.Model):
    _inherit = 'purchase.needs'

    _columns = {
        'branch_id': fields.many2one('tbvip.branch', 'Branch', required=True),
    }