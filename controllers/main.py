import json

from openerp import http
from openerp.http import request
from openerp.tools.translate import _

class website_tbvip(http.Controller):
	
# KONTRA BON ----------------------------------------------------------------------------------------------------------------

	@http.route('/tbvip/kontra_bon', type='http', auth="user", website=True)
	def purchase_kontra_bon(self, **kwargs):
		env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))
		uid = env.uid
		return request.render("tbvip.website_tbvip_list_with_filter", {
			'page_title': 'Kontra Bon',
			'container_id': 'kontra_bon_wrap',
		})
	
	@http.route('/tbvip/kontra_bon/fetch_data/<string:filters>', type='http',
		auth="user", website=True)
	def purchase_kontra_bon_fetch_list(self, filters, **kwargs):
		filters = json.loads(filters)
		supplier = filters.get('supplier', None)
		state = filters.get('state', None)
		time_range = filters.get('time_range', None)
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
	
	@http.route('/tbvip/kontra_bon/save/<string:data>', type='http', auth="user", website=True)
	def purchase_kontra_bon_save(self, data, **kwargs):
		handler_obj = http.request.env['tbvip.website.handler']
		result = handler_obj.save_kontra_bon(json.loads(data))
		if result:
			response = {
				'status': 'ok',
				'info': _('Save Success'),
				'success' : True,
			}
		else:
			response = {
				'status': 'ok',
				'info': _('Save Failed'),
				'success' : False,
			}
		return json.dumps(response)


# STOCK OPNAME INJECT -------------------------------------------------------------------------------------------------------

	@http.route('/tbvip/stock_opname', type='http', auth="user", website=True)
	def stock_opname_inject(self, **kwargs):
		env = request.env(context=dict(request.env.context, show_address=True, no_tag_br=True))
		uid = env.uid
		return request.render("tbvip.website_tbvip_stock_opname", {
			'so_inject_title': 'Stock Opname Inject',
			'so_title': 'Stock Opname',
			'container_id': 'stock_opname_wrap',
		})

	@http.route('/tbvip/stock_opname/fetch_branches', type='http', auth="user", website=True)
	def stock_opname_fetch_branches(self, **kwargs):
		tbvip_branch = http.request.env['tbvip.branch']
		result = []
		for record in tbvip_branch.search([]):
			result.append({
				'id': record.id,
				'name': record.name,
			})
		result = sorted(result, key=lambda branch: branch['name'])
		return json.dumps(result)

	@http.route('/tbvip/stock_opname/fetch_data/<string:filters>', type='http',
		auth="user", website=True)
	def stock_opname_fetch_data(self, filters, **kwargs):
		filters = json.loads(filters)
		branch = filters.get('branch', None)
		state = filters.get('state', None)
		employee = filters.get('employee', None)
		product = filters.get('product', None)
	# set filter pencarian voucher
		domain = {
			'branch': branch,
			'state': state,
			'employee': employee,
			'product': product,
		}
		handler_obj = http.request.env['tbvip.website.handler']
		result = handler_obj.load_stock_opname(domain)
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

	@http.route('/tbvip/stock_opname/fetch_so_inject', type='http', auth="user", website=True)
	def stock_opname_fetch_so_inject(self, **kwargs):
		stock_opname_inject = http.request.env['stock.opname.inject']
		result = []
		for record in stock_opname_inject.search([]):
			result.append({
				'product_name': record.product_id.name,
				'priority': record.priority,
			})
		result = sorted(result, key=lambda branch: branch['priority'])
		return json.dumps(result)

	@http.route('/tbvip/stock_opname/create_so_inject/<string:data>', type='http', auth="user", website=True)
	def stock_opname_so_inject_create(self, data, **kwargs):
		handler_obj = http.request.env['tbvip.website.handler']
		result = handler_obj.create_so_inject(json.loads(data))
		if result:
			response = {
				'status': 'ok',
				'info': _('Save Success'),
				'success' : True,
			}
		else:
			response = {
				'status': 'ok',
				'info': _('Save Failed. No product with that name exist'),
				'success' : False,
			}
		return json.dumps(response)