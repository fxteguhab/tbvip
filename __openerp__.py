{
	'name': 'TB VIP Bandung',
	'version': '0.1',
	'category': 'Sales Management',
	'description': """
		Custom implementation for Toko Besi VIP Bandung
	""",
	'author': 'Christyan Juniady and Associates',
	'maintainer': 'Christyan Juniady and Associates',
	'website': 'http://www.chjs.biz',
	'depends': [
		"base", "board", "web", "website",
		"purchase_needs", "chjs_custom_view", "chjs_price_list",
		"account_accountant", "account_cancel", "stock", "sale", "purchase", "fleet", "hr", "hr_attendance", "hr_expense",
		"purchase_sale_discount", "stock_opname", "account_receivable_limit",
		"sale_multiple_payment", "canvassing", "hr_point_payroll", "product_custom_conversion", "product_production",
		"account_simplified_journal"
	],
	'sequence': 150,
	'data': [
		'report/account_report.xml',
		'report/documents/stock_inventory.xml',
		'report/documents/account_voucher.xml',
		'report/documents/stock_inventory.xml',
		'report/documents/sale_receipt.xml',
		'report/purchase_report.xml',
		'report/sale_report.xml',
		'security/ir_rule.xml',
		'security/tbvip_security.xml',
		'cron/tbvip_cron.xml',
		'data/product_data.xml',
		'data/account_data.xml',
		'data/fleet_data.xml',
		'data/tbvip_data.xml',
		'data/stock_data.xml',
		'menu/bon_menu.xml',
		'menu/commission_menu.xml',
		'menu/demand_menu.xml',
		'menu/product_menu.xml',
		'menu/tbvip_menu.xml',
		'menu/purchase_menu.xml',
		'menu/purchase_needs_menu.xml',
		'menu/stock_menu.xml',
		'menu/stock_opname_menu.xml',
		'menu/sale_menu.xml',
		'menu/koreksi_bon_menu.xml',
		'menu/account_voucher_menu.xml',
		'menu/tbvip_stock_move_menu.xml',
		'views/account_invoice_view.xml',
		'views/account_view.xml',
		'views/account_voucher_view.xml',
		'views/bon_view.xml',
		'views/commission_view.xml',
		'views/conversion_view.xml',
		'views/demand_view.xml',
		'views/employee_view.xml',
		'views/hr_view.xml',
		'views/product_view.xml',
		'views/product_production_view.xml',
		'views/purchase_needs_view.xml',
		'views/purchase_view.xml',
		'views/sale_view.xml',
		'views/stock_view.xml',
		'views/tbvip.xml',
		'views/res_users_view.xml',
		'views/res_partner_view.xml',
		'views/stock_opname_view.xml',
		'views/fleet_view.xml',
		'views/canvassing_view.xml',
		'views/chjs_price_list_view.xml',
		'views/sale_order_return_view.xml',
		'views/koreksi_bon_view.xml',
		'views/res_config_view.xml',
		'views/tbvip_stock_move_view.xml',
		'workflows/purchase_workflow.xml',
		'menu/accounting_menu.xml',
		# 'menu/account_receivable_limit.xml',
		'security/ir.model.access.csv',
		'security/tbvip_hidden.xml',
	],
	'demo': [
	],
	'test': [
	],
	'installable': True,
	'auto_install': False,
	'qweb': [
	]
}
