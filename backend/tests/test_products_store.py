from datetime import UTC, date, datetime

from hubapp.products.store import _row_to_product


def test_row_to_product_maps_columns_in_order():
    # created_at is TIMESTAMPTZ in Postgres, so psycopg returns a tz-aware
    # datetime in real usage — match that here rather than a naive one.
    created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    row = (
        "11111111-1111-1111-1111-111111111111",
        "Kitchen vacuum",
        "Roborock",
        "S7",
        "vacuum",
        2022,
        date(2022, 6, 1),
        date(2024, 6, 1),
        "Bought on sale",
        None,
        created_at,
    )
    product = _row_to_product(row)

    assert product.id == "11111111-1111-1111-1111-111111111111"
    assert product.nickname == "Kitchen vacuum"
    assert product.brand == "Roborock"
    assert product.model == "S7"
    assert product.category == "vacuum"
    assert product.year == 2022
    assert product.purchase_date == date(2022, 6, 1)
    assert product.warranty_expires == date(2024, 6, 1)
    assert product.notes == "Bought on sale"
    assert product.ha_device_id is None
    assert product.created_at == created_at
