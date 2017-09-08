from openerp.osv import osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


class stock_return_picking(osv.osv_memory):
    _inherit = 'stock.return.picking'

    def _create_returns(self, cr, uid, ids, context=None):
        new_picking_id, pick_type_id = super(stock_return_picking, self)._create_returns(cr, uid, ids, context=context)
        stock_picking_obj = self.pool.get('stock.picking')
        pop_up = stock_picking_obj.do_enter_transfer_details(cr, uid, [new_picking_id], context)
        if pop_up:
            stock_transfer_detail_id = pop_up['res_id']
            stock_transfer_detail_obj = self.pool.get(pop_up['res_model'])
            stock_transfer = stock_transfer_detail_obj.browse(cr, uid, stock_transfer_detail_id)
            stock_transfer_detail_obj.do_detailed_transfer(cr, uid, stock_transfer_detail_id)
        return new_picking_id, pick_type_id

