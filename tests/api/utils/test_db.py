import pytest
import sqlite3
import aiosqlite
from unittest.mock import patch, AsyncMock, MagicMock, call
from src.api.utils.db import (
    get_new_db_connection,
    set_db_defaults,
    execute_db_operation,
    execute_many_db_operation,
    execute_multiple_db_operations,
    serialise_list_to_str,
    deserialise_list_from_str,
)


class TestSerialiseDeserialise:
    def test_serialise_list_to_str(self):
        """Test serialising a list to a comma-separated string."""
        test_list = ["item1", "item2", "item3"]
        result = serialise_list_to_str(test_list)
        assert result == "item1,item2,item3"

    def test_serialise_empty_list(self):
        """Test serialising an empty list."""
        result = serialise_list_to_str([])
        assert result is None

    def test_serialise_none(self):
        """Test serialising None."""
        result = serialise_list_to_str(None)
        assert result is None

    def test_deserialise_list_from_str(self):
        """Test deserialising a comma-separated string to a list."""
        test_str = "item1,item2,item3"
        result = deserialise_list_from_str(test_str)
        assert result == ["item1", "item2", "item3"]

    def test_deserialise_empty_string(self):
        """Test deserialising an empty string."""
        result = deserialise_list_from_str("")
        assert result == []

    def test_deserialise_none(self):
        """Test deserialising None."""
        result = deserialise_list_from_str(None)
        assert result == []


@pytest.mark.asyncio
class TestDbConnections:
    @pytest.mark.skip(reason="Need to find a better way to mock async context managers")
    @patch("src.api.utils.db.aiosqlite")
    async def test_get_new_db_connection(self, mock_aiosqlite):
        """Test the get_new_db_connection context manager."""
        # Setup mock connection
        mock_conn = AsyncMock()

        # Mock the aiosqlite.connect to return a connection with async context manager methods
        mock_aiosqlite.connect.return_value.__aenter__.return_value = mock_conn

        # Use the context manager
        async with get_new_db_connection() as conn:
            assert conn == mock_conn
            # Now mock the methods used inside the context manager
            mock_conn.execute.assert_called_once_with("PRAGMA synchronous=NORMAL;")
            mock_conn.set_trace_callback.assert_called_once()

        # Check that close was called after exiting the context
        mock_conn.close.assert_called_once()

    @pytest.mark.skip(reason="Need to find a better way to mock async context managers")
    @patch("src.api.utils.db.aiosqlite")
    async def test_get_new_db_connection_exception(self, mock_aiosqlite):
        """Test the get_new_db_connection context manager with an exception."""
        # Setup mock connection
        mock_conn = AsyncMock()

        # Mock the aiosqlite.connect to return a connection with async context manager methods
        mock_aiosqlite.connect.return_value.__aenter__.return_value = mock_conn

        # Set up the exception to be raised when execute is called
        mock_conn.execute.side_effect = Exception("Test exception")

        # Use the context manager with an exception
        with pytest.raises(Exception):
            async with get_new_db_connection() as conn:
                pass

        # Since the exception was raised inside the context,
        # the __aexit__ method should have been called,
        # which should have called conn.rollback() and conn.close()
        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
class TestDbOperations:
    @patch("src.api.utils.db.get_new_db_connection")
    async def test_execute_db_operation_fetch_one(self, mock_get_conn):
        """Test execute_db_operation with fetch_one=True."""
        # Setup mocks
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 1, "name": "Test"}
        mock_get_conn.return_value = mock_conn

        # Call the function
        result = await execute_db_operation(
            "SELECT * FROM test WHERE id = ?", params=(1,), fetch_one=True
        )

        # Check results
        assert result == {"id": 1, "name": "Test"}
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM test WHERE id = ?", (1,)
        )
        mock_cursor.fetchone.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("src.api.utils.db.get_new_db_connection")
    async def test_execute_db_operation_fetch_all(self, mock_get_conn):
        """Test execute_db_operation with fetch_all=True."""
        # Setup mocks
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Test1"},
            {"id": 2, "name": "Test2"},
        ]
        mock_get_conn.return_value = mock_conn

        # Call the function
        result = await execute_db_operation("SELECT * FROM test", fetch_all=True)

        # Check results
        assert result == [{"id": 1, "name": "Test1"}, {"id": 2, "name": "Test2"}]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test")
        mock_cursor.fetchall.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("src.api.utils.db.get_new_db_connection")
    async def test_execute_db_operation_get_last_row_id(self, mock_get_conn):
        """Test execute_db_operation with get_last_row_id=True."""
        # Setup mocks
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 42
        mock_get_conn.return_value = mock_conn

        # Call the function
        result = await execute_db_operation(
            "INSERT INTO test (name) VALUES (?)", params=("Test",), get_last_row_id=True
        )

        # Check results
        assert result == 42
        mock_cursor.execute.assert_called_once_with(
            "INSERT INTO test (name) VALUES (?)", ("Test",)
        )
        mock_conn.commit.assert_called_once()

    @patch("src.api.utils.db.get_new_db_connection")
    async def test_execute_many_db_operation(self, mock_get_conn):
        """Test execute_many_db_operation."""
        # Setup mocks
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Call the function
        params_list = [("Test1",), ("Test2",), ("Test3",)]
        await execute_many_db_operation(
            "INSERT INTO test (name) VALUES (?)", params_list
        )

        # Check results
        mock_cursor.executemany.assert_called_once_with(
            "INSERT INTO test (name) VALUES (?)", params_list
        )
        mock_conn.commit.assert_called_once()

    @patch("src.api.utils.db.get_new_db_connection")
    async def test_execute_multiple_db_operations(self, mock_get_conn):
        """Test execute_multiple_db_operations."""
        # Setup mocks
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Call the function
        commands_and_params = [
            ("INSERT INTO test (name) VALUES (?)", ("Test1",)),
            ("UPDATE test SET name = ? WHERE id = ?", ("Test2", 1)),
            ("DELETE FROM test WHERE id = ?", (2,)),
        ]
        await execute_multiple_db_operations(commands_and_params)

        # Check results
        assert mock_cursor.execute.call_count == 3
        mock_cursor.execute.assert_has_calls(
            [
                call("INSERT INTO test (name) VALUES (?)", ("Test1",)),
                call("UPDATE test SET name = ? WHERE id = ?", ("Test2", 1)),
                call("DELETE FROM test WHERE id = ?", (2,)),
            ]
        )
        mock_conn.commit.assert_called_once()


# Test for set_db_defaults would require mocking sqlite3.connect and executescript
# which is more complex as it's not an async function
class TestSetDbDefaults:
    @patch("src.api.utils.db.sqlite3.connect")
    def test_set_db_defaults_wal_not_set(self, mock_connect):
        """Test set_db_defaults when WAL mode is not set."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.execute().fetchone.return_value = ["delete"]  # Not WAL mode

        # Call the function
        set_db_defaults()

        # Check results
        mock_conn.executescript.assert_called_once_with("PRAGMA journal_mode = WAL;")

    @patch("src.api.utils.db.sqlite3.connect")
    def test_set_db_defaults_wal_already_set(self, mock_connect):
        """Test set_db_defaults when WAL mode is already set."""
        # Setup mocks
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.execute().fetchone.return_value = ["wal"]  # Already in WAL mode

        # Call the function
        set_db_defaults()

        # Check that executescript was not called
        mock_conn.executescript.assert_not_called()
