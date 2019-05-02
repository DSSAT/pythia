import datetime
import itertools

import pythia.util


def generate_days(start_offset, days_between, number_of_dates):
    return ((d * days_between) + start_offset for d in range(number_of_dates))


# def generate_pdate(k, run, context):
def pdate_factors(year, start_offset, days_between, number_of_dates):
    two_digit_year = str(year)[2:]
    g = generate_days(start_offset, days_between, number_of_dates)
    return ["{}{}".format(two_digit_year, "{:>03d}".format(d)) for d in g]


def hdate_factors(pdates, start_offset, days_between, number_of_dates):
    g = generate_days(start_offset, days_between, number_of_dates)
    offsets = (datetime.timedelta(days=d) for d in g)
    return list(
        dict.fromkeys([
            pythia.util.to_julian_date(pythia.util.from_julian_date(p) + h)
            for p, h in itertools.product(pdates, offsets)
        ]))


def generate_factor_list(pdates_len, hdates_offsets_len):
    return [(pf + 1, pf + hf + 1) for pf, hf in itertools.product(
        range(pdates_len), range(hdates_offsets_len))]
