"""
Pydantic models for visual consistency tracking in video generation.

These schemas track subjects (humans, animals, objects), environments,
and visual styles to maintain consistency across video segments.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum
from datetime import datetime


class ConfidenceLevel(str, Enum):
    """How confident we are about an attribute value."""
    CONFIRMED = "confirmed"    # User explicitly stated
    INFERRED = "inferred"      # LLM deduced from context
    DEFAULT = "default"        # System assumption


class Attribute(BaseModel):
    """A single attribute with confidence tracking."""
    value: str
    confidence: ConfidenceLevel = ConfidenceLevel.DEFAULT
    source_turn: Optional[int] = None  # Conversation turn where this was set

    def __str__(self) -> str:
        return self.value


class SubjectType(str, Enum):
    """Type of subject in the video."""
    HUMAN = "human"
    ANIMAL = "animal"
    OBJECT = "object"


# ============ Detail Models ============

class HairDetails(BaseModel):
    """Detailed hair attributes for human subjects."""
    color: Optional[Attribute] = None
    length: Optional[Attribute] = None  # short, medium, long, bald
    style: Optional[Attribute] = None   # straight, curly, wavy, braided
    texture: Optional[Attribute] = None # fine, thick, coarse

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []
        if self.color:
            parts.append(f"{self.color.value} hair")
        if self.length and detail_level != "minimal":
            parts.append(self.length.value)
        if self.style and detail_level == "full":
            parts.append(f"{self.style.value} style")
        if self.texture and detail_level == "full":
            parts.append(f"{self.texture.value} texture")
        return " ".join(parts) if parts else ""


class FaceDetails(BaseModel):
    """Detailed facial attributes for human subjects."""
    shape: Optional[Attribute] = None       # oval, round, square, heart
    skin_tone: Optional[Attribute] = None   # fair, medium, olive, dark, etc.
    eye_color: Optional[Attribute] = None
    eye_shape: Optional[Attribute] = None   # almond, round, hooded
    nose: Optional[Attribute] = None        # small, prominent, button
    lips: Optional[Attribute] = None        # thin, full
    facial_hair: Optional[Attribute] = None # none, stubble, beard, mustache
    distinguishing_features: Optional[Attribute] = None  # freckles, scar, dimples

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []
        if self.skin_tone:
            parts.append(f"{self.skin_tone.value} skin")
        if self.eye_color and detail_level != "minimal":
            parts.append(f"{self.eye_color.value} eyes")
        if self.facial_hair and self.facial_hair.value != "none" and detail_level != "minimal":
            parts.append(f"with {self.facial_hair.value}")
        if detail_level == "full":
            if self.shape:
                parts.append(f"{self.shape.value} face")
            if self.distinguishing_features:
                parts.append(self.distinguishing_features.value)
        return ", ".join(parts) if parts else ""


class ClothingDetails(BaseModel):
    """Clothing/attire attributes."""
    upper_body: Optional[Attribute] = None   # shirt, jacket, sweater
    lower_body: Optional[Attribute] = None   # jeans, skirt, pants
    footwear: Optional[Attribute] = None     # sneakers, heels, barefoot
    accessories: Optional[Attribute] = None  # watch, glasses, hat
    style: Optional[Attribute] = None        # casual, formal, sporty
    colors: Optional[Attribute] = None       # primary color palette

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []
        if self.style:
            parts.append(f"{self.style.value} attire")
        if self.upper_body and detail_level != "minimal":
            color_prefix = f"{self.colors.value} " if self.colors and detail_level == "full" else ""
            parts.append(f"{color_prefix}{self.upper_body.value}")
        if self.lower_body and detail_level == "full":
            parts.append(self.lower_body.value)
        if self.accessories and detail_level == "full":
            parts.append(f"wearing {self.accessories.value}")
        return ", ".join(parts) if parts else ""


class BodyDetails(BaseModel):
    """Body characteristics for human subjects."""
    build: Optional[Attribute] = None     # slim, athletic, average, muscular
    height: Optional[Attribute] = None    # short, average, tall
    posture: Optional[Attribute] = None   # upright, relaxed, hunched
    age_range: Optional[Attribute] = None # child, teen, young adult, middle-aged, elderly

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []
        if self.age_range:
            parts.append(self.age_range.value)
        if self.build and detail_level != "minimal":
            parts.append(f"{self.build.value} build")
        if self.height and detail_level == "full":
            parts.append(self.height.value)
        return ", ".join(parts) if parts else ""


class HumanDetails(BaseModel):
    """All details specific to human subjects."""
    gender: Optional[Attribute] = None  # male, female, non-binary, ambiguous
    hair: Optional[HairDetails] = None
    face: Optional[FaceDetails] = None
    body: Optional[BodyDetails] = None
    clothing: Optional[ClothingDetails] = None
    expression: Optional[Attribute] = None  # neutral, happy, focused, frustrated
    pose: Optional[Attribute] = None        # sitting, standing, walking

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []

        # Gender (always include)
        if self.gender:
            parts.append(self.gender.value)

        # Body/age
        if self.body:
            body_desc = self.body.to_prompt_block(detail_level)
            if body_desc:
                parts.append(body_desc)

        # Face
        if self.face:
            face_desc = self.face.to_prompt_block(detail_level)
            if face_desc:
                parts.append(face_desc)

        # Hair
        if self.hair:
            hair_desc = self.hair.to_prompt_block(detail_level)
            if hair_desc:
                parts.append(hair_desc)

        # Clothing
        if self.clothing and detail_level != "minimal":
            clothing_desc = self.clothing.to_prompt_block(detail_level)
            if clothing_desc:
                parts.append(clothing_desc)

        # Expression and pose
        if self.expression and detail_level != "minimal":
            parts.append(f"{self.expression.value} expression")
        if self.pose and detail_level == "full":
            parts.append(self.pose.value)

        return ", ".join(parts) if parts else ""


class AnimalDetails(BaseModel):
    """Details specific to animal subjects."""
    species: Optional[Attribute] = None     # dog, cat, bird, etc.
    breed: Optional[Attribute] = None       # golden retriever, siamese, etc.
    color: Optional[Attribute] = None       # fur/feather color
    pattern: Optional[Attribute] = None     # solid, spotted, striped
    size: Optional[Attribute] = None        # small, medium, large
    features: Optional[Attribute] = None    # long ears, fluffy tail, etc.
    behavior: Optional[Attribute] = None    # calm, playful, alert

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []

        # Species/breed (always include)
        if self.breed:
            parts.append(self.breed.value)
        elif self.species:
            parts.append(self.species.value)

        # Color/pattern
        if self.color:
            parts.append(self.color.value)
        if self.pattern and detail_level != "minimal":
            parts.append(self.pattern.value)

        # Size and features
        if self.size and detail_level != "minimal":
            parts.append(f"{self.size.value} sized")
        if self.features and detail_level == "full":
            parts.append(f"with {self.features.value}")

        # Behavior
        if self.behavior and detail_level == "full":
            parts.append(f"appearing {self.behavior.value}")

        return ", ".join(parts) if parts else ""


class ObjectDetails(BaseModel):
    """Details specific to object subjects (products, items, etc.)."""
    category: Optional[Attribute] = None    # laptop, phone, chair, etc.
    brand_style: Optional[Attribute] = None # Apple-like, industrial, vintage
    material: Optional[Attribute] = None    # metal, plastic, wood, glass
    color: Optional[Attribute] = None       # primary color
    finish: Optional[Attribute] = None      # matte, glossy, brushed
    size: Optional[Attribute] = None        # compact, standard, large
    condition: Optional[Attribute] = None   # new, worn, pristine
    key_features: Optional[Attribute] = None # distinguishing visual elements

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []

        # Category (always include)
        if self.category:
            parts.append(self.category.value)

        # Style/brand
        if self.brand_style and detail_level != "minimal":
            parts.append(f"{self.brand_style.value} style")

        # Material/color/finish
        if self.color:
            parts.append(self.color.value)
        if self.material and detail_level != "minimal":
            parts.append(self.material.value)
        if self.finish and detail_level == "full":
            parts.append(f"{self.finish.value} finish")

        # Size and features
        if self.size and detail_level == "full":
            parts.append(self.size.value)
        if self.key_features and detail_level == "full":
            parts.append(self.key_features.value)

        return ", ".join(parts) if parts else ""


# ============ Main Subject Sheet ============

class SubjectSheet(BaseModel):
    """
    Unified subject sheet that handles humans, animals, and objects.
    The central schema for tracking subject visual consistency.
    """
    id: str  # Unique identifier for this subject
    name: Optional[str] = None  # Human-readable name (e.g., "Main User", "Product")
    subject_type: SubjectType
    role: Optional[str] = None  # Role in the video (protagonist, product, prop)

    # Type-specific details (only one will be populated based on subject_type)
    human_details: Optional[HumanDetails] = None
    animal_details: Optional[AnimalDetails] = None
    object_details: Optional[ObjectDetails] = None

    # Common to all subjects
    description: Optional[Attribute] = None  # Free-form description override

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        """
        Generate a prompt-ready text block describing this subject.

        Detail levels:
        - full: ~150 tokens - every detail
        - medium: ~80 tokens - key features only
        - minimal: ~30 tokens - bare essentials
        """
        # If there's a direct description override, use it
        if self.description and detail_level == "minimal":
            return self.description.value

        parts = []

        # Add role context if available
        if self.role and detail_level == "full":
            parts.append(f"[{self.role}]")

        # Type-specific details
        if self.subject_type == SubjectType.HUMAN and self.human_details:
            parts.append(self.human_details.to_prompt_block(detail_level))
        elif self.subject_type == SubjectType.ANIMAL and self.animal_details:
            parts.append(self.animal_details.to_prompt_block(detail_level))
        elif self.subject_type == SubjectType.OBJECT and self.object_details:
            parts.append(self.object_details.to_prompt_block(detail_level))

        # Add description as supplement for full detail
        if self.description and detail_level == "full":
            parts.append(f"({self.description.value})")

        return " ".join(filter(None, parts))


# ============ Environment Sheet ============

class LightingDetails(BaseModel):
    """Lighting characteristics for the environment."""
    type: Optional[Attribute] = None        # natural, artificial, mixed
    direction: Optional[Attribute] = None   # front, side, back, top, ambient
    quality: Optional[Attribute] = None     # soft, hard, diffused
    color_temp: Optional[Attribute] = None  # warm, cool, neutral
    intensity: Optional[Attribute] = None   # dim, moderate, bright
    source: Optional[Attribute] = None      # sun, window, lamp, screen glow

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []
        if self.type:
            parts.append(f"{self.type.value} lighting")
        if self.color_temp and detail_level != "minimal":
            parts.append(self.color_temp.value)
        if self.source and detail_level == "full":
            parts.append(f"from {self.source.value}")
        if self.quality and detail_level == "full":
            parts.append(self.quality.value)
        return ", ".join(parts) if parts else ""


class EnvironmentSheet(BaseModel):
    """
    Environment/setting details for visual consistency.
    Tracks location, lighting, atmosphere, and time of day.
    """
    id: str
    name: Optional[str] = None

    # Location
    setting_type: Optional[Attribute] = None     # indoor, outdoor, studio
    location: Optional[Attribute] = None         # office, home, street, park
    specific_area: Optional[Attribute] = None    # desk, living room, sidewalk

    # Atmosphere
    mood: Optional[Attribute] = None             # professional, cozy, energetic
    time_of_day: Optional[Attribute] = None      # morning, afternoon, evening, night
    weather: Optional[Attribute] = None          # sunny, cloudy, rainy (outdoor)

    # Visual elements
    lighting: Optional[LightingDetails] = None
    color_scheme: Optional[Attribute] = None     # warm earth tones, cool blues
    background_elements: Optional[Attribute] = None  # plants, monitors, windows
    depth: Optional[Attribute] = None            # shallow, medium, deep (bokeh)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        """Generate environment description for prompts."""
        parts = []

        # Location
        if self.location:
            parts.append(self.location.value)
        if self.specific_area and detail_level != "minimal":
            parts.append(self.specific_area.value)

        # Time and mood
        if self.time_of_day and detail_level != "minimal":
            parts.append(self.time_of_day.value)
        if self.mood:
            parts.append(f"{self.mood.value} atmosphere")

        # Lighting
        if self.lighting:
            lighting_desc = self.lighting.to_prompt_block(detail_level)
            if lighting_desc:
                parts.append(lighting_desc)

        # Additional details for full
        if detail_level == "full":
            if self.color_scheme:
                parts.append(self.color_scheme.value)
            if self.background_elements:
                parts.append(f"with {self.background_elements.value}")
            if self.depth:
                parts.append(f"{self.depth.value} depth of field")

        return ", ".join(filter(None, parts))


# ============ Visual Style ============

class CameraDetails(BaseModel):
    """Camera and composition style."""
    angle: Optional[Attribute] = None       # eye-level, low, high, dutch
    shot_type: Optional[Attribute] = None   # close-up, medium, wide, extreme
    movement: Optional[Attribute] = None    # static, pan, dolly, handheld
    lens: Optional[Attribute] = None        # 35mm, 50mm, wide-angle, telephoto

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        parts = []
        if self.shot_type:
            parts.append(f"{self.shot_type.value} shot")
        if self.angle and detail_level != "minimal":
            parts.append(f"{self.angle.value} angle")
        if self.lens and detail_level == "full":
            parts.append(f"{self.lens.value} lens")
        return ", ".join(parts) if parts else ""


class VisualStyle(BaseModel):
    """
    Overall visual/cinematic style for the video.
    Ensures consistent look across all frames.
    """
    id: str
    name: Optional[str] = None

    # Aesthetic
    style: Optional[Attribute] = None           # photorealistic, cinematic, stylized
    tone: Optional[Attribute] = None            # warm, cool, neutral, dramatic
    color_grade: Optional[Attribute] = None     # natural, desaturated, vibrant
    contrast: Optional[Attribute] = None        # low, medium, high

    # Camera
    camera: Optional[CameraDetails] = None

    # Technical
    aspect_ratio: Optional[Attribute] = None    # 16:9, 9:16, 1:1
    quality: Optional[Attribute] = None         # 4K, cinematic quality, etc.

    # Motifs
    visual_motif: Optional[Attribute] = None    # recurring visual element
    transition_style: Optional[Attribute] = None  # smooth, cut, morph

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_prompt_block(self, detail_level: Literal["full", "medium", "minimal"] = "medium") -> str:
        """Generate style description for prompts."""
        parts = []

        # Core style
        if self.style:
            parts.append(self.style.value)
        if self.quality and detail_level != "minimal":
            parts.append(self.quality.value)

        # Tone and color
        if self.tone:
            parts.append(f"{self.tone.value} tone")
        if self.color_grade and detail_level != "minimal":
            parts.append(f"{self.color_grade.value} color")

        # Camera
        if self.camera:
            camera_desc = self.camera.to_prompt_block(detail_level)
            if camera_desc:
                parts.append(camera_desc)

        # Motif for full
        if self.visual_motif and detail_level == "full":
            parts.append(f"with {self.visual_motif.value}")

        return ", ".join(filter(None, parts))


# ============ Video Consistency State ============

class VideoConsistencyState(BaseModel):
    """
    Complete consistency state for a video generation session.
    Combines all subjects, environment, and style into one trackable state.
    """
    id: str
    session_id: str  # Links to the video generation session

    # Core elements
    subjects: list[SubjectSheet] = Field(default_factory=list)
    environment: Optional[EnvironmentSheet] = None
    style: Optional[VisualStyle] = None

    # Consistency markers
    consistent_elements: Optional[str] = None  # Human-readable summary
    visual_motif: Optional[str] = None         # Recurring visual theme

    # State tracking
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_subject_by_id(self, subject_id: str) -> Optional[SubjectSheet]:
        """Find a subject by ID."""
        for subject in self.subjects:
            if subject.id == subject_id:
                return subject
        return None

    def get_subject_by_role(self, role: str) -> Optional[SubjectSheet]:
        """Find a subject by role."""
        for subject in self.subjects:
            if subject.role == role:
                return subject
        return None

    def get_primary_subject(self) -> Optional[SubjectSheet]:
        """Get the primary/protagonist subject."""
        return self.get_subject_by_role("protagonist") or (
            self.subjects[0] if self.subjects else None
        )

    def to_prompt_block(
        self,
        detail_level: Literal["full", "medium", "minimal"] = "medium",
        include_subjects: bool = True,
        include_environment: bool = True,
        include_style: bool = True
    ) -> str:
        """
        Generate a complete prompt block for the entire consistency state.
        Can selectively include/exclude sections.
        """
        sections = []

        # Style (often goes first in prompts)
        if include_style and self.style:
            style_block = self.style.to_prompt_block(detail_level)
            if style_block:
                sections.append(style_block)

        # Subjects
        if include_subjects and self.subjects:
            subject_blocks = []
            for subject in self.subjects:
                block = subject.to_prompt_block(detail_level)
                if block:
                    subject_blocks.append(block)
            if subject_blocks:
                sections.append(". ".join(subject_blocks))

        # Environment
        if include_environment and self.environment:
            env_block = self.environment.to_prompt_block(detail_level)
            if env_block:
                sections.append(env_block)

        # Consistent elements for full detail
        if detail_level == "full" and self.consistent_elements:
            sections.append(f"Consistent elements: {self.consistent_elements}")

        return ". ".join(filter(None, sections))
