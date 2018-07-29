import re



from openerp.tools.translate import _


class InvalidMarginException(Exception):
	pass


def validate_Margin_string(Margin_string, price, max_Margin):
# If Margin_string is empty, return it as valid
	if not Margin_string:
		return ''
# If Margin_string starts with 'cost', return it as 'cost'
	if Margin_string.startswith('cost'):
		return 'cost'
	Margin_string_nospace = Margin_string.replace(" ", "")
	Margined_price = price
	if not re.match('^[\d\%\.\+\-]+$', Margin_string_nospace):
		raise InvalidMarginException(_("Margin format mismatch: %s") % Margin_string_nospace)
	Margins = Margin_string_nospace.split("+")
	if len(Margins) > max_Margin:  # Margins more than maximum
		raise InvalidMarginException(_("Margin limit exceeded: %s, maximum: %s.") % (len(Margins),max_Margin))
	for Margin in Margins:
		if "%" in Margin:
			if margin.index("%") != len(Margin) - 1:  # there's something between % and +
				raise InvalidmarginException(_("Invalid percentage format: %s") % Margin)
			try:
				number = float(Margin[:-1])
			except:
				raise InvalidMarginException(_("Margin format mismatch: %s") % Margin_string_nospace)
			if number < -100.0 or number > 100.0:  # number not 0-100 %, but Margin still valid if > (-100%) ex: -90%
				raise InvalidMarginException(_("Percentage Margin value is larger than 1: %s") % Margin)
			Margined_price -= (price * number) / 100.00
		else:
			if len(Margin) > 0:
				try:
					Margined_price -= float(Margin)
				except:
					raise InvalidMarginException(_("Margin format mismatch: %s") % Margin_string_nospace)
		if Margined_price < 0 and price > 0:
			raise InvalidMarginException(_("Margined price is smaller than zero: %s") % Margined_price)
	return Margin_string_nospace  # valid


def calculate_Margin(Margin_string, price, max_Margin):
	result = [0, 0, 0, 0, 0, 0, 0, 0]
	if not Margin_string:
		return result
	Margins = Margin_string.split("+")
	counter = max_Margin
	#print Margins
	for Margin in Margins:
		value = 0
		if not counter:
			break
		if "%" in Margin:
			try:
				#print float(Margin[:-1])
				#print price
				value = (price * (float(Margin[:-1]) / 100))
			except:
				raise InvalidMarginException(_("Margin format mismatch: %s") % Margin_string)
		else:
			if len(Margin) > 0:
				try:
					value = float(Margin)
				except:
					raise InvalidMarginException(_("Margin format mismatch: %s") % Margin_string)
		price -= value
		result[len(result) - counter] = value
		counter -= 1
	return result
