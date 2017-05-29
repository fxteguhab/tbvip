import re



from openerp.tools.translate import _


class InvalidCommissionException(Exception):
	pass


def validate_commission_string(commission_string, price):
# If commission_string is empty, return it as valid
	if not commission_string:
		return ''
	commission_string_nospace = commission_string.replace(" ", "")
	commissioned_price = price
	if not re.match('^[\d\%\.\+\-]+$', commission_string_nospace):
		raise InvalidCommissionException(_("Commission format mismatch: %s") % commission_string_nospace)
	commissions = commission_string_nospace.split("+")
	for commission in commissions:
		if "%" in commission:
			if commission.index("%") != len(commission) - 1:  # there's something between % and +
				raise InvalidCommissionException(_("Invalid percentage format: %s") % commission)
			try:
				number = float(commission[:-1])
			except:
				raise InvalidCommissionException(_("Commission format mismatch: %s") % commission_string_nospace)
			if number < -100.0 or number > 100.0:  # number not 0-100 %, but commission still valid if > (-100%) ex: -90%
				raise InvalidCommissionException(_("Percentage commission value is larger than 1: %s") % commission)
			commissioned_price -= (price * number) / 100.00
		else:
			if len(commission) > 0:
				try:
					commissioned_price -= float(commission)
				except:
					raise InvalidCommissionException(_("Commission format mismatch: %s") % commission_string_nospace)
		if commissioned_price < 0:
			raise InvalidCommissionException(_("Commissioned price is smaller than zero: %s") % commissioned_price)
	return commission_string_nospace  # valid


def calculate_commission(commission_string, price):
	if not commission_string:
		return 0
	commissions = commission_string.split("+")
	commission_result = 0
	for commission in commissions:
		value = 0
		if "%" in commission:
			try:
				value = (price * (float(commission[:-1]))) / 100.00
			except:
				raise InvalidCommissionException(_("Commission format mismatch: %s") % commission_string)
		else:
			if len(commission) > 0:
				try:
					value = float(commission)
				except:
					raise InvalidCommissionException(_("Commission format mismatch: %s") % commission_string)
		price -= value
		commission_result += value
	return commission_result