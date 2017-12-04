import json

from openerp import http
from openerp.tools.translate import _
from openerp.osv import osv, fields
from openerp.http import request
from datetime import datetime, date, timedelta
from mako.lookup import TemplateLookup
from openerp.addons.web.controllers.main import serialize_exception,content_disposition
import base64

_INTERBRANCH_STATE = [
	('draft', 'Draft'),
	('accepted', 'Accepted'),
	('rejected', 'Rejected')
]

# Credits to https://tutorialopenerp.wordpress.com/2014/03/08/print-text-dot-matrix/

tpl_lookup = TemplateLookup(directories=['openerp/addons/tbvip/print_template'])

class controller_print(http.Controller):
	
	@http.route('/tbvip/print/<string:model>/<string:id>', type='http', auth="user", website=True)
	def purchase_kontra_bon(self, model, id, **kwargs):
		obj = http.request.env[model]
		data = obj.search([('id', '=', id)])
		
		if model == 'sale.order':
			data_string = self.print_sale_order(data)
		elif model == 'canvassing.canvas':
			data_string = self.print_delivery_order(data)
		elif model == 'purchase.order':
			data_string = self.print_draft_purchase_order(data)
		elif model == 'tbvip.interbranch.stock.move':
			data_string = self.print_interbranch_stock_move(data)
		elif model == 'account.voucher':
			data_string = self.print_kontra_bon(data)
		elif model == 'hr.payslip':
			data_string = self.print_payslip_dot_matrix(data)
		
		data_string = data_string.replace("\r\n", "\n").encode('utf-8')
		filecontent = base64.b64encode(data_string)
		filecontent = base64.b64decode(filecontent)
		if not filecontent:
			return request.not_found()
		else:
			filename = '%s_%s.txt' % (model.replace('.', '_'), id)
			return request.make_response(filecontent,
				[('Content-Type', 'application/octet-stream'),
					('Content-Disposition', content_disposition(filename))])
	
	def print_payslip_dot_matrix(self, payslip):
		# Mendefinisikan path dari modul report terkait
		tpl_lookup = TemplateLookup(directories=['openerp/addons/tbvip/print_template'])
		template = tpl_lookup.get_template('payslip.txt')
		
		# Prepare worked days data
		worked_days = {'masuk': 0, 'full': 0, 'full_minggu': 0}
		for worked_day in payslip.worked_days_line_ids:
			if worked_day.code == 'MASUK':
				worked_days['masuk'] = worked_day.number_of_days
			elif worked_day.code == 'FULL':
				worked_days['full'] = worked_day.number_of_days
			elif worked_day.code == 'FULL_MINGGU':
				worked_days['full_minggu'] = worked_day.number_of_days
		
		bonus = {}
		for input_line in payslip.input_line_ids:
			bonus.update({input_line.code: input_line.amount})
		
		line = {}
		for payslip_line in payslip.line_ids:
			line.update({payslip_line.code: payslip_line.total})
		
		total_bonus_point = bonus.get('POIN_XTRA_POINT', 0) \
							+ bonus.get('POIN_PENALTY_POINT', 0) \
							+ bonus.get('POIN_TOP_POINT', 0) \
							+ bonus.get('POIN_MOBIL_POINT', 0) \
							+ bonus.get('POIN_MOTOR_POINT', 0) \
							+ bonus.get('POIN_SO_POINT', 0) \
							+ bonus.get('POIN_SALES_POINT', 0) \
							+ bonus.get('POIN_ADM_POINT', 0)
		
		total_bonus_value = bonus.get('POIN_XTRA_BONUS', 0) \
							+ bonus.get('POIN_PENALTY_BONUS', 0) \
							+ bonus.get('POIN_TOP_BONUS', 0) \
							+ bonus.get('POIN_MOBIL_BONUS', 0) \
							+ bonus.get('POIN_MOTOR_BONUS', 0) \
							+ bonus.get('POIN_SO_BONUS', 0) \
							+ bonus.get('POIN_SALES_BONUS', 0) \
							+ bonus.get('POIN_ADM_BONUS', 0)
		
		payslip_print = template.render(
			print_date=str(datetime.now()),
			from_date=str(payslip.date_from),
			name=str(payslip.employee_id.name),
			masuk=str(worked_days.get('masuk', 0)),
			pokok=str(bonus.get('MASUK_BONUS_BASIC', 0)),
			full=str(worked_days.get('full', 0)),
			makan=str(bonus.get('FULL_BONUS_BASIC', 0)),
			full_minggu=str(worked_days.get('full_minggu', 0)),
			mingguan=str(bonus.get('FULL_MINGGU_BONUS_BASIC', 0)),
			total_pokok=str(line.get('BASIC', 0)),
			
			to_date=str(payslip.date_to),
			
			total_minggu=str(total_bonus_value + line.get('BASIC', 0)),
			
			potongan=str(0),
			
			point_mobil=str(bonus.get('POIN_MOBIL_POINT', 0)),
			lvl_mobil=str(bonus.get('POIN_MOBIL_LEVEL', 0)),
			bonus_mobil=str(bonus.get('POIN_MOBIL_BONUS', 0)),
			nabung=str(0),
			
			point_motor=str(bonus.get('POIN_MOTOR_POINT', 0)),
			lvl_motor=str(bonus.get('POIN_MOTOR_LEVEL', 0)),
			bonus_motor=str(bonus.get('POIN_MOTOR_BONUS', 0)),
			
			point_so=str(bonus.get('POIN_SO_POINT', 0)),
			lvl_so=str(bonus.get('POIN_SO_LEVEL', 0)),
			bonus_so=str(bonus.get('POIN_SO_BONUS', 0)),
			gaji=str(line.get('NET', 0)),
			
			point_sales=str(bonus.get('POIN_SALES_POINT', 0)),
			lvl_sales=str(bonus.get('POIN_SALES_LEVEL', 0)),
			bonus_sales=str(bonus.get('POIN_SALES_BONUS', 0)),
			
			point_adm=str(bonus.get('POIN_ADM_POINT', 0)),
			lvl_adm=str(bonus.get('POIN_ADM_LEVEL', 0)),
			bonus_adm=str(bonus.get('POIN_ADM_BONUS', 0)),
			tabungan=str(0),
			
			point_xtra=str(bonus.get('POIN_XTRA_POINT', 0)),
			lvl_xtra=str(bonus.get('POIN_XTRA_LEVEL', 0)),
			bonus_xtra=str(bonus.get('POIN_XTRA_BONUS', 0)),
			pinjaman=str(0),
			
			point_penalti=str(bonus.get('POIN_PENALTY_POINT', 0)),
			lvl_penalti=str(bonus.get('POIN_PENALTY_LEVEL', 0)),
			bonus_penalti=str(bonus.get('POIN_PENALTY_BONUS', 0)),
			level=str(bonus.get('CURRENT_LEVEL_BASIC', 0)),
			
			point_top=str(bonus.get('POIN_TOP_POINT', 0)),
			lvl_top=str(bonus.get('POIN_TOP_LEVEL', 0)),
			bonus_top=str(bonus.get('POIN_TOP_BONUS', 0)),
			total_poin=str(bonus.get('TOTAL_POINT_BASIC', 0)),
			
			total_bonus_point=str(total_bonus_point),
			total_bonus_value=str(total_bonus_value),
			target_poin=str(bonus.get('NEXT_LEVEL_POINT_BASIC', 0)),
		)
		return payslip_print
	
	def print_kontra_bon(self, acc_vou):
		tpl = tpl_lookup.get_template('kontra_bon.txt')
		tpl_line = tpl_lookup.get_template('kontra_bon_line.txt')
		
		company = acc_vou.create_uid.company_id
		company_name = company.name if company.name else ''
		branch_name = acc_vou.create_uid.branch_id.name if acc_vou.create_uid.branch_id.name else ''
		supplier_name = acc_vou.partner_id.name if acc_vou.partner_id.name else ''
		
		# add lines
		row_number = 0
		account_voucher_line = []
		for line in acc_vou.line_dr_ids:
			row_number += 1
			row = tpl_line.render(
				no=str(row_number),
				reference_number=line.move_line_id.invoice.name if line.move_line_id and line.move_line_id.invoice else '-',
				delivery_date=datetime.strptime(line.date_original, '%Y-%m-%d').strftime('%Y-%m-%d'),
				total=str(line.amount),
			)
			account_voucher_line.append(row)
		# render account voucher
		account_voucher = tpl.render(
			branch_name=branch_name,
			company_name=company_name,
			supplier_name=supplier_name,
			payment_date=datetime.strptime(acc_vou.date, '%Y-%m-%d').strftime('%Y-%m-%d'),
			lines=account_voucher_line,
			subtotal=str(acc_vou.amount),
			discount=str(0),
			total=str(acc_vou.amount),
		)
		return account_voucher
	
	
	def print_interbranch_stock_move(self, ism):
		tpl = tpl_lookup.get_template('interbranch_stock_move.txt')
		tpl_line = tpl_lookup.get_template('interbranch_stock_move_line.txt')
	
		company = ism.create_uid.company_id
		company_name = company.name if company.name else ''
		from_location = ism.from_stock_location_id.name if ism.from_stock_location_id.name else ''
		to_location = ism.to_stock_location_id.name if ism.to_stock_location_id.name else ''
		move_date = ism.move_date
		input_by = ism.input_user_id.name if ism.input_user_id.name else ''
		prepare_by = ism.prepare_employee_id.user_id.name if ism.prepare_employee_id.user_id.name else ''
		accepted_by = ism.accepted_by_user_id.user_id.name if ism.accepted_by_user_id.user_id.name else ''
		rejected_by = ism.rejected_by_user_id.user_id.name if ism.rejected_by_user_id.user_id.name else ''
		
		# add lines
		row_number = 0
		ism_line = []
		for line in ism.interbranch_stock_move_line_ids:
			row_number += 1
			row = tpl_line.render(
				no=str(row_number),
				name=str(line.product_id.name),
				qty=str(line.qty),
				uom=str(line.uom_id.name),
				is_changed='v' if line.is_changed else '',
			)
			ism_line.append(row)
		# render account voucher
		account_voucher = tpl.render(
			company_name=company_name,
			from_location=from_location,
			to_location=to_location,
			state=_(dict(_INTERBRANCH_STATE).get(ism.state,'-')),
			move_date=datetime.strptime(move_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d'),
			input_by=input_by,
			prepare_by=prepare_by,
			accepted_by=accepted_by,
			rejected_by=rejected_by,
			lines=ism_line,
		)
		return account_voucher
	
	def print_draft_purchase_order(self, dpo):
		# define template for printing
		tpl = tpl_lookup.get_template('draft_purchase_order.txt')
		tpl_line = tpl_lookup.get_template('draft_purchase_order_line.txt')
	
		branch_address = dpo.branch_id.address if dpo.branch_id.address else ''
		branch_name = dpo.branch_id.name if dpo.branch_id.name else ''
		supplier_name = dpo.partner_id.name if dpo.partner_id.name else ''
		
		# add purchase order lines
		order_line_rows = []
		for line in dpo.order_line:
			row = tpl_line.render(
				qty=str(line.product_qty),
				name=line.product_id.name,
			)
			order_line_rows.append(row)
		# render purchase order
		draft_po = tpl.render(
			date=datetime.strptime(dpo.date_order, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y'),
			branch_name=branch_name,
			branch_address=branch_address,
			supplier_name=supplier_name,
			order_lines=order_line_rows,
		)
		return draft_po
	
	def print_delivery_order(self, cvs):
		# define template for printing
		tpl = tpl_lookup.get_template('canvas.txt')
		tpl_line = tpl_lookup.get_template('canvas_line.txt')
		
		vehicle_name = cvs.fleet_vehicle_id.name if cvs.fleet_vehicle_id.name else ''
		driver_name_1 = cvs.driver1_id.name if cvs.driver1_id.name else ''
		# print for every invoices
		for inv in cvs.invoice_line_ids:
			receiver_name = inv.invoice_id.partner_id.name if inv.invoice_id.partner_id.name else ''
			receiver_address = inv.address if inv.address else ''
			account_invoice_line = []
			for acc_inv_line in inv.invoice_id.invoice_line:
				row = tpl_line.render(
					name=acc_inv_line.product_id.name,
					qty=str(acc_inv_line.quantity),
				)
				account_invoice_line.append(row)
			# render invoice
			invoice_rendered = tpl.render(
				date=datetime.strptime(cvs.date_created, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y'),
				vehicle_name=vehicle_name,
				driver_name_1=driver_name_1,
				receiver_name=receiver_name,
				receiver_address=receiver_address,
				invoice_line=account_invoice_line,
			)
		return invoice_rendered
	
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