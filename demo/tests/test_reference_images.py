"""
Tests for reference image generation (Phase 3).

Run with:
    cd demo && pytest tests/test_reference_images.py -v

Success criteria: All tests must pass.

These tests verify:
1. Reference prompt generation for different subject types
2. Reference image endpoint behavior
3. Storage of reference URLs in subjects
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestReferencePromptGeneration:
    """Test prompt generation for reference images."""

    def test_human_reference_prompt_includes_key_details(self):
        """Human reference prompts should include appearance details."""
        from consistency import ConsistencyManager, SubjectType, ConfidenceLevel, Attribute
        from consistency.schemas import HairDetails, FaceDetails

        manager = ConsistencyManager("test-session")
        subject = manager.create_human_subject(
            name="Sarah",
            role="protagonist",
            gender="female",
            age_range="young adult"
        )

        # Add more details
        if subject.human_details:
            subject.human_details.hair = HairDetails(
                color=Attribute(value="dark brown", confidence=ConfidenceLevel.CONFIRMED),
                style=Attribute(value="shoulder-length wavy", confidence=ConfidenceLevel.CONFIRMED)
            )
            subject.human_details.face = FaceDetails(
                skin_tone=Attribute(value="warm beige", confidence=ConfidenceLevel.CONFIRMED)
            )

        from consistency import PromptAssembler
        assembler = PromptAssembler(manager.state)

        # Generate reference prompt
        prompt = assembler.assemble_reference_prompt(
            subject_id=subject.id,
            pose="front-facing, neutral expression"
        )

        # Should include key visual details
        assert "female" in prompt.lower()
        assert "dark brown" in prompt.lower()
        assert "front-facing" in prompt.lower()
        assert "reference" in prompt.lower() or "clear lighting" in prompt.lower()

    def test_animal_reference_prompt_includes_species_details(self):
        """Animal reference prompts should include species and breed."""
        from consistency import ConsistencyManager, SubjectType, ConfidenceLevel, Attribute
        from consistency.schemas import AnimalDetails

        manager = ConsistencyManager("test-session")
        subject = manager.add_subject(
            subject_type=SubjectType.ANIMAL,
            name="Max",
            role="pet"
        )
        subject.animal_details = AnimalDetails(
            species=Attribute(value="dog", confidence=ConfidenceLevel.CONFIRMED),
            breed=Attribute(value="golden retriever", confidence=ConfidenceLevel.CONFIRMED),
            color=Attribute(value="golden cream", confidence=ConfidenceLevel.CONFIRMED)
        )

        from consistency import PromptAssembler
        assembler = PromptAssembler(manager.state)

        prompt = assembler.assemble_reference_prompt(
            subject_id=subject.id,
            pose="sitting, looking at camera"
        )

        # Should include animal details
        assert "golden retriever" in prompt.lower() or "dog" in prompt.lower()
        assert "golden" in prompt.lower() or "cream" in prompt.lower()

    def test_object_reference_prompt_includes_product_details(self):
        """Object reference prompts should include material and design."""
        from consistency import ConsistencyManager, SubjectType, ConfidenceLevel, Attribute
        from consistency.schemas import ObjectDetails

        manager = ConsistencyManager("test-session")
        subject = manager.add_subject(
            subject_type=SubjectType.OBJECT,
            name="Hero Product",
            role="product"
        )
        subject.object_details = ObjectDetails(
            category=Attribute(value="smartphone", confidence=ConfidenceLevel.CONFIRMED),
            color=Attribute(value="midnight black", confidence=ConfidenceLevel.CONFIRMED),
            material=Attribute(value="glass and aluminum", confidence=ConfidenceLevel.INFERRED)
        )

        from consistency import PromptAssembler
        assembler = PromptAssembler(manager.state)

        prompt = assembler.assemble_reference_prompt(
            subject_id=subject.id,
            pose="front view, slight angle"
        )

        # Should include object details
        assert "smartphone" in prompt.lower()


class TestReferenceImageEndpoint:
    """Test the /api/generate-reference endpoint."""

    def test_endpoint_requires_session(self, app_client):
        """Should return error if no session exists."""
        response = app_client.post("/api/generate-reference", json={
            "subject_id": "fake-id"
        })
        assert response.status_code in [400, 404]

    def test_endpoint_requires_valid_subject(self, app_client_with_session):
        """Should return error for invalid subject ID."""
        response = app_client_with_session.post("/api/generate-reference", json={
            "subject_id": "nonexistent-subject-id"
        })
        assert response.status_code in [400, 404]
        data = response.get_json()
        assert "error" in data or "not found" in str(data).lower()

    def test_endpoint_generates_reference_for_valid_subject(self, app_client_with_subject):
        """Should start image generation for valid subject."""
        client, subject_id = app_client_with_subject

        response = client.post("/api/generate-reference", json={
            "subject_id": subject_id,
            "pose": "front-facing portrait"
        })

        # Should either complete immediately or return task ID for polling
        assert response.status_code == 200
        data = response.get_json()
        assert "task_id" in data or "url" in data or "reference_url" in data

    def test_endpoint_stores_reference_url_on_completion(self, app_client_with_subject):
        """After generation, reference URL should be stored in subject."""
        client, subject_id = app_client_with_subject

        # This test may need mocking if actual API isn't available
        # The implementation should store the URL in subject.reference_image_url


class TestReferenceImageStorage:
    """Test storage and retrieval of reference images."""

    def test_subject_has_reference_url_field(self):
        """SubjectSheet should have reference_image_url field."""
        from consistency.schemas import SubjectSheet, SubjectType

        subject = SubjectSheet(
            id="test-id",
            name="Test",
            subject_type=SubjectType.HUMAN
        )

        # Should have the field (may be None initially)
        assert hasattr(subject, "reference_image_url") or hasattr(subject, "reference_url")

    def test_manager_can_update_reference_url(self):
        """ConsistencyManager should be able to set reference URL."""
        from consistency import ConsistencyManager, SubjectType

        manager = ConsistencyManager("test-session")
        subject = manager.create_human_subject(name="Test", role="protagonist")

        # Should be able to set reference URL
        # The implementation may vary - could be a method or direct assignment
        test_url = "https://example.com/reference.png"

        # Try different approaches the implementation might use
        if hasattr(manager, "set_reference_url"):
            manager.set_reference_url(subject.id, test_url)
        elif hasattr(subject, "reference_image_url"):
            subject.reference_image_url = test_url
        elif hasattr(subject, "reference_url"):
            subject.reference_url = test_url

        # Verify it was stored
        updated_subject = manager.get_subject(subject.id)
        ref_url = getattr(updated_subject, "reference_image_url", None) or getattr(updated_subject, "reference_url", None)
        assert ref_url == test_url


# ============ Fixtures ============

@pytest.fixture
def app_client():
    """Create a test client without session."""
    import sys
    sys.path.insert(0, ".")
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def app_client_with_session():
    """Create a test client with an active session."""
    import sys
    sys.path.insert(0, ".")
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["session_id"] = "test-session-123"
            sess["conversation"] = []
        yield client


@pytest.fixture
def app_client_with_subject():
    """Create a test client with a session and a subject."""
    import sys
    sys.path.insert(0, ".")
    from app import app, get_consistency_manager
    from consistency import SubjectType

    app.config["TESTING"] = True

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["session_id"] = "test-session-with-subject"
            sess["conversation"] = []

        # Create a subject in the manager
        manager = get_consistency_manager("test-session-with-subject")
        subject = manager.create_human_subject(
            name="Test Subject",
            role="protagonist",
            gender="female"
        )

        yield client, subject.id
