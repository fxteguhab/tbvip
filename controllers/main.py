import json

from openerp import http
from openerp.http import request
from openerp.tools.translate import _


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
