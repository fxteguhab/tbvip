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
		"chjs_custom_view",
		"account_accountant", "account_cancel", "stock", "sale", "purchase", "fleet", "hr",
		"purchase_needs", "purchase_sale_discount", "stock_opname",  "account_receivable_limit",
		"sale_direct_cash"
	],
	'sequence': 150,
	'data': [
		'security/tbvip_security.xml',
		'cron/tbvip_cron.xml',
		'data/product_data.xml',
		'data/account_data.xml',
		'data/fleet_data.xml',
		'data/tbvip_data.xml',
		'data/stock_data.xml',
		'menu/bon_menu.xml',
		'menu/demand_menu.xml',
		'menu/tbvip_menu.xml',
		'menu/purchase_menu.xml',
		'menu/stock_menu.xml',
		'views/account_invoice_view.xml',
		'views/account_view.xml',
		'views/account_voucher_view.xml',
		'views/bon_view.xml',
		'views/demand_view.xml',
		'views/employee_view.xml',
		'views/product_view.xml',
		'views/purchase_view.xml',
		'views/purchase_needs_view.xml',
		'views/sale_view.xml',
		'views/stock_view.xml',
		'views/tbvip.xml',
		'views/res_users_view.xml',
		'views/stock_opname_view.xml'
		'report/account_report.xml',
		'report/documents/account_voucher.xml',
		'report/purchase_report.xml',
		'workflows/purchase_workflow.xml',
		'security/ir_rule.xml',
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
