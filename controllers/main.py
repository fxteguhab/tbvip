import json

from openerp import http
from openerp.http import request
from openerp.tools.translate import _

# TIMTBVIP: All Done
# - untuk pilihan supplier tolong ditambahin "[All Suppliers]" yang mana tidak memfilter kontra bon
# berdasarkan supplier tertentu DONE
# - judul (di tab browser) untuk kontra bon masih "List with Filter", tolong ganti jadi Kontra Bon DONE
# - tampilan angka tolong pakai pemisah ribuan. di JS udah ada function buat memformat itu, mungkin
# bisa dipake DONE
# - format tanggal DD/MM/YYYY DONE
# - Nilai yang ditampilkan di list invoice adalah Amount bukan Original Amount, demikian juga total yayng di kepala accordion nya DONE
# - di detail payment tampilkan hanya invoice yang Amount-nya > 0 DONE
# - sebelum manggil kontra_bon_fetch_data, kosongkan dulu div yang buat nampilin data. hal ini supaya 
# ketika search tidak mengembalikan apa2 jangan sampe masih ada data sisa search sebelumnya DONE
# - di list invoice, bila Due kosong keluarnya jangan "false" tapi "-" (strip) aja DONE

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
		# set filter pencarian voucher
		domain = {
			'supplier': supplier,
			'state': state,
			'time_range': time_range,
		}
		handler_obj = env['tbvip.website.handler']
		result = handler_obj.load_kontra_bon(env, domain)
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
		return json.dumps(response)
	
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
		list_id = [];
		for record in account_vouchers.search([]):
			id = str(record.partner_id.id)
			name = record.partner_id.name
			if id not in list_id:
				list_id.append(id);
				result.append({
					'id': id,
					'name': name,
				});
		return json.dumps(result)
