import re



from openerp.tools.translate import _


class InvalidDiscountException(Exception):
	pass


def validate_discount_string(discount_string, price, max_discount):
# If discount_string is empty, return it as valid
	if not discount_string:
		return ''
	discount_string_nospace = discount_string.replace(" ", "")
	discounted_price = price
	if not re.match('^[\d\%\.\+\-]+$', discount_string_nospace):
		raise InvalidDiscountException(_("Discount format mismatch: %s") % discount_string_nospace)
	discounts = discount_string_nospace.split("+")
	if len(discounts) > max_discount:  # discounts more than maximum
		raise InvalidDiscountException(_("Discount limit exceeded: %s, maximum: %s.") % (len(discounts),max_discount))
	for discount in discounts:
		if "%" in discount:
			if discount.index("%") != len(discount) - 1:  # there's something between % and +
				raise InvalidDiscountException(_("Invalid percentage format: %s") % discount)
			try:
				number = float(discount[:-1])
			except:
				raise InvalidDiscountException(_("Discount format mismatch: %s") % discount_string_nospace)
			if number < -100.0 or number > 100.0:  # number not 0-100 %, but discount still valid if > (-100%) ex: -90%
				raise InvalidDiscountException(_("Percentage discount value is larger than 1: %s") % discount)
			discounted_price -= (price * number) / 100.00
		else:
			if len(discount) > 0:
				try:
					discounted_price -= float(discount)
				except:
					raise InvalidDiscountException(_("Discount format mismatch: %s") % discount_string_nospace)
		if discounted_price < 0:
			raise InvalidDiscountException(_("Discounted price is smaller than zero: %s") % discounted_price)
	return discount_string_nospace  # valid


def calculate_discount(discount_string, price, max_discount):
	result = [0, 0, 0, 0, 0, 0, 0, 0]
	if not discount_string:
		return result
	discounts = discount_string.split("+")
	counter = max_discount
	for discount in discounts:
		value = 0
		if not counter:
			break
		if "%" in discount:
			try:
				value = (price * (float(discount[:-1]))) / 100.00
			except:
				raise InvalidDiscountException(_("Discount format mismatch: %s") % discount_string)
		else:
			if len(discount) > 0:
				try:
					value = float(discount)
				except:
					raise InvalidDiscountException(_("Discount format mismatch: %s") % discount_string)
		price -= value
		result[len(result) - counter] = value
		counter -= 1
	return result
