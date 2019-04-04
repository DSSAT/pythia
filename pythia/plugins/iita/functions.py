import datetime


def generate_days(start_offset, days_between, number_of_dates):
    return ((d * days_between) + start_offset for d in range(number_of_dates))


# def generate_pdate(k, run, context):
def generate_pdate(year, start_offset, days_between, number_of_dates):
    two_digit_year = str(year)[2:]
    g = generate_days(start_offset, days_between, number_of_dates)
    return ["{}{}".format(two_digit_year, "{:>03d}".format(d)) for d in g]


# def generate_hdate
def generate_hdate(pdates, start_offset, days_between, number_of_dates):
    g = generate_days(start_offset, days_between, number_of_dates)
    return [datetime.timedelta(days=d) for d in g]


def generate_factors(run, **kwargs):
    pass
