from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import Board, Card, Column, User, get_db, utcnow_naive
from .auth import VALID_USERNAME, require_authenticated

router = APIRouter(prefix="/api", tags=["boards"], dependencies=[Depends(require_authenticated)])


class CardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    column_id: int
    title: str
    description: str
    position: int


class ColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: int
    title: str
    position: int


class BoardResponse(BaseModel):
    id: int
    title: str
    columns: list[ColumnResponse]
    cards: list[CardResponse]


class RenameColumnRequest(BaseModel):
    column_id: int
    title: str = Field(min_length=1, max_length=255)


class CreateCardRequest(BaseModel):
    column_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str = ""


class UpdateCardRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class MoveCardRequest(BaseModel):
    column_id: int
    position: int = Field(ge=0)


class DeleteResponse(BaseModel):
    success: bool


def _get_current_user(db: Session, request: Request) -> User:
    require_authenticated(request)
    user = db.query(User).filter(User.username == VALID_USERNAME).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def _get_user_board(db: Session, user: User) -> Board:
    board = db.query(Board).filter(Board.user_id == user.id).first()
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board


def _build_board_response(db: Session, board: Board) -> BoardResponse:
    columns = db.query(Column).filter(Column.board_id == board.id).order_by(Column.position.asc()).all()
    column_ids = [column.id for column in columns]

    cards_query = db.query(Card).filter(Card.column_id.in_(column_ids)) if column_ids else db.query(Card).filter(False)
    cards = cards_query.order_by(Card.column_id.asc(), Card.position.asc()).all()

    return BoardResponse(id=board.id, title=board.title, columns=columns, cards=cards)


def _get_column_for_board(db: Session, board_id: int, column_id: int) -> Column:
    column = db.query(Column).filter(Column.board_id == board_id, Column.id == column_id).first()
    if column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found")
    return column


