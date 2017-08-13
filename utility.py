import re

def update_uom_domain(onchange_result):
	if not onchange_result:
		onchange_result = {}
	if onchange_result.get('domain', False):
		if onchange_result['domain'].get('uom_id_1', False):
			onchange_result['domain']['uom_id_1'].append(('is_auto_create', '=', False))
			onchange_result['domain']['uom_id_2'].append(('is_auto_create', '=', False))
			onchange_result['domain']['uom_id_3'].append(('is_auto_create', '=', False))
			onchange_result['domain']['uom_id_4'].append(('is_auto_create', '=', False))
			onchange_result['domain']['uom_id_5'].append(('is_auto_create', '=', False))
		else:
			onchange_result['domain']['uom_id_1'] = [('is_auto_create', '=', False)]
			onchange_result['domain']['uom_id_2'] = [('is_auto_create', '=', False)]
			onchange_result['domain']['uom_id_3'] = [('is_auto_create', '=', False)]
			onchange_result['domain']['uom_id_4'] = [('is_auto_create', '=', False)]
			onchange_result['domain']['uom_id_5'] = [('is_auto_create', '=', False)]
	else:
		onchange_result.update({'domain': {'uom_id_1': [('is_auto_create', '=', False)],
			'uom_id_2': [('is_auto_create', '=', False)],
			'uom_id_3': [('is_auto_create', '=', False)],
			'uom_id_4': [('is_auto_create', '=', False)],
			'uom_id_5': [('is_auto_create', '=', False)]}})
	return onchange_result