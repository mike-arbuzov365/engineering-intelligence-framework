class CheckoutController:
    def __init__(self, payments):
        self.payments = payments

    def checkout(self):
        return self.payments.capture()


class PaymentService:
    def __init__(self, invoices):
        self.invoices = invoices

    def capture(self):
        return self.invoices.save()


class InvoiceRepository:
    def save(self):
        return "saved"
