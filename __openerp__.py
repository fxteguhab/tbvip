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
		"account_accountant", "stock", "sale", "purchase", "fleet", "hr",
		"purchase_needs", "purchase_sale_discount",
	],
	'sequence': 150,
	'data': [
		'cron/tbvip_cron.xml',
		'data/product_data.xml',
		'data/account_data.xml',
		'data/fleet_data.xml',
		'data/tbvip_data.xml',
		'views/account_invoice_view.xml',
		'views/account_voucher_view.xml',
		'views/employee_view.xml',
		'views/product_view.xml',
		'views/purchase_view.xml',
		'views/purchase_needs_view.xml',
		'views/tbvip.xml',
		'report/account_report.xml',
		'report/documents/account_voucher.xml',
		'report/purchase_report.xml',
		'menu/tbvip_menu.xml',
		'menu/purchase_menu.xml',
		'workflows/invoice_workflow.xml',
		'workflows/purchase_workflow.xml',
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
