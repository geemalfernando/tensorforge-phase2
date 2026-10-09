from app.database import Connection, HybridRow


class RecordingConnection:
    def __init__(self):
        self.query = None
        self.parameters = None

    def execute(self, query, parameters):
        self.query = query
        self.parameters = parameters
        return self


def test_postgres_connection_translates_sqlite_placeholders():
    raw_connection = RecordingConnection()
    connection = Connection(raw_connection, postgres=True)

    connection.execute("SELECT * FROM jobs WHERE job_id=? AND status=?", ("id", "queued"))

    assert raw_connection.query == "SELECT * FROM jobs WHERE job_id=%s AND status=%s"
    assert raw_connection.parameters == ("id", "queued")


def test_hybrid_row_supports_named_and_positional_access():
    row = HybridRow({"status": "running", "processed": 12})

    assert row["status"] == "running"
    assert row[0] == "running"
    assert row[1] == 12
