from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

# ==========================================================================================================================

class account_invoice(models.Model):
	_inherit = 'account.invoice'
	
	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	
	discount_amount = fields.Float(string='Discount') # JUNED: ini mending ke purchase_sales_discount deh 
	check_maturity_date = fields.Date(string='Check Maturity Date',
		readonly=True, states={'draft': [('readonly', False)]}) # JUNED: maaf salah tulis di 004, seharusnya ini ada di account.voucher bukan account.invoice. tolong pindahkan beserta definisi field ini di viewnya
	
	# OVERRIDES -------------------------------------------------------------------------------------------------------------
	
	@api.one
	@api.depends('discount_amount')
	def _compute_amount(self): # JUNED: ini juga ke purchase_sales_discount
		super(account_invoice, self)._compute_amount()
		if self.amount_total:
			if self.amount_total - self.discount_amount < 0:
				raise except_orm(_('Warning!'), _('Total amount after discount should not be less than zero.'))
			else:
				self.amount_total -= self.discount_amount
		else:
			self.discount_amount = 0
			
# ==========================================================================================================================


class account_invoice_line(models.Model): # JUNED: ini juga ke purchase_sales_line
	_inherit = 'account.invoice.line'
	
	# METHODS ---------------------------------------------------------------------------------------------------------------
	
	@api.depends('price_unit', 'discount_amount_line')
	def _compute_discount_amount_line_percentage(self):
		"""
		Final price for each line is computed with the equation (self.price_unit*(1-(self.discount or 0.0)/100.0)).
		To make use the discount field, the discount_amount_line will be converted into percentage, so that the subtotal
		of each line will be updated as expected when there's a change in the field.
		"""
		for record in self:
			if(record.price_unit != 0):
				record.discount = (record.discount_amount_line / record.price_unit) * 100.0
			else:
				record.discount = 0.0

	# COLUMNS ---------------------------------------------------------------------------------------------------------------
	discount_amount_line = fields.Float(string='Discount')
	discount = fields.Float(string='Discount (%)', digits= dp.get_precision('Discount'),
							compute=_compute_discount_amount_line_percentage, default=0.0)
