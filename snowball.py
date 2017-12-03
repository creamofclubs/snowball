import logging
import collections
import datetime
import sample_debts

# Number of periods where there is a payment/compound event
_PERIODS = 12
_LOG_LEVEL = logging.INFO


class Loan(object):

    def __init__(self, name, principal, interest):
        self.name = name
        self.principal = principal
        self.interest = interest
        self.period = _PERIODS

    def _adjust_loan(self, adjustment):
        logging.info('Made a %s adjustment on %s.', adjustment, self.name)
        self.principal += adjustment

    def accrue_interest(self):
        interest_adjustment = self.calculate_interest()
        self._adjust_loan(interest_adjustment)

    def paydown_loan(self, payment):
        payment = -payment
        self._adjust_loan(payment)

    def calculate_interest(self):
        return self.principal * self.interest / self.period

    def loan_data(self):
        formatted_text = """
        Name: %s
        Principal: %s
        Interest: %s
        Period: %s""" % (self.name, self.principal, self.interest, self.period)
        return formatted_text


class PaymentSchedule(object):

    def __init__(self, debts, starting_month):
        self.payment_schedule = {}
        for loan in debts:
            self.payment_schedule[loan.name] = [0]
        self.period = 0
        self.current_cycle = []
        self.starting_month = starting_month
        logging.info('Created the following columns %s.', self.payment_schedule)

    def end_payment_cycle(self):
        self.period += 1
        for loan_name in self.payment_schedule:
            loan_entry = self.payment_schedule[loan_name]
            loan_entry.append(0)

    def add_payment(self, loan_name, payment):
        loan_entry = self.payment_schedule[loan_name]
        loan_entry[self.period] += payment

    def _add_month(self, date):
        date += datetime.timedelta(32)
        date.replace(day=1)
        return date

    def print_schedule(self):
        schedule = []
        header = ''
        rows = []
        for loan_name in self.payment_schedule:
            header += loan_name + ',' + ' '
            row = self.payment_schedule[loan_name]
            rows.append(row)
        schedule.append(header)
        schedule.append(rows)
        return schedule


class PaymentCalculator(object):

    def __init__(self, debts, initial_monthly_payment, starting_month, delay_first_payment=0):
        self.debts = self._create_ordered_debt_objects(debts)
        self.monthly_payment = initial_monthly_payment
        self.payment_schedule = PaymentSchedule(self.debts, starting_month)
        for period in xrange(delay_first_payment):
            for loan in self.debts:
                loan.accrue_interest()

    def _create_ordered_debt_objects(self, debts):
        debt_obejcts = []
        ordered_debt_objects = []
        semi_ordered_debt_objects = []
        interests = set()
        debts_by_interest = collections.defaultdict(list)

        for debt_name in debts:
            debt = debts[debt_name]
            principal = debt['principal']
            interest = debt['interest']
            loan = Loan(debt_name, principal, interest)
            debt_obejcts.append(loan)
            debts_by_interest[loan.interest].append(loan)
            interests.add(interest)

        for interest in interests:
            debts = debts_by_interest[interest]
            debts = sorted(debts, key=lambda loan: loan.principal)
            debts_by_interest[interest] = debts

        interests = list(interests)
        interests.sort()
        interests.reverse()

        for interest in interests:
            semi_ordered_debt_objects.append(debts_by_interest[interest])

        for debt_list in semi_ordered_debt_objects:
            for debt in debt_list:
                ordered_debt_objects.append(debt)

        return ordered_debt_objects

    def _make_interest_payments(self, paydown_funds):
        for loan in self.debts:
            interest_only = loan.calculate_interest()
            logging.info('%s has a %s interest payment pending.', loan.name, interest_only)
            loan.accrue_interest()
            payment = 0
            if paydown_funds > interest_only:
                payment = interest_only
            else:
                payment = paydown_funds
            loan.paydown_loan(payment)
            paydown_funds -= payment
            self.payment_schedule.add_payment(loan.name, payment)
            logging.info('Making a %s payment on %s.', payment, loan.name)
        logging.info('Remaining funds of %s after interest payments.', paydown_funds)
        return paydown_funds

    def _make_snowballpayment(self, remaining_funds):
        loan_index = 0
        while remaining_funds > 0 and len(self.debts) > loan_index:
            loan = self.debts[loan_index]
            loan_balance = loan.principal
            payment = 0
            if remaining_funds < loan_balance:
                payment = remaining_funds
                remaining_funds = 0
            else:
                payment = loan_balance
                logging.info('loan %s paid off!', loan.name)
                self.debts.remove(loan)
            loan.paydown_loan(payment)
            self.payment_schedule.add_payment(loan.name, payment)
            remaining_funds -= payment

    def activate(self):
        while len(self.debts) > 0:
            paydown_funds = self.monthly_payment
            for loan in self.debts:
                logging.info('%s', loan.loan_data())

            remaining_funds = self._make_interest_payments(paydown_funds)

            self._make_snowballpayment(remaining_funds)
            for loan in self.debts:
                logging.info('%s', loan.loan_data())
            self.payment_schedule.end_payment_cycle()
        return self.payment_schedule.print_schedule()


def main():

    logging.getLogger().setLevel(_LOG_LEVEL)
    debts = sample_debts.debts
    today = datetime.date.today()
    initial_payment = 1000
    model = PaymentCalculator(debts, initial_payment, today)
    payment_schedule = model.activate()
    print payment_schedule


if __name__ == "__main__":
    main()
