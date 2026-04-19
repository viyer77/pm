"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { api, ApiError, type ApiBoard, type ApiCard } from "@/lib/api";
import { createId, moveCard, type BoardData, type Card } from "@/lib/kanban";

type KanbanBoardProps = {
  onUnauthorized?: () => void;
  reloadTrigger?: number;
};

const toColumnUiId = (id: number) => `col-${id}`;
const toCardUiId = (id: number) => `card-${id}`;

const parseBackendId = (value: string, prefix: "col" | "card"): number | null => {
  const match = value.match(new RegExp(`^${prefix}-(\\d+)$`));
  if (!match) {
    return null;
  }
  const parsed = Number(match[1]);
  return Number.isInteger(parsed) ? parsed : null;
};

const normalizeDetails = (description: string) => description || "No details yet.";

const fromApiBoard = (data: ApiBoard): BoardData => {
  const sortedColumns = [...data.columns].sort((a, b) => a.position - b.position);
  const cardsByColumn = new Map<number, ApiCard[]>();
  for (const card of data.cards) {
    const group = cardsByColumn.get(card.column_id) ?? [];
    group.push(card);
    cardsByColumn.set(card.column_id, group);
  }

  const cards: Record<string, Card> = {};
  for (const card of data.cards) {
    const uiId = toCardUiId(card.id);
    cards[uiId] = {
      id: uiId,
      title: card.title,
      details: normalizeDetails(card.description),
    };
  }

  return {
    id: data.id,
    title: data.title,
    columns: sortedColumns.map((column) => {
      const columnCards = [...(cardsByColumn.get(column.id) ?? [])].sort(
        (a, b) => a.position - b.position
      );
      return {
        id: toColumnUiId(column.id),
        title: column.title,
        cardIds: columnCards.map((card) => toCardUiId(card.id)),
      };
    }),
    cards,
  };
};

const toErrorMessage = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 0) {
      return "Network issue. Please try again.";
    }
    if (error.status === 401) {
      return "Session expired. Please sign in again.";
    }
    return `Request failed (${error.status}).`;
  }
  return "Something went wrong. Please try again.";
};

export const KanbanBoard = ({ onUnauthorized, reloadTrigger }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const loadBoard = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await api.getBoard();
      setBoard(fromApiBoard(data));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized?.();
        return;
      }
      setLoadError(toErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    void loadBoard();
  }, [loadBoard, reloadTrigger]);

  const runOptimisticUpdate = async (
    nextBoard: BoardData,
    mutate: () => Promise<unknown>,
    rollbackBoard: BoardData
  ) => {
    setActionError(null);
    setBoard(nextBoard);
    try {
      await mutate();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        onUnauthorized?.();
        return;
      }
      setBoard(rollbackBoard);
      setActionError(toErrorMessage(error));
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!board || !over || active.id === over.id) {
      return;
    }

    const activeId = active.id as string;
    const overId = over.id as string;
    const nextColumns = moveCard(board.columns, activeId, overId);
    const nextBoard: BoardData = { ...board, columns: nextColumns };

    const movedCardBackendId = parseBackendId(activeId, "card");
    if (movedCardBackendId === null) {
      setBoard(nextBoard);
      return;
    }

    const targetColumn = nextColumns.find((column) => column.cardIds.includes(activeId));
    const targetPosition = targetColumn?.cardIds.indexOf(activeId) ?? 0;
    const targetColumnBackendId = targetColumn
      ? parseBackendId(targetColumn.id, "col")
      : null;

    if (targetColumnBackendId === null) {
      return;
    }

    void runOptimisticUpdate(
      nextBoard,
      () => api.moveCard(movedCardBackendId, targetColumnBackendId, targetPosition),
      board
    );
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!board) {
      return;
    }

    const columnBackendId = parseBackendId(columnId, "col");
    if (columnBackendId === null) {
      return;
    }

    const nextBoard: BoardData = {
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    };

    void runOptimisticUpdate(
      nextBoard,
      () => api.renameColumn(columnBackendId, title),
      board
    );
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (!board) {
      return;
    }

    const columnBackendId = parseBackendId(columnId, "col");
    if (columnBackendId === null) {
      return;
    }

    const tempId = createId("card-temp");
    const nextBoard: BoardData = {
      ...board,
      cards: {
        ...board.cards,
        [tempId]: {
          id: tempId,
          title,
          details: details || "No details yet.",
        },
      },
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, tempId] }
          : column
      ),
    };

    setActionError(null);
    setBoard(nextBoard);

    void (async () => {
      try {
        const created = await api.createCard(columnBackendId, title, details);
        const persistedUiId = toCardUiId(created.id);
        setBoard((current) => {
          if (!current) {
            return current;
          }
          const tempCard = current.cards[tempId];
          if (!tempCard) {
            return current;
          }

          const updatedCards = { ...current.cards };
          delete updatedCards[tempId];
          updatedCards[persistedUiId] = {
            id: persistedUiId,
            title: created.title,
            details: normalizeDetails(created.description),
          };

          const updatedColumns = current.columns.map((column) => ({
            ...column,
            cardIds: column.cardIds.map((cardId) =>
              cardId === tempId ? persistedUiId : cardId
            ),
          }));

          return { ...current, cards: updatedCards, columns: updatedColumns };
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          onUnauthorized?.();
          return;
        }
        setBoard(board);
        setActionError(toErrorMessage(error));
      }
    })();
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!board) {
      return;
    }

    const nextBoard: BoardData = {
      ...board,
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => id !== cardId)
      ),
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: column.cardIds.filter((id) => id !== cardId) }
          : column
      ),
    };

    const cardBackendId = parseBackendId(cardId, "card");
    if (cardBackendId === null) {
      setBoard(nextBoard);
      return;
    }

    void runOptimisticUpdate(nextBoard, () => api.deleteCard(cardBackendId), board);
  };

  const handleUpdateCard = (cardId: string, title: string, details: string) => {
    if (!board) {
      return;
    }
    const currentCard = board.cards[cardId];
    if (!currentCard) {
      return;
    }

    const nextBoard: BoardData = {
      ...board,
      cards: {
        ...board.cards,
        [cardId]: {
          ...currentCard,
          title,
          details: details || "No details yet.",
        },
      },
    };

    const cardBackendId = parseBackendId(cardId, "card");
    if (cardBackendId === null) {
      setBoard(nextBoard);
      return;
    }

    void runOptimisticUpdate(
      nextBoard,
      () => api.updateCard(cardBackendId, { title, description: details }),
      board
    );
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (isLoading && !board) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <p className="text-sm font-semibold text-[var(--gray-text)]">Loading board...</p>
      </div>
    );
  }

  if (loadError && !board) {
    return (
      <div className="mx-auto mt-10 max-w-xl rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm text-red-700">{loadError}</p>
        <button
          type="button"
          onClick={() => {
            setIsLoading(true);
            void loadBoard();
          }}
          className="mt-4 rounded-full bg-[var(--secondary-purple)] px-5 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!board) {
    return null;
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                {board.title}
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
          {actionError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {actionError}
            </div>
          ) : null}
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds
                  .map((cardId) => board.cards[cardId])
                  .filter((card): card is Card => Boolean(card))}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
                onUpdateCard={handleUpdateCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>
    </div>
  );
};
