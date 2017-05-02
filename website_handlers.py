import calendar
import csv
import os
from datetime import datetime, date, timedelta

from dateutil.relativedelta import relativedelta
from openerp.models import BaseModel
from openerp.osv import osv, fields


class tbvip_website_handler(osv.osv):
	_name = 'tbvip.website.handler'
	_description = 'Model for handling website-based requests'
	_auto = False
	
	def _format_date(self, date_string):
		if date_string:
			return datetime.strptime(date_string, '%Y-%m-%d').strftime('%d-%m-%Y')
		else:
			return '-'
	
	def _format_datetime(self, date_string):
		if date_string:
			return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y %H:%M:%S')
		else:
			return '-'
		
	# KONTRA BON ------------------------------------------------------------------------------------------------------------
	
	def load_kontra_bon(self, domain, context={}):
		args = []
	# Pool domains
		args.extend(self._kontra_bon_pool_supplier(domain))
		args.extend(self._kontra_bon_pool_state(domain))
		args.extend(self._kontra_bon_pool_date(domain))
		
		account_voucher = self.env['account.voucher']
		vouchers = account_voucher.search(args)
		result = []
		for voucher in vouchers:
			line_dr_ids = []
			included_line_counter = 0
			line_total_amount = 0
			for line_dr in voucher.line_dr_ids:
				line = {}
				line_total_amount = 0
				if line_dr.amount > 0:
					line.update({'move_line_id': line_dr.move_line_id.name})
					line.update({'date_due': self._format_date(line_dr.date_due)})
					line.update({'amount': line_dr.amount})
					line_dr_ids.append(line)
					line_total_amount += line_dr.amount
					included_line_counter += 1
		# Get bank details
			bank_acc = "-"
			bank_holder = "-"
			if len(voucher.bank_id) > 0:
				bank_acc = voucher.bank_id.acc_number
				bank_holder = voucher.bank_id.partner_id.name
			record = {
				'id': voucher.id,
				'partner_id': voucher.partner_id.name,
				'date': self._format_date(voucher.date),
				'line_dr_ids': line_dr_ids,
				'line_dr_ids_length': included_line_counter,
				'amount': voucher.amount,
				'line_total_amount': line_total_amount,
				'journal_id': voucher.journal_id.id,
				'reference': voucher.reference if voucher.reference else '',
				'check_maturity_date': voucher.check_maturity_date if voucher.check_maturity_date else '',
				'state': voucher.state,
				'bank_acc': bank_acc,
				'bank_holder': bank_holder,
			}
			result.append(record)
		return result
	
	def _kontra_bon_pool_supplier(self, domain):
		args = []
		supplier = domain.get('supplier', '').strip()
		supplier = supplier.encode('ascii', 'ignore')
		if supplier.isdigit():
			args.append(['partner_id.id', '=', supplier])
		return args
	
	def _kontra_bon_pool_state(self, domain):
		args = []
		state = domain.get('state', '').strip()
		if state == 'draft':
			args.append(['state', '=', 'draft'])
			args.append(['reference', '=', False])
		elif state == 'giro':
			args.append(['state', '=', 'draft'])
			args.append(['reference', '!=', False])
		elif state == 'posted':
			args.append(['state', '=', 'posted'])
		return args
	
	def _kontra_bon_pool_date(self, domain):
		args = []
		time_range = domain.get('time_range', '').strip()
		if time_range != '':
			date_start = ''
			date_end = date.today().strftime('%Y-%m-%d')
			if time_range == 'this_month':
				date_start = date.today().strftime('%Y-%m-01')
			elif time_range == 'last_month':
				date_start = (date.today() + relativedelta(months=-1)).strftime('%Y-%m-%d')
			elif time_range == 'last_3month':
				date_start = (date.today() + relativedelta(months=-3)).strftime('%Y-%m-%d')
			if date_start:
				args.append(['date', '>=', date_start])
			if date_end:
				args.append(['date', '<=', date_end])
		return args
	
	def save_kontra_bon(self, domain, context={}):
		account_voucher = self.env['account.voucher']
		vouchers = account_voucher.search([('id', '=', domain.get('id', ''))])
		return vouchers.write(domain)
	
# STOCK OPNAME --------------------------------------------------------------------------------------------------------------
	
	def load_stock_opname(self, domain, context={}):
		args = []
		# Pool domains
		args.extend(self._stock_opname_pool_branch(domain))
		args.extend(self._stock_opname_pool_state(domain))
		args.extend(self._stock_opname_pool_employee(domain))
		args.extend(self._stock_opname_pool_product(domain))
		
		stock_inventory_obj = self.env['stock.inventory']
		stock_inventory_datas = stock_inventory_obj.search(args)
		result = []
		for stock_inventory_data in stock_inventory_datas:
			line_ids_data = [];
			for line_data in stock_inventory_data.line_ids:
				line_id_data = {}
				line_id_data['product_name'] = line_data.product_id.name
				line_id_data['location_name'] = line_data.location_id.name
				line_id_data['product_qty'] = line_data.product_qty
				line_id_data['theoretical_qty'] = line_data.theoretical_qty
				line_id_data['product_uom_name'] = line_data.product_uom_id.name
				line_ids_data.append(line_id_data);
			record = {
				'id': stock_inventory_data.id,
				'state': stock_inventory_data.state,
				'employee_name': stock_inventory_data.employee_id.name,
				'location_name': stock_inventory_data.location_id.name,
				'date': self._format_datetime(stock_inventory_data.date),
				'line_ids': line_ids_data
			}
			result.append(record)
		return result
	
	def _stock_opname_pool_branch(self, domain):
		args = []
		location_id = domain.get('branch', '').strip()
		location_id = location_id.encode('ascii', 'ignore')
		if location_id.isdigit():
			args.append(['location_id.id', '=', location_id])
		return args
		
	def _stock_opname_pool_state(self, domain):
		args = []
		state = domain.get('state', '').strip()
		if state != 'all':
			args.append(['state', '=', state])
		return args
	
	def _stock_opname_pool_employee(self, domain):
		args = []
		employee_name = domain.get('employee', '').strip()
		if employee_name:
			args.append(['employee_id.name', 'ilike', employee_name])
		return args
	
	def _stock_opname_pool_product(self, domain):
		args = []
		product_name = domain.get('product', '').strip()
		if product_name:
			args.append(['line_ids.product_id.name', 'ilike', product_name])
		return args
	
	def create_so_inject(self, domain, context={}):
		stock_opname_inject = self.env['stock.opname.inject']
		product_obj = self.env['product.product']
		product_ids = product_obj.search([
			('name', '=ilike', domain.get('product_name', '')),
			('type', '=', 'product')
		])
		if len(product_ids) > 0:
			priority = domain.get('priority', '').strip()
			priority = priority.encode('ascii', 'ignore')
			return stock_opname_inject.create({
				'product_id': product_ids[0],
				'priority': int(priority),
			})
		else:
			return False