def _get_card_for_board(db: Session, board_id: int, card_id: int) -> Card:
    card = (
        db.query(Card)
        .join(Column, Card.column_id == Column.id)
        .filter(Column.board_id == board_id, Card.id == card_id)
        .first()
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return card


@router.get("/boards", response_model=BoardResponse)
def get_board(request: Request, db: Session = Depends(get_db)) -> BoardResponse:
    user = _get_current_user(db, request)
    board = _get_user_board(db, user)
    return _build_board_response(db, board)


@router.post("/columns", response_model=ColumnResponse)
def rename_column(payload: RenameColumnRequest, request: Request, db: Session = Depends(get_db)) -> ColumnResponse:
    user = _get_current_user(db, request)
    board = _get_user_board(db, user)
    column = _get_column_for_board(db, board.id, payload.column_id)
    column.title = payload.title.strip()
    db.commit()
    db.refresh(column)
    return column


@router.post("/cards", response_model=CardResponse, status_code=status.HTTP_201_CREATED)
def create_card(payload: CreateCardRequest, request: Request, db: Session = Depends(get_db)) -> CardResponse:
    user = _get_current_user(db, request)
    board = _get_user_board(db, user)
    column = _get_column_for_board(db, board.id, payload.column_id)

    next_position = db.query(func.coalesce(func.max(Card.position) + 1, 0)).filter(Card.column_id == column.id).scalar()
    card = Card(
        column_id=column.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        position=next_position,
        updated_at=utcnow_naive(),
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.put("/cards/{card_id}", response_model=CardResponse)
def update_card(
    card_id: int, payload: UpdateCardRequest, request: Request, db: Session = Depends(get_db)
) -> CardResponse:
    if payload.title is None and payload.description is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes requested")

    user = _get_current_user(db, request)
    board = _get_user_board(db, user)
    card = _get_card_for_board(db, board.id, card_id)

    if payload.title is not None:
        card.title = payload.title.strip()
    if payload.description is not None:
        card.description = payload.description.strip()
    card.updated_at = utcnow_naive()

    db.commit()
    db.refresh(card)
    return card


@router.delete("/cards/{card_id}", response_model=DeleteResponse)
def delete_card(card_id: int, request: Request, db: Session = Depends(get_db)) -> DeleteResponse:
    user = _get_current_user(db, request)
    board = _get_user_board(db, user)
    card = _get_card_for_board(db, board.id, card_id)

    column_id = card.column_id
    db.delete(card)
    db.flush()

    remaining_cards = db.query(Card).filter(Card.column_id == column_id).order_by(Card.position.asc()).all()
    for idx, remaining in enumerate(remaining_cards):
        remaining.position = idx
    db.commit()

    return DeleteResponse(success=True)


@router.put("/cards/{card_id}/move", response_model=CardResponse)
def move_card(
    card_id: int, payload: MoveCardRequest, request: Request, db: Session = Depends(get_db)
) -> CardResponse:
    user = _get_current_user(db, request)
    board = _get_user_board(db, user)
    card = _get_card_for_board(db, board.id, card_id)
    target_column = _get_column_for_board(db, board.id, payload.column_id)

    source_column_id = card.column_id
    source_position = card.position
    now = utcnow_naive()
    stage_offset = 1000

    try:
        if source_column_id == target_column.id:
            column_size = db.query(func.count(Card.id)).filter(Card.column_id == source_column_id).scalar() or 0
            target_index = min(payload.position, max(column_size - 1, 0))
            if target_index == source_position:
                return card

            # Move the card out of the active position range to avoid unique collisions.
            db.execute(
                update(Card)
                .where(Card.id == card.id)
                .values(position=-1, updated_at=now)
            )

            if target_index > source_position:
                db.execute(
                    update(Card)
                    .where(
                        Card.column_id == source_column_id,
                        Card.position >= source_position + 1,
                        Card.position <= target_index,
                    )
                    .values(position=Card.position + stage_offset, updated_at=now)
                )
                db.execute(
                    update(Card)
                    .where(
                        Card.column_id == source_column_id,
                        Card.position >= source_position + 1 + stage_offset,
                        Card.position <= target_index + stage_offset,
                    )
                    .values(position=Card.position - (stage_offset + 1), updated_at=now)
                )
            else:
                db.execute(
                    update(Card)
                    .where(
                        Card.column_id == source_column_id,
                        Card.position >= target_index,
                        Card.position <= source_position - 1,
                    )
                    .values(position=Card.position + stage_offset, updated_at=now)
                )
                db.execute(
                    update(Card)
                    .where(
                        Card.column_id == source_column_id,
                        Card.position >= target_index + stage_offset,
                        Card.position <= source_position - 1 + stage_offset,
                    )
                    .values(position=Card.position - (stage_offset - 1), updated_at=now)
                )

            db.execute(
                update(Card)
                .where(Card.id == card.id)
                .values(position=target_index, updated_at=now)
            )
        else:
            target_count = db.query(func.count(Card.id)).filter(Card.column_id == target_column.id).scalar() or 0
            target_index = min(payload.position, target_count)

            # Park moved card first so source/target reindexing can happen safely.
            db.execute(
                update(Card)
                .where(Card.id == card.id)
                .values(position=-1, updated_at=now)
            )

            # Close source gap.
            db.execute(
                update(Card)
                .where(Card.column_id == source_column_id, Card.position > source_position)
                .values(position=Card.position + stage_offset, updated_at=now)
            )
            db.execute(
                update(Card)
                .where(Card.column_id == source_column_id, Card.position >= source_position + 1 + stage_offset)
                .values(position=Card.position - (stage_offset + 1), updated_at=now)
            )

            # Open target slot.
            db.execute(
                update(Card)
                .where(Card.column_id == target_column.id, Card.position >= target_index)
                .values(position=Card.position + stage_offset, updated_at=now)
            )
            db.execute(
                update(Card)
                .where(Card.column_id == target_column.id, Card.position >= target_index + stage_offset)
                .values(position=Card.position - (stage_offset - 1), updated_at=now)
            )

            # Move card into target slot.
            db.execute(
                update(Card)
                .where(Card.id == card.id)
                .values(column_id=target_column.id, position=target_index, updated_at=now)
            )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to reorder cards")

    moved_card = _get_card_for_board(db, board.id, card_id)
    return moved_card
