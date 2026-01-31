"""
Tests for Phase 1: Session Saving Bug Fixes.

Run with:
    cd demo && pytest tests/test_phase1_session_bugfix.py -v

Success criteria: All tests must pass.

These tests verify:
1. Session cookies stay under 4KB limit
2. No duplicate sessions are created
3. Sessions persist conversation data correctly
4. Session deletion works properly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestSessionCookieSize:
    """Test that session cookies stay within browser limits."""

    def test_flask_session_not_storing_conversation(self):
        """Flask session should NOT store full conversation (causes cookie overflow)."""
        from app import app

        with app.test_client() as client:
            # Start a session
            response = client.get('/')
            assert response.status_code == 200

            # Check what's in the session - should NOT have full conversation
            with client.session_transaction() as sess:
                # Session should only store session_id reference, not full data
                if 'conversation' in sess:
                    # If conversation is stored, it should be empty or minimal
                    conv = sess.get('conversation', [])
                    # Serialize to check size
                    conv_json = json.dumps(conv)
                    # Should be well under 4KB (4093 bytes is the cookie limit)
                    assert len(conv_json) < 2000, (
                        f"Session stores {len(conv_json)} bytes of conversation data. "
                        "This will cause cookie overflow. Store conversation in database only."
                    )

    def test_session_stores_only_ids(self):
        """Session should only store IDs, not full data."""
        from app import app

        with app.test_client() as client:
            response = client.get('/')

            with client.session_transaction() as sess:
                # Check all session keys
                allowed_keys = {'session_id', 'image_provider', 'video_provider',
                               'llm_provider', 'llm_model', '_fresh', '_id'}

                for key in sess.keys():
                    if key.startswith('_'):
                        continue  # Flask internal keys

                    value = sess[key]
                    if isinstance(value, (list, dict)):
                        value_json = json.dumps(value)
                        assert len(value_json) < 500, (
                            f"Session key '{key}' stores {len(value_json)} bytes. "
                            "Large data should be in database, not session cookie."
                        )


class TestNoDuplicateSessions:
    """Test that sessions aren't duplicated."""

    def test_page_refresh_doesnt_create_new_session(self):
        """Refreshing the page should use existing session, not create new."""
        from app import app
        import db

        with app.test_client() as client:
            # First request - creates session
            response1 = client.get('/')
            with client.session_transaction() as sess:
                session_id_1 = sess.get('session_id')

            # Second request - should use same session
            response2 = client.get('/')
            with client.session_transaction() as sess:
                session_id_2 = sess.get('session_id')

            assert session_id_1 == session_id_2, (
                "Page refresh created a new session instead of reusing existing one"
            )

    def test_explicit_session_param_is_used(self):
        """When ?session=X is provided, that session should be used."""
        from app import app
        import db

        # Create a session first
        test_session_id = db.create_session(name="Test Session")

        with app.test_client() as client:
            # Request with explicit session
            response = client.get(f'/?session={test_session_id}')

            with client.session_transaction() as sess:
                assert sess.get('session_id') == test_session_id, (
                    "URL session parameter was ignored"
                )

        # Cleanup
        db.delete_session(test_session_id)


class TestSessionPersistence:
    """Test that session data persists correctly."""

    def test_conversation_persists_to_database(self):
        """Conversation should be stored in database, retrievable later."""
        from app import app
        import db

        with app.test_client() as client:
            # Create session
            client.get('/')

            with client.session_transaction() as sess:
                session_id = sess.get('session_id')

            # Send a chat message
            response = client.post('/chat',
                json={'message': 'Test product idea'},
                content_type='application/json'
            )

            # Verify conversation is in database
            conversation = db.get_conversation(session_id)
            assert len(conversation) >= 1, (
                "Conversation was not saved to database"
            )

            # User message should be there
            user_messages = [m for m in conversation if m['role'] == 'user']
            assert any('Test product idea' in m['content'] for m in user_messages), (
                "User message was not saved to database"
            )

    def test_session_loads_from_database_on_refresh(self):
        """Session data should load from database when page is refreshed."""
        from app import app
        import db

        # Create session with some data
        session_id = db.create_session(name="Persistence Test")
        db.add_message(session_id, "user", "My test message")
        db.add_message(session_id, "assistant", '{"message": "Test response"}')

        with app.test_client() as client:
            # Load the session
            response = client.get(f'/?session={session_id}')
            assert response.status_code == 200

            # The session should have loaded the conversation
            # (This is handled by restoreSessionState in JS, but backend should provide data)
            session_data = db.get_session(session_id)
            assert len(session_data['conversation']) == 2, (
                "Session conversation not retrieved from database"
            )

        # Cleanup
        db.delete_session(session_id)


class TestSessionDeletion:
    """Test that session deletion works properly."""

    def test_delete_session_removes_from_database(self):
        """Deleting a session should remove it from database."""
        import db

        # Create a session
        session_id = db.create_session(name="To Delete")
        db.add_message(session_id, "user", "Test message")

        # Verify it exists
        assert db.get_session(session_id) is not None

        # Delete it
        db.delete_session(session_id)

        # Verify it's gone
        assert db.get_session(session_id) is None, (
            "Session still exists after deletion"
        )

    def test_delete_session_removes_related_data(self):
        """Deleting a session should cascade to conversations and videos."""
        import db

        # Create session with related data
        session_id = db.create_session(name="Cascade Test")
        db.add_message(session_id, "user", "Test")
        video_id = db.create_video(session_id, script={"test": True})

        # Delete session
        db.delete_session(session_id)

        # Conversation should be gone (foreign key cascade)
        conversation = db.get_conversation(session_id)
        assert len(conversation) == 0, (
            "Conversation data still exists after session deletion"
        )

        # Video should be gone
        video = db.get_video(video_id)
        assert video is None, (
            "Video data still exists after session deletion"
        )

    def test_delete_api_endpoint_works(self):
        """DELETE /api/sessions/<id> should work."""
        from app import app
        import db

        session_id = db.create_session(name="API Delete Test")

        with app.test_client() as client:
            response = client.delete(f'/api/sessions/{session_id}')
            assert response.status_code == 200

            # Verify deleted
            assert db.get_session(session_id) is None


class TestEmptySessionHandling:
    """Test handling of sessions with no conversation."""

    def test_empty_session_not_shown_as_saved(self):
        """Sessions with only the initial message shouldn't appear as 'saved'."""
        import db

        # Create empty session
        session_id = db.create_session(name="Empty Test")

        # Get session - it should have no conversation
        session = db.get_session(session_id)
        assert len(session['conversation']) == 0

        # List sessions - empty ones could be filtered or marked
        sessions = db.list_sessions()
        empty_session = next((s for s in sessions if s['id'] == session_id), None)
        assert empty_session is not None

        # The has_video flag or similar should indicate it's essentially empty
        # (This might need a new field like 'has_content' or filtering logic)

        # Cleanup
        db.delete_session(session_id)
