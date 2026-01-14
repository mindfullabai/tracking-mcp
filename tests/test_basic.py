"""Basic tests for tracking server database operations."""

import os
import sys
import sqlite3
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_server.tracking_server import get_db_connection, auto_register_entity_type


def test_db_connection():
    """Test database connection."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM entity_types")
    count = cursor.fetchone()["count"]
    print(f"✓ Database connection OK (found {count} entity types)")
    conn.close()


def test_auto_register():
    """Test auto-registration of entity types."""
    test_data = {"test_field": "value", "test_number": 42}
    auto_register_entity_type("test_entity", test_data)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entity_types WHERE entity_type = 'test_entity'")
    row = cursor.fetchone()

    assert row is not None, "Entity type not registered"
    assert row["entity_type"] == "test_entity"
    assert "test_field" in json.loads(row["schema_example"])

    print("✓ Auto-registration OK")

    # Cleanup
    cursor.execute("DELETE FROM entity_types WHERE entity_type = 'test_entity'")
    conn.commit()
    conn.close()


def test_manual_insert_query():
    """Test manual insert and query."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert test event
    test_data = {"value": 123, "note": "test"}
    cursor.execute(
        """
        INSERT INTO tracking_events (entity_type, date, data)
        VALUES (?, ?, ?)
        """,
        ("test", datetime.now().strftime("%Y-%m-%d"), json.dumps(test_data))
    )
    event_id = cursor.lastrowid
    conn.commit()

    # Query back
    cursor.execute("SELECT * FROM tracking_events WHERE id = ?", (event_id,))
    row = cursor.fetchone()

    assert row is not None
    assert row["entity_type"] == "test"
    assert json.loads(row["data"])["value"] == 123

    print("✓ Manual insert/query OK")

    # Cleanup
    cursor.execute("DELETE FROM tracking_events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Running basic tests...")
    print()

    try:
        test_db_connection()
        test_auto_register()
        test_manual_insert_query()

        print()
        print("✅ All tests passed!")

    except Exception as e:
        print()
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
