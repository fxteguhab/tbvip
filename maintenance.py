from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.osv import osv, fields
from openerp.tools.translate import _

class tbvip_maintenance(osv.osv):
	_name = 'tbvip.maintenance'
	_description = 'Script sekali-jalan untuk maintenance/update program'
	_auto = False

	def fillin_partner_buy_pricelist(self, cr, uid, context={}):
	# 20180522 isi field partner_id dari product purchase price berdasarkan 
	# po terbaru. ini karena per tanggal ini product current price punya tambahan
	# field partner_id
	# ambil semua product current price buy yang partner nya kosong
		cr.execute("""
			SELECT * FROM product_current_price 
			WHERE 
				partner_id IS NULL AND 
				price_type_id in (SELECT id FROM price_type WHERE type='buy')
			""")
		buy_prices_without_partners = [{'id': row['id'],'product_id': row['product_id']} for row in cr.dictfetchall()]
		for price_data in buy_prices_without_partners:
			cr.execute("""
				SELECT 
					po.partner_id
				FROM purchase_order_line po_line, purchase_order po 
				WHERE 
					po_line.order_id = po.id AND 
					po_line.product_id = %s 
				ORDER BY po.date_order DESC 
				""" % price_data['product_id'])
			po_row = cr.dictfetchone()
			if po_row:
				cr.execute("""
					UPDATE product_current_price SET partner_id=%s 
					WHERE id=%s
					""" % (po_row['partner_id'],price_data['id']))
