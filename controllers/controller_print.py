
from openerp import http
from openerp.tools.translate import _
from openerp.http import request
from datetime import datetime, date, timedelta
from mako.lookup import TemplateLookup
from openerp.addons.web.controllers.main import serialize_exception,content_disposition
import base64
import os

_INTERBRANCH_STATE = [
	('draft', 'Draft'),
	('accepted', 'Accepted'),
	('rejected', 'Rejected')
]

# Credits to https://tutorialopenerp.wordpress.com/2014/03/08/print-text-dot-matrix/

basepath = ''
sep = os.sep
temp = os.path.abspath(os.path.dirname(__file__)).split(sep)
for v_slice in temp[:-1]: basepath = basepath + v_slice + sep	
tpl_lookup = TemplateLookup(directories=[basepath + 'print_template'])

class controller_print(http.Controller):
	
	@http.route('/tbvip/print/<string:model>/<string:id>', type='http', auth="user", website=True)
	def purchase_kontra_bon(self, model, id, **kwargs):
		obj = http.request.env[model]
		data = obj.search([('id', '=', id)])
		
		if model == 'sale.order':
			data_string = self.print_sale_order(data)
		elif model == 'stock.picking':
			data_string = self.print_delivery_order(data)
		elif model == 'purchase.order':
			data_string = self.print_draft_purchase_order(data)
		elif model == 'tbvip.interbranch.stock.move':
			data_string = self.print_interbranch_stock_move(data)
		elif model == 'account.voucher':
			data_string = self.print_kontra_bon(data)
		elif model == 'hr.payslip':
			data_string = self.print_payslip_dot_matrix(data)
		elif model == 'stock.inventory':
			data_string = self.print_stock_inventory(data)
		elif model == 'purchase.needs':
			data_string = self.print_purchase_needs(data)
		
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
	
	def thousand_separator(self, int_or_float):
		return "{0:,.0f}".format(int_or_float).replace(',', '.')
	
	def print_stock_inventory(self, inv_adj):
		tpl = tpl_lookup.get_template('stock_opname.txt')
		tpl_line = tpl_lookup.get_template('stock_opname_line.txt')
		
		# get inventory adjustment lines
		row_number = 0
		stock_opname_rows = []
		for line in inv_adj.line_ids:
			row_number += 1
			row = tpl_line.render(
				no=str(row_number),
				name=line.product_id.name if line.product_id.name else '',
				location=line.location_id.name if line.location_id.name else '',
				qty='' if inv_adj.state == 'draft' else self.thousand_separator(line.product_qty),
			)
			stock_opname_rows.append(row)
		# render stock opname
		stock_opname = tpl.render(
			datetime=(datetime.strptime(inv_adj.date, '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)).strftime('%d/%m/%Y %H:%M:%S'),
			expiration_datetime=datetime.strptime(inv_adj.expiration_date, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S'),
			employee_name=inv_adj.employee_id.name,
			stock_opname_line=stock_opname_rows,
		)
		return stock_opname
	
	def print_payslip_dot_matrix(self, payslip):
		# Mendefinisikan path dari modul report terkait
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
							- bonus.get('POIN_PENALTY_POINT', 0) \
							+ bonus.get('POIN_MOBIL_POINT', 0) \
							+ bonus.get('POIN_MOTOR_POINT', 0) \
							+ bonus.get('POIN_SO_POINT', 0) \
							+ bonus.get('POIN_SALES_POINT', 0) \
							+ bonus.get('POIN_ADM_POINT', 0)
		
	# bonus value hanya muncul (tidak 0) kalau point SO mencapai minimal tertentu
	# minimal ini disimpan di System Parameter hr_point.minimum_so_point 
		minimum_so_point = request.env['ir.config_parameter'].get_param('hr_point.minimum_so_point')
		minimum_so_point = float(minimum_so_point)
		if bonus.get('POIN_SO_POINT', 0) >= minimum_so_point:
			total_bonus_value = bonus.get('POIN_XTRA_BONUS', 0) \
								- bonus.get('POIN_PENALTY_BONUS', 0) \
								+ bonus.get('POIN_MOBIL_BONUS', 0) \
								+ bonus.get('POIN_MOTOR_BONUS', 0) \
								+ bonus.get('POIN_SO_BONUS', 0) \
								+ bonus.get('POIN_SALES_BONUS', 0) \
								+ bonus.get('POIN_ADM_BONUS', 0)
		else:
			total_bonus_value = 0
		
		loan = 0
		saving = 0
		loan_label = "Cicil"
		saving_label = "Tabung"
		if payslip.saving_action == 'inc':
			saving_label = "Tabung"
			saving = payslip.saving_amount
		elif payslip.saving_action == 'dec':
			saving_label = "Tarik"
			saving = -payslip.saving_amount
		if payslip.loan_action == 'inc':
			loan_label = "Pinjam"
			loan = payslip.loan_amount
		elif payslip.loan_action == 'dec':
			loan_label = "Cicil"
			loan = -payslip.loan_amount
		
		payslip_print = template.render(
			print_date=(datetime.now() + timedelta(hours=7)).strftime("%d/%m/%Y %H:%M"),
			from_date=str(payslip.date_from),
			name=str(payslip.employee_id.name),
			masuk=self.thousand_separator(worked_days.get('masuk', 0)),
			pokok=self.thousand_separator(bonus.get('MASUK_BONUS_BASIC', 0)),
			full=self.thousand_separator(worked_days.get('full', 0)),
			makan=self.thousand_separator(bonus.get('FULL_BONUS_BASIC', 0)),
			full_minggu=self.thousand_separator(worked_days.get('full_minggu', 0)),
			mingguan=self.thousand_separator(bonus.get('FULL_MINGGU_BONUS_BASIC', 0)),
			total_pokok=self.thousand_separator(line.get('BASIC', 0)),
			
			to_date=str(payslip.date_to),
			
			total_minggu=self.thousand_separator(line.get('BASIC', 0) + total_bonus_value),
			loan_label=loan_label,
			minjam=self.thousand_separator(abs(loan)),
			
			point_mobil=self.thousand_separator(bonus.get('POIN_MOBIL_POINT', 0)),
			lvl_mobil=self.thousand_separator(bonus.get('POIN_MOBIL_LEVEL', 0)),
			bonus_mobil=self.thousand_separator(bonus.get('POIN_MOBIL_BONUS', 0)),
			saving_label=saving_label,
			nabung=self.thousand_separator(abs(saving)),
			
			point_motor=self.thousand_separator(bonus.get('POIN_MOTOR_POINT', 0)),
			lvl_motor=self.thousand_separator(bonus.get('POIN_MOTOR_LEVEL', 0)),
			bonus_motor=self.thousand_separator(bonus.get('POIN_MOTOR_BONUS', 0)),
			
			point_so=self.thousand_separator(bonus.get('POIN_SO_POINT', 0)),
			lvl_so=self.thousand_separator(bonus.get('POIN_SO_LEVEL', 0)),
			bonus_so=self.thousand_separator(bonus.get('POIN_SO_BONUS', 0)),
			gaji=self.thousand_separator(line.get('BASIC', 0) + total_bonus_value - saving + loan),
			
			point_sales=self.thousand_separator(bonus.get('POIN_SALES_POINT', 0)),
			lvl_sales=self.thousand_separator(bonus.get('POIN_SALES_LEVEL', 0)),
			bonus_sales=self.thousand_separator(bonus.get('POIN_SALES_BONUS', 0)),
			
			point_adm=self.thousand_separator(bonus.get('POIN_ADM_POINT', 0)),
			lvl_adm=self.thousand_separator(bonus.get('POIN_ADM_LEVEL', 0)),
			bonus_adm=self.thousand_separator(bonus.get('POIN_ADM_BONUS', 0)),
			tabungan=self.thousand_separator(payslip.current_saving + saving),
			
			point_xtra=self.thousand_separator(bonus.get('POIN_XTRA_POINT', 0)),
			lvl_xtra=self.thousand_separator(bonus.get('POIN_XTRA_LEVEL', 0)),
			bonus_xtra=self.thousand_separator(bonus.get('POIN_XTRA_BONUS', 0)),
			pinjaman=self.thousand_separator(payslip.current_loan + loan),
			
			point_penalti=self.thousand_separator(bonus.get('POIN_PENALTY_POINT', 0)),
			lvl_penalti=self.thousand_separator(bonus.get('POIN_PENALTY_LEVEL', 0)),
			bonus_penalti=self.thousand_separator(bonus.get('POIN_PENALTY_BONUS', 0)),
			level=self.thousand_separator(bonus.get('CURRENT_LEVEL_BASIC', 0)),
			
			total_poin=self.thousand_separator(bonus.get('TOTAL_POINT_BASIC', 0)),
			
			total_bonus_point=self.thousand_separator(total_bonus_point),
			total_bonus_value=self.thousand_separator(total_bonus_value),
			target_poin=self.thousand_separator(bonus.get('NEXT_LEVEL_POINT_BASIC', 0)),
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
			if line.amount <= 0: continue
			row_number += 1
			row = tpl_line.render(
				no=str(row_number),
				reference_number=line.move_line_id.invoice.name if line.move_line_id and line.move_line_id.invoice else '-',
				delivery_date=datetime.strptime(line.date_original, '%Y-%m-%d').strftime('%Y-%m-%d'),
				total=self.thousand_separator(line.amount),
			)
			account_voucher_line.append(row)
		# render account voucher
		account_voucher = tpl.render(
			branch_name=branch_name,
			company_name=company_name,
			supplier_name=supplier_name,
			payment_date=datetime.strptime(acc_vou.check_maturity_date, '%Y-%m-%d').strftime('%Y-%m-%d'),
			lines=account_voucher_line,
			subtotal=self.thousand_separator(acc_vou.amount),
			discount=self.thousand_separator(0),
			total=self.thousand_separator(acc_vou.amount),
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
		accepted_by = ism.accepted_by_user_id.name if ism.accepted_by_user_id.name else ''
		rejected_by = ism.rejected_by_user_id.name if ism.rejected_by_user_id.name else ''
		
		# add lines
		row_number = 0
		ism_line = []
		for line in ism.interbranch_stock_move_line_ids:
			row_number += 1
			row = tpl_line.render(
				no=str(row_number),
				name=str(line.product_id.name) if line.product_id.name else '',
				qty=self.thousand_separator(line.qty),
				uom=str(line.uom_id.name) if line.uom_id.name else '',
				is_changed='v' if line.is_changed else '',
			)
			ism_line.append(row)
		# render account voucher
		account_voucher = tpl.render(
			company_name=company_name,
			from_location=from_location,
			to_location=to_location,
			state=_(dict(_INTERBRANCH_STATE).get(ism.state,'-')),
			move_date=(datetime.strptime(move_date, '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)).strftime('%Y-%m-%d'),
			input_by=input_by,
			prepare_by=prepare_by,
			is_draft=ism.state == 'draft',
			accepted_or_rejected=_(dict(_INTERBRANCH_STATE).get(ism.state,'')) + ' by' if ism.state != 'draft' else '',
			accepted_or_rejected_by=accepted_by if ism.state == 'accepted' else rejected_by,
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
				qty=self.thousand_separator(line.product_qty),
				name=line.product_id.name,
				uom=line.product_uom.name,
			)
			order_line_rows.append(row)
		# render purchase order
		draft_po = tpl.render(
			date=(datetime.strptime(dpo.date_order, '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)).strftime('%d/%m/%Y'),
			branch_name=branch_name,
			branch_address=branch_address,
			supplier_name=supplier_name,
			order_lines=order_line_rows,
		)
		return draft_po
	
	def print_purchase_needs(self, purchase_needs):
		# define template for printing
		tpl = tpl_lookup.get_template('purchase_needs.txt')
		tpl_line = tpl_lookup.get_template('purchase_needs_line.txt')

		supplier_name = purchase_needs.supplier_id.name if purchase_needs.supplier_id.name else ''
		# add purchase order lines
		ordered_needs_rows = []
		purchase_needs_draft_rows = []
		for line in purchase_needs.draft_needs_ids:
			ordered_needs_rows.append({
				'qty': self.thousand_separator(line.product_qty),
				'name': line.product_id.name,
				'branch_name': line.branch_id.name if line.branch_id.name else '',
			})
		sorted(ordered_needs_rows, key=lambda r: r['branch_name'])
		for need_row in ordered_needs_rows:
			row = tpl_line.render(
				qty=need_row['qty'],
				name=need_row['name'],
				branch_name=need_row['branch_name'],
			)
			purchase_needs_draft_rows.append(row)
		# render purchase order
		draft_po = tpl.render(
			date=(datetime.now()).strftime('%d/%m/%Y %H:%M:%S'),
			#date=(datetime.now() + timedelta(hours=7)).strftime('%d/%m/%Y %H:%M:%S'),
			supplier_name=supplier_name,
			lines=purchase_needs_draft_rows,
		)
		return draft_po
	
	def print_delivery_order(self, stock_picking):
		# define template for printing
		tpl = tpl_lookup.get_template('stock_picking.txt')
		tpl_line = tpl_lookup.get_template('stock_picking_line.txt')
		
		receiver_name = stock_picking.partner_id.name if stock_picking.partner_id.name else ''
		receiver_address = stock_picking.partner_id.street if stock_picking.partner_id.street else ''
		# print for every stock move
		move_lines = []
		for stock_move in stock_picking.move_lines:
			row = tpl_line.render(
				name=stock_move.product_id.name,
				qty=self.thousand_separator(stock_move.product_uom_qty),
			)
			move_lines.append(row)
		# render stock_picking
		stock_picking_rendered = tpl.render(
			date=datetime.today().strftime('%Y-%m-%d'),
			receiver_name=receiver_name,
			receiver_address=receiver_address,
			move_lines=move_lines,
		)
		return stock_picking_rendered
	
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
				qty=self.thousand_separator(line.product_uom_qty),
				uom=line.product_uom.name,
				name=line.product_id.name,
				unit_price=self.thousand_separator(line.price_unit),
				discount=line.discount_string if line.discount_string else "",
				subtotal=self.thousand_separator(line.price_subtotal),
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
			
			date=(datetime.strptime(so.date_order, '%Y-%m-%d %H:%M:%S') + timedelta(hours=7)).strftime('%d/%m/%Y'),
			customer_name=customer_name,
			customer_address=customer_address,
			
			order_lines=order_line_rows,
			discount_total=self.thousand_separator(so.total_discount_amount),
			total=self.thousand_separator(so.amount_total),
		)
		return sale_order