"""
ConsistencyManager - State tracking for visual consistency across video frames.

Handles creation, updates, and persistence of consistency state via database.
"""
import uuid
from datetime import datetime
from typing import Optional

from .schemas import (
    VideoConsistencyState,
    SubjectSheet,
    SubjectType,
    EnvironmentSheet,
    VisualStyle,
    Attribute,
    ConfidenceLevel,
    HumanDetails,
    AnimalDetails,
    ObjectDetails,
)


class ConsistencyManager:
    """
    Manages visual consistency state for a video generation session.

    Provides methods to:
    - Create and update subjects, environments, and styles
    - Save/load state from database
    - Generate prompt blocks at different detail levels
    """

    def __init__(self, session_id: str, db_module=None):
        """
        Initialize a ConsistencyManager for a session.

        Args:
            session_id: The video generation session ID
            db_module: Optional database module for persistence
        """
        self.session_id = session_id
        self._db = db_module
        self._state: Optional[VideoConsistencyState] = None
        self._dirty = False  # Track if state has unsaved changes

    @property
    def state(self) -> VideoConsistencyState:
        """Get the current consistency state, loading from DB if needed."""
        if self._state is None:
            self._state = self._load_or_create()
        return self._state

    def _load_or_create(self) -> VideoConsistencyState:
        """Load existing state from DB or create new one."""
        if self._db:
            existing = self._db.get_consistency_state(self.session_id)
            if existing:
                return existing

        # Create new empty state
        return VideoConsistencyState(
            id=str(uuid.uuid4()),
            session_id=self.session_id
        )

    def save(self) -> bool:
        """
        Save current state to database.

        Returns:
            True if saved successfully, False if no DB configured or error
        """
        if not self._db or self._state is None:
            return False

        self._state.updated_at = datetime.utcnow()
        self._state.version += 1

        try:
            self._db.save_consistency_state(self._state)
            self._dirty = False
            return True
        except Exception:
            return False

    def load(self) -> bool:
        """
        Force reload state from database.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self._db:
            return False

        try:
            loaded = self._db.get_consistency_state(self.session_id)
            if loaded:
                self._state = loaded
                self._dirty = False
                return True
            return False
        except Exception:
            return False

    @property
    def is_dirty(self) -> bool:
        """Check if there are unsaved changes."""
        return self._dirty

    # ============ Subject Management ============

    def add_subject(
        self,
        subject_type: SubjectType,
        name: Optional[str] = None,
        role: Optional[str] = None,
        **kwargs
    ) -> SubjectSheet:
        """
        Add a new subject to the consistency state.

        Args:
            subject_type: Type of subject (human, animal, object)
            name: Human-readable name for the subject
            role: Role in the video (protagonist, product, prop)
            **kwargs: Additional attributes to set

        Returns:
            The created SubjectSheet
        """
        subject = SubjectSheet(
            id=str(uuid.uuid4()),
            name=name,
            subject_type=subject_type,
            role=role
        )

        # Initialize type-specific details
        if subject_type == SubjectType.HUMAN:
            subject.human_details = HumanDetails()
        elif subject_type == SubjectType.ANIMAL:
            subject.animal_details = AnimalDetails()
        elif subject_type == SubjectType.OBJECT:
            subject.object_details = ObjectDetails()

        self.state.subjects.append(subject)
        self._dirty = True

        return subject

    def get_subject(self, subject_id: str) -> Optional[SubjectSheet]:
        """Get a subject by ID."""
        return self.state.get_subject_by_id(subject_id)

    def get_subject_by_role(self, role: str) -> Optional[SubjectSheet]:
        """Get a subject by role."""
        return self.state.get_subject_by_role(role)

    def update_subject(
        self,
        subject_id: str,
        turn: Optional[int] = None,
        confidence: ConfidenceLevel = ConfidenceLevel.INFERRED,
        **updates
    ) -> Optional[SubjectSheet]:
        """
        Update a subject's attributes.

        Args:
            subject_id: ID of the subject to update
            turn: Conversation turn number for source tracking
            confidence: Confidence level for the updates
            **updates: Attribute updates as key-value pairs

        Returns:
            Updated SubjectSheet or None if not found
        """
        subject = self.get_subject(subject_id)
        if not subject:
            return None

        # Process updates based on subject type
        details = None
        if subject.subject_type == SubjectType.HUMAN:
            details = subject.human_details
        elif subject.subject_type == SubjectType.ANIMAL:
            details = subject.animal_details
        elif subject.subject_type == SubjectType.OBJECT:
            details = subject.object_details

        if details:
            for key, value in updates.items():
                if hasattr(details, key):
                    attr = Attribute(
                        value=str(value),
                        confidence=confidence,
                        source_turn=turn
                    )
                    setattr(details, key, attr)

        subject.updated_at = datetime.utcnow()
        self._dirty = True

        return subject

    def remove_subject(self, subject_id: str) -> bool:
        """
        Remove a subject from the state.

        Returns:
            True if removed, False if not found
        """
        for i, subject in enumerate(self.state.subjects):
            if subject.id == subject_id:
                self.state.subjects.pop(i)
                self._dirty = True
                return True
        return False

    # ============ Environment Management ============

    def set_environment(
        self,
        name: Optional[str] = None,
        **kwargs
    ) -> EnvironmentSheet:
        """
        Set or create the environment configuration.

        Args:
            name: Human-readable name
            **kwargs: Environment attributes

        Returns:
            The EnvironmentSheet
        """
        if self.state.environment is None:
            self.state.environment = EnvironmentSheet(
                id=str(uuid.uuid4()),
                name=name
            )
        elif name:
            self.state.environment.name = name

        self._dirty = True
        return self.state.environment

    def update_environment(
        self,
        turn: Optional[int] = None,
        confidence: ConfidenceLevel = ConfidenceLevel.INFERRED,
        **updates
    ) -> Optional[EnvironmentSheet]:
        """
        Update environment attributes.

        Args:
            turn: Conversation turn for source tracking
            confidence: Confidence level
            **updates: Attribute updates

        Returns:
            Updated EnvironmentSheet or None
        """
        env = self.state.environment
        if not env:
            env = self.set_environment()

        for key, value in updates.items():
            if hasattr(env, key):
                attr = Attribute(
                    value=str(value),
                    confidence=confidence,
                    source_turn=turn
                )
                setattr(env, key, attr)

        env.updated_at = datetime.utcnow()
        self._dirty = True

        return env

    # ============ Style Management ============

    def set_style(
        self,
        name: Optional[str] = None,
        **kwargs
    ) -> VisualStyle:
        """
        Set or create the visual style configuration.

        Args:
            name: Human-readable name
            **kwargs: Style attributes

        Returns:
            The VisualStyle
        """
        if self.state.style is None:
            self.state.style = VisualStyle(
                id=str(uuid.uuid4()),
                name=name
            )
        elif name:
            self.state.style.name = name

        self._dirty = True
        return self.state.style

    def update_style(
        self,
        turn: Optional[int] = None,
        confidence: ConfidenceLevel = ConfidenceLevel.INFERRED,
        **updates
    ) -> Optional[VisualStyle]:
        """
        Update visual style attributes.

        Args:
            turn: Conversation turn for source tracking
            confidence: Confidence level
            **updates: Attribute updates

        Returns:
            Updated VisualStyle or None
        """
        style = self.state.style
        if not style:
            style = self.set_style()

        for key, value in updates.items():
            if hasattr(style, key):
                attr = Attribute(
                    value=str(value),
                    confidence=confidence,
                    source_turn=turn
                )
                setattr(style, key, attr)

        style.updated_at = datetime.utcnow()
        self._dirty = True

        return style

    # ============ Consistency Helpers ============

    def set_consistent_elements(self, description: str):
        """Set the human-readable consistent elements summary."""
        self.state.consistent_elements = description
        self._dirty = True

    def set_visual_motif(self, motif: str):
        """Set the recurring visual motif."""
        self.state.visual_motif = motif
        self._dirty = True

    # ============ Prompt Generation ============

    def get_prompt_block(
        self,
        detail_level: str = "medium",
        include_subjects: bool = True,
        include_environment: bool = True,
        include_style: bool = True
    ) -> str:
        """
        Generate a complete prompt block from the current state.

        Args:
            detail_level: "full", "medium", or "minimal"
            include_subjects: Include subject descriptions
            include_environment: Include environment description
            include_style: Include style description

        Returns:
            Formatted prompt string
        """
        return self.state.to_prompt_block(
            detail_level=detail_level,
            include_subjects=include_subjects,
            include_environment=include_environment,
            include_style=include_style
        )

    def get_subject_prompt(
        self,
        subject_id: str,
        detail_level: str = "medium"
    ) -> Optional[str]:
        """Get prompt block for a specific subject."""
        subject = self.get_subject(subject_id)
        if subject:
            return subject.to_prompt_block(detail_level)
        return None

    # ============ State Export/Import ============

    def to_dict(self) -> dict:
        """Export state as dictionary (for JSON serialization)."""
        return self.state.model_dump(mode="json")

    def from_dict(self, data: dict) -> bool:
        """
        Import state from dictionary.

        Returns:
            True if successful
        """
        try:
            self._state = VideoConsistencyState.model_validate(data)
            self._state.session_id = self.session_id  # Ensure session ID matches
            self._dirty = True
            return True
        except Exception:
            return False

    # ============ Convenience Methods ============

    def create_human_subject(
        self,
        name: str = "Main Character",
        role: str = "protagonist",
        gender: Optional[str] = None,
        age_range: Optional[str] = None,
        **kwargs
    ) -> SubjectSheet:
        """
        Convenience method to create a human subject with common attributes.

        Returns:
            Created SubjectSheet
        """
        subject = self.add_subject(
            subject_type=SubjectType.HUMAN,
            name=name,
            role=role
        )

        # Set initial human details if provided
        if subject.human_details:
            if gender:
                subject.human_details.gender = Attribute(
                    value=gender,
                    confidence=ConfidenceLevel.DEFAULT
                )
            if age_range:
                if not subject.human_details.body:
                    from .schemas import BodyDetails
                    subject.human_details.body = BodyDetails()
                subject.human_details.body.age_range = Attribute(
                    value=age_range,
                    confidence=ConfidenceLevel.DEFAULT
                )

        return subject

    def create_product_subject(
        self,
        name: str = "Product",
        category: Optional[str] = None,
        **kwargs
    ) -> SubjectSheet:
        """
        Convenience method to create a product/object subject.

        Returns:
            Created SubjectSheet
        """
        subject = self.add_subject(
            subject_type=SubjectType.OBJECT,
            name=name,
            role="product"
        )

        if category and subject.object_details:
            subject.object_details.category = Attribute(
                value=category,
                confidence=ConfidenceLevel.DEFAULT
            )

        return subject
