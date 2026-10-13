"""Pytest bootstrap: guarantees DB isolation before ANY test module is imported.

pytest imports conftest.py before collecting test modules, so SRH_DB_PATH is
set before database.db_manager binds DB_PATH at its first import. Without
this, whichever test module imports first (alphabetical: test_ingest_job)
would pin the whole suite to the production database file.
"""
import os
import tempfile

import pytest

_tmp_db = tempfile.NamedTemporaryFile(prefix="srh_test_conftest_", suffix=".db", delete=False)
_tmp_db.close()
os.environ["SRH_DB_PATH"] = _tmp_db.name


@pytest.fixture(scope="session", autouse=True)
def _cleanup_conftest_tmp_db():
    yield
    try:
        os.unlink(_tmp_db.name)
    except OSError:
        pass
