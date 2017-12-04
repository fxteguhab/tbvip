import json

from openerp import http
from openerp.http import request
from datetime import datetime, date, timedelta
from mako.lookup import TemplateLookup
from openerp.addons.web.controllers.main import serialize_exception,content_disposition
import base64

tpl_lookup = TemplateLookup(directories=['openerp/addons/tbvip/print_template'])

class controller_print(http.Controller):
	
	@http.route('/tbvip/print/<string:model>/<string:id>', type='http', auth="user", website=True)
	def purchase_kontra_bon(self, model, id, **kwargs):
		# path_file = 'openerp/addons/tbvip/tmp/'
		obj = http.request.env[model]
		data = obj.search([('id', '=', id)])
		
		if model == 'sale.order':
			data_string = self.print_sale_order(data)
			# filename = path_file + 'print_sale_order_' + datetime.now().strftime('%Y-%m-%d_%H%M%S') + '.txt'
			# f = open(filename, 'w')
			# f.write(data_string.encode('utf-8').strip())
		
		data_string = data_string.replace("\r\n", "\n").encode('utf-8')
		missing_padding = len(data_string) % 4
		if missing_padding != 0:
			data_string += b'='* (4 - missing_padding)
			
		filecontent = base64.b64encode(data_string)
		if not filecontent:
			return request.not_found()
		else:
			filename = '%s_%s.txt' % (model.replace('.', '_'), id)
			return request.make_response(filecontent,
				[('Content-Type', 'application/octet-stream'),
					('Content-Disposition', content_disposition(filename))])
		# f.close()
		# return f
	
	def print_sale_order(self, so):
		tpl = tpl_lookup.get_template('sale_order.txt')
		tpl_line = tpl_lookup.get_template('sale_order_line.txt')
		
		company = so.create_uid.company_id
		company_name = company.name if company.name else ''
		company_address = so.branch_id.address if so.branch_id.address else ''
		company_city = company.city if company.city else ''
		company_phone = company.phone if company.phone else ''
		branch_name = so.branch_id.name if so.branch_id.name else ''
		customer_name = so.partner_id.name if so.partner_id.name else ''
		customer_address = so.partner_id.street if so.partner_id.street else ''
		
		# add sale order lines
		row_number = 0
		order_line_rows = []
		for line in so.order_line:
			row_number += 1
			row = tpl_line.render(
				no=str(row_number),
				qty=str(line.product_uom_qty),
				uom=line.product_uom.name,
				name=line.product_id.name,
				unit_price=str(line.price_unit),
				discount=line.discount_string if line.discount_string else "",
				subtotal=str(line.price_subtotal),
			)
			order_line_rows.append(row)
		# add blank rows
		while row_number < 15:
			row_number += 1
			row = tpl_line.render(
				no=str(row_number),
				qty='',
				uom='',
				name='',
				unit_price='',
				discount='',
				subtotal='',
			)
			order_line_rows.append(row)
		# render sale order
		sale_order = tpl.render(
			branch_name=branch_name,
			company_name=company_name,
			company_address=company_address,
			company_city=company_city,
			company_phone=company_phone,
			bon_number=so.bon_number,
			
			date=datetime.strptime(so.date_order, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y'),
			customer_name=customer_name,
			customer_address=customer_address,
			
			order_lines=order_line_rows,
			discount_total=str(so.total_discount_amount),
			total=str(so.amount_total),
		)
		return sale_order