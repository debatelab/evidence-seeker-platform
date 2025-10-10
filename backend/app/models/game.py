from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.user import User
from app.core.database import Base


class GameSession(Base):
    """Model for individual game sessions"""

    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    level_id = Column(Integer, ForeignKey("game_levels.id"), nullable=False)
    score = Column(Integer, default=0)
    max_combo = Column(Integer, default=0)
    coins_earned = Column(Integer, default=0)
    distance_traveled = Column(Float, default=0.0)
    game_duration = Column(Integer, default=0)  # in seconds
    is_completed = Column(Boolean, default=False)
    died_reason = Column(String(50))  # ground, pipe, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="game_sessions")
    level = relationship("GameLevel", back_populates="game_sessions")
    events = relationship(
        "GameEvent", back_populates="session", cascade="all, delete-orphan"
    )


class GameLevel(Base):
    """Model for game levels"""

    __tablename__ = "game_levels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    difficulty = Column(String(20), default="normal")  # easy, normal, hard, expert
    background_image = Column(String(500))
    pipe_gap = Column(Float, default=150.0)  # gap between pipes
    pipe_frequency = Column(Float, default=2.0)  # seconds between pipes
    bird_gravity = Column(Float, default=0.5)
    bird_flap_strength = Column(Float, default=-8.0)
    scroll_speed = Column(Float, default=2.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    game_sessions = relationship("GameSession", back_populates="level")
    high_scores = relationship(
        "HighScore", back_populates="level", cascade="all, delete-orphan"
    )


class GameEvent(Base):
    """Model for tracking game events during gameplay"""

    __tablename__ = "game_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    event_type = Column(
        String(50), nullable=False
    )  # flap, collision, coin_collect, etc.
    event_data = Column(JSON)  # additional event-specific data
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("GameSession", back_populates="events")


class HighScore(Base):
    """Model for storing high scores"""

    __tablename__ = "high_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    level_id = Column(Integer, ForeignKey("game_levels.id"), nullable=False)
    score = Column(Integer, nullable=False)
    max_combo = Column(Integer, default=0)
    coins_earned = Column(Integer, default=0)
    distance_traveled = Column(Float, default=0.0)
    game_duration = Column(Integer, default=0)
    achieved_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="high_scores")
    level = relationship("GameLevel", back_populates="high_scores")


class Achievement(Base):
    """Model for game achievements"""

    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    icon = Column(String(500))
    condition_type = Column(String(50), nullable=False)  # score, combo, coins, etc.
    condition_value = Column(Integer, nullable=False)
    reward_coins = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserAchievement(Base):
    """Model for tracking user achievements"""

    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    achieved_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")


class CoinShopItem(Base):
    """Model for items available in coin shop"""

    __tablename__ = "coin_shop_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    icon = Column(String(500))
