from text2sql.catalog import terms_prompt
from text2sql.profile import date_kind, profile_columns


def test_date_only():
    assert date_kind(["2018-01-01 00:00:00", "2018-01-02 00:00:00"]).startswith("date only")


def test_datetime():
    assert date_kind(["2018-01-01 10:30:00", "2018-01-02 00:00:00"]) == "datetime"


def test_date_only_tolerates_dst_noise():
    values = ["2018-01-01 00:00:00"] * 99 + ["2017-10-15 01:00:00"]
    assert date_kind(values).startswith("date only")


def test_not_date():
    assert date_kind(["franca", "2018-01-01 00:00:00"]) is None
    assert date_kind([]) is None


def test_profile_flags_estimated_date():
    lines = profile_columns().splitlines()
    est = next(l for l in lines if "order_estimated_delivery_date" in l)
    assert "date only" in est
    delivered = next(l for l in lines if "order_delivered_customer_date" in l)
    assert "datetime" in delivered


def test_profile_lists_small_value_sets():
    status = next(l for l in profile_columns().splitlines() if "orders.order_status" in l)
    assert "values:" in status and "delivered" in status


def test_terms_prompt_has_late_delivery():
    assert "date(order_estimated_delivery_date)" in terms_prompt()
