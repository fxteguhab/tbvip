import json

from openerp import http
from openerp.http import request
from openerp.tools.translate import _

# JUNED: numpang nulis di sini karena di XML ngga bisa. ini semua terkait tampilan modul website kontra bon:
# - untuk pilihan supplier tolong ditambahin "[All Suppliers]" yang mana tidak memfilter kontra bon
# berdasarkan supplier tertentu
# - judul (di tab browser) untuk kontra bon masih "List with Filter", tolong ganti jadi Kontra Bon
# - tampilan angka tolong pakai pemisah ribuan. di JS udah ada function buat memformat itu, mungkin
# bisa dipake
# - format tanggal DD/MM/YYYY
# - Nilai yang ditampilkan di list invoice adalah Amount bukan Original Amount, demikian juga total yayng di kepala accordion nya
# - di detail payment tampilkan hanya invoice yang Amount-nya > 0
# - sebelum manggil kontra_bon_fetch_data, kosongkan dulu div yang buat nampilin data. hal ini supaya 
# ketika search tidak mengembalikan apa2 jangan sampe masih ada data sisa search sebelumnya
# - di list invoice, bila Due kosong keluarnya jangan "false" tapi "-" (strip) aja

class website_tbvip(http.Controller):
	@http.route('/tbvip/kontra_bon', type='http', auth="user", website=True)
	def purchase_kontra_bon(self, **kwargs):
		env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))
		uid = env.uid
		return request.render("tbvip.website_tbvip_list_with_filter", {
			'page_title': 'Kontra Bon',
			'container_id': 'kontra_bon_wrap',
		})
	
	@http.route('/tbvip/kontra_bon/fetch_data/<string:supplier>/<string:state>/<string:time_range>', type='http',
				auth="user", website=True)
	def purchase_kontra_bon_fetch_list(self, supplier, state, time_range, **kwargs):
		env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))
		result = []
		# set filter pencarian voucher
		domain = {
			'supplier': supplier,
			'state': state,
			'time_range': time_range,
		}
		handler_obj = env['tbvip.website.handler']
		result.append(handler_obj.load_kontra_bon(env, domain))
		
		#get journals
		account_journals = http.request.env['account.journal']
		result_journal = []
		list_id_journal = [];
		for record in account_journals.search([('type', '=', 'bank')]):
			id = str(record.id)
			name = record.name
			if id not in list_id_journal:
				list_id_journal.append(id);
				result_journal.append({
					'id': id,
					'name': name,
				});
		result.append(result_journal)
		
		# return hasilnya
		if len(result) == 0:
			response = {
				'status': 'ok',
				'info': _('The search returns no result.')
			}
		else:
			response = {
				'status': 'ok',
				'data': result,
			}
		res = json.dumps(response)
		return res
	
	@http.route('/tbvip/kontra_bon/fetch_suppliers', type='http', auth="user", website=True)
	def purchase_kontra_bon_fetch_suppliers(self, **kwargs):
	# TIMTBVIP: sudah diubah caranya
	# ada pendekatan yang jauh lebih baik daripada meng-concat string pakai , [ ] ; dsb.
	# idenya, kamu bikin list seperti biasa (dalam hal ini list of dict {id, name})
	# lalu dengan mudahnya tinggal panggil json.dumps() dan tada! kamu langsung punya JSON string
	# https://docs.python.org/2/library/json.html
	# tolong ini diganti dan di-note buat ke depannya
		account_vouchers = http.request.env['account.voucher']
		result = [];
		list_id_supplier = [];
		for record in account_vouchers.search([]):
			id = str(record.partner_id.id)
			name = record.partner_id.name
			if id not in list_id_supplier:
				list_id_supplier.append(id);
				result.append({
					'id': id,
					'name': name,
				});
		return json.dumps(result)