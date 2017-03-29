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
		# env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))
		result = []
		# set filter pencarian voucher
		domain = {
			'supplier': supplier,
			'state': state,
			'time_range': time_range,
		}
		handler_obj = http.request.env['tbvip.website.handler']
		result.append(handler_obj.load_kontra_bon(domain))
		
		# return hasilnya
		if len(result[0]) == 0:
			response = {
				'status': 'ok',
				'info': _('The search returns no result.')
			}
		else:
			# get journals
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
			response = {
				'status': 'ok',
				'data': result,
			}
		res = json.dumps(response)
		return res
	
	@http.route('/tbvip/kontra_bon/fetch_suppliers', type='http', auth="user", website=True)
	def purchase_kontra_bon_fetch_suppliers(self, **kwargs):
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
		result = sorted(result, key=lambda supplier: supplier['name'])
		return json.dumps(result)
	
	@http.route(
		'/tbvip/kontra_bon/save/<string:id>/<string:reference>/<string:amount>/<string:journal_id>/<string:check_maturity_date>',
		type='http', auth="user", website=True)
	def purchase_kontra_bon_save(self, id, reference, amount, journal_id, check_maturity_date, **kwargs):
		result = []
		domain = {'id': id}
		if reference != "null":
			domain['reference'] = reference
		else:
			domain['reference'] = ''
		if amount != "null":
			domain['amount'] = amount
		else:
			domain['amount'] = ''
		if journal_id != "null":
			domain['journal_id'] = journal_id
		else:
			domain['journal_id'] = ''
		if check_maturity_date != "null":
			domain['check_maturity_date'] = check_maturity_date
		else:
			domain['check_maturity_date'] = ''
		handler_obj = http.request.env['tbvip.website.handler']
		result.append(handler_obj.save_kontra_bon(domain))
		
		# get journals
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
