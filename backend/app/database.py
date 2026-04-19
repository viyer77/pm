from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Generator

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DEFAULT_USERNAME = "user"
DEFAULT_PASSWORD_HASH = "password"
DEFAULT_BOARD_TITLE = "My Project Board"
DEFAULT_COLUMN_TITLES = ["Backlog", "Discovery", "In Progress", "Review", "Done"]
DEFAULT_CARD_SEED = {
    "Backlog": [
        ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics."),
        ("Gather customer signals", "Review support tags, sales notes, and churn feedback."),
    ],
    "Discovery": [("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.")],
    "In Progress": [
        ("Refine status language", "Standardize column labels and tone across the board."),
        ("Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    ],
    "Review": [("QA micro-interactions", "Verify hover, focus, and loading states.")],
    "Done": [
        ("Ship marketing page", "Final copy approved and asset pack delivered."),
        ("Close onboarding sprint", "Document release notes and share internally."),
    ],
}


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.datetime("now"), nullable=False
    )

    boards: Mapped[list["Board"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.datetime("now"), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="boards")
    columns: Mapped[list["Column"]] = relationship(back_populates="board", cascade="all, delete-orphan")


class Column(Base):
    __tablename__ = "columns"
    __table_args__ = (UniqueConstraint("board_id", "position", name="uq_columns_board_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.datetime("now"), nullable=False
    )

    board: Mapped[Board] = relationship(back_populates="columns")
    cards: Mapped[list["Card"]] = relationship(back_populates="column", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (UniqueConstraint("column_id", "position", name="uq_cards_column_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    column_id: Mapped[int] = mapped_column(ForeignKey("columns.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.datetime("now"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.datetime("now"), nullable=False
    )

    column: Mapped[Column] = relationship(back_populates="cards")


def _build_database_url() -> str:
    configured = os.getenv("DATABASE_URL")
    if configured:
        return configured

    # database.py lives at /app/app/database.py in the container, so parents[1] is /app.
    root = Path(__file__).resolve().parents[1]
    db_path = root / "data" / "pm.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


DATABASE_URL = _build_database_url()
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_defaults(db: Session) -> None:
    user = db.query(User).filter(User.username == DEFAULT_USERNAME).first()
    if user is None:
        user = User(username=DEFAULT_USERNAME, password_hash=DEFAULT_PASSWORD_HASH)
        db.add(user)
        db.flush()

    board = db.query(Board).filter(Board.user_id == user.id).first()
    if board is None:
        board = Board(user_id=user.id, title=DEFAULT_BOARD_TITLE)
        db.add(board)
        db.flush()

    existing_columns = db.query(Column).filter(Column.board_id == board.id).count()
    if existing_columns == 0:
        for idx, title in enumerate(DEFAULT_COLUMN_TITLES):
            db.add(Column(board_id=board.id, title=title, position=idx))
        db.flush()

    existing_cards = (
        db.query(Card)
        .join(Column, Card.column_id == Column.id)
        .filter(Column.board_id == board.id)
        .count()
    )
    if existing_cards == 0:
        columns_by_title = {
            column.title: column
            for column in db.query(Column).filter(Column.board_id == board.id).all()
        }
        for title, cards in DEFAULT_CARD_SEED.items():
            column = columns_by_title.get(title)
            if column is None:
                continue
            for idx, (card_title, description) in enumerate(cards):
                db.add(
                    Card(
                        column_id=column.id,
                        title=card_title,
                        description=description,
                        position=idx,
                        updated_at=utcnow_naive(),
                    )
                )
    db.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _seed_defaults(db)


def reset_db_for_tests() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        _seed_defaults(db)
