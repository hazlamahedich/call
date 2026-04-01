from unittest.mock import MagicMock


def _make_row(**fields):
    row = MagicMock()
    row._mapping = fields
    return row


def _make_result(row=None, fetchall=None):
    result = MagicMock()
    result.first.return_value = row
    if fetchall is not None:
        result.fetchall.return_value = fetchall
    return result
