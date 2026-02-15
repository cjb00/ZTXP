# tests/test_notes_api.py
"""Unit tests for the Notes API Lambda handler."""
import importlib
import importlib.util
import json
import os
from unittest.mock import patch, MagicMock

import pytest

_notes_dir = os.path.join(os.path.dirname(__file__), "..", "app", "lambdas", "notes_api")

mock_table = MagicMock()
mock_ddb_resource = MagicMock()
mock_ddb_resource.Table.return_value = mock_table

with patch.dict(os.environ, {"TABLE_NAME": "test-notes"}):
    with patch("boto3.resource", return_value=mock_ddb_resource):
        spec = importlib.util.spec_from_file_location("notes_handler", os.path.join(_notes_dir, "handler.py"))
        notes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(notes)
        notes.table = mock_table


def _make_event(method="GET", proxy="", body=None, principal_id="user:alice"):
    event = {
        "requestContext": {
            "http": {"method": method},
            "authorizer": {"lambda": {"principalId": principal_id}},
        },
        "pathParameters": {"proxy": proxy} if proxy else None,
    }
    if body:
        event["body"] = json.dumps(body)
    return event


class TestUserIdExtraction:
    def test_extracts_principal(self):
        event = _make_event(principal_id="user:bob")
        assert notes._user_id(event) == "user:bob"

    def test_defaults_to_anonymous(self):
        event = {"requestContext": {}}
        assert notes._user_id(event) == "anonymous"


class TestNoteIdFromPath:
    def test_extracts_note_id(self):
        event = _make_event(proxy="abc-123")
        assert notes._note_id_from_path(event) == "abc-123"

    def test_none_when_empty(self):
        event = _make_event()
        assert notes._note_id_from_path(event) is None


class TestLambdaHandler:
    def test_list_notes(self):
        mock_table.query.return_value = {"Items": [{"note_id": "1", "title": "Test"}]}
        result = notes.lambda_handler(_make_event(method="GET"), None)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert len(body["notes"]) == 1

    def test_get_note(self):
        mock_table.get_item.return_value = {"Item": {"note_id": "abc", "title": "Hello"}}
        result = notes.lambda_handler(_make_event(method="GET", proxy="abc"), None)

        assert result["statusCode"] == 200
        assert json.loads(result["body"])["title"] == "Hello"

    def test_get_note_not_found(self):
        mock_table.get_item.return_value = {}
        result = notes.lambda_handler(_make_event(method="GET", proxy="missing"), None)

        assert result["statusCode"] == 404

    def test_create_note(self):
        mock_table.put_item.return_value = {}
        result = notes.lambda_handler(
            _make_event(method="POST", body={"title": "New", "content": "Body"}), None
        )
        body = json.loads(result["body"])

        assert result["statusCode"] == 201
        assert body["title"] == "New"
        assert "note_id" in body
        assert "created_at" in body

    def test_update_note(self):
        mock_table.update_item.return_value = {"Attributes": {"title": "Updated"}}
        result = notes.lambda_handler(
            _make_event(method="PUT", proxy="abc", body={"title": "Updated", "content": "New body"}),
            None,
        )

        assert result["statusCode"] == 200
        assert json.loads(result["body"])["title"] == "Updated"

    def test_delete_note(self):
        mock_table.delete_item.return_value = {}
        result = notes.lambda_handler(_make_event(method="DELETE", proxy="abc"), None)

        assert result["statusCode"] == 200
        assert json.loads(result["body"])["deleted"] == "abc"

    def test_method_not_allowed(self):
        result = notes.lambda_handler(_make_event(method="PATCH"), None)
        assert result["statusCode"] == 405

    def test_invalid_json_body(self):
        event = _make_event(method="POST")
        event["body"] = "not-json"
        result = notes.lambda_handler(event, None)
        assert result["statusCode"] == 400
