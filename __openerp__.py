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
		"base","board","web",
		"chjs_custom_view",
		"account_accountant","stock","sale","purchase",
	],
	'sequence': 150,
	'data': [
		'cron/tbvip.xml',
		'data/product.xml',
		'views/product.xml',
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
