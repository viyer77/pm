# Frontend: Kanban Studio

A React 19 + Next.js 16 single-board Kanban application with drag-and-drop card management, built with TypeScript and Tailwind CSS.

## Architecture Overview

The frontend is a client-side Next.js app (to be served by FastAPI backend) that manages a single Kanban board with 5 fixed columns. State is managed locally via React hooks with initial data defined in [lib/kanban.ts](lib/kanban.ts). The application is fully functional as a demo and ready for backend integration.

## Components

### `KanbanBoard` ([src/components/KanbanBoard.tsx](src/components/KanbanBoard.tsx))
The main orchestrator component. Responsibilities:
- Manages global board state (`BoardData`), including columns and cards
- Handles drag-and-drop via `@dnd-kit/core` library
- Exposes handlers for rename, add card, and delete card operations
- Renders decorative gradient overlays in the background
- Displays a header with board title, description, and column pills
- Wraps `KanbanColumn` components inside `DndContext`

**Key handlers:**
- `handleDragStart`: Tracks the dragged card ID
- `handleDragEnd`: Calls `moveCard()` utility and updates state
- `handleRenameColumn`: Updates column title
- `handleAddCard`: Creates a new card with generated ID
- `handleDeleteCard`: Removes card from cards and column

**Drag-and-drop setup:**
- Uses `PointerSensor` with 6px activation distance to distinguish drag from click
- Uses `closestCorners` collision detection
- Renders `DragOverlay` with `KanbanCardPreview` during drag

### `KanbanColumn` ([src/components/KanbanColumn.tsx](src/components/KanbanColumn.tsx))
Represents a single column in the Kanban board.
- Receives column data and card list as props
- Uses `@dnd-kit/sortable` for reorderable card context
- Renders an editable column title (inline text input)
- Shows card count badge
- Displays all cards via `KanbanCard` components
- Shows empty state placeholder when column has no cards
- Contains `NewCardForm` at the bottom for adding cards
- Applies yellow ring highlight when column is a valid drop target

### `KanbanCard` ([src/components/KanbanCard.tsx](src/components/KanbanCard.tsx))
Individual card component with drag capability.
- Uses `useSortable` hook to integrate with dnd-kit
- Displays card title and details
- Includes "Remove" button for deletion
- Applies visual feedback during drag (reduced opacity, enhanced shadow)
- Accepts keyboard/pointer interactions via dnd-kit attributes and listeners

### `KanbanCardPreview` ([src/components/KanbanCardPreview.tsx](src/components/KanbanCardPreview.tsx))
Rendered during drag in `DragOverlay`. Shows a preview of the card being dragged with visual elevation (enhanced shadow) to indicate it's floating above the board.

### `NewCardForm` ([src/components/NewCardForm.tsx](src/components/NewCardForm.tsx))
Modal form for creating new cards in a column.
- Toggled by "Add a card" button
- Form state: `{ title: string, details: string }`
- Validates that title is not empty/whitespace only
- Trims whitespace from inputs before submission
- "Add card" button uses purple accent color (submit/CTA styling)
- "Cancel" button closes form without saving

## Data Model

Defined in [lib/kanban.ts](lib/kanban.ts):

```typescript
type Card = {
  id: string;
  title: string;
  details: string;
};

type Column = {
  id: string;
  title: string;
  cardIds: string[];  // References to Card IDs
};

type BoardData = {
  columns: Column[];
  cards: Record<string, Card>;  // Normalized card lookup
};
```

**Initial data:** `initialData` includes 5 columns (Backlog, Discovery, In Progress, Review, Done) with 8 sample cards.

**ID generation:** `createId(prefix)` generates unique IDs using a combination of random hex and current timestamp: `{prefix}-{random}{timestamp}`.

## Utilities

### `moveCard(columns, activeId, overId)`
Core drag-and-drop logic. Handles:
- Reordering cards within the same column (respects insertion position)
- Moving cards between columns
- Dropping cards directly onto a column (appends to end)
- Returns new columns array with updated card positions

## Key Libraries & Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 16.1.6 | React framework, static generation, dev server |
| `react` | 19.2.3 | UI framework |
| `react-dom` | 19.2.3 | React DOM rendering |
| `@dnd-kit/core` | 6.3.1 | Low-level drag-and-drop primitives |
| `@dnd-kit/sortable` | 10.0.0 | Reorderable list support |
| `@dnd-kit/utilities` | 3.2.2 | Transform utilities for dnd-kit |
| `tailwindcss` | 4 | Utility-first CSS framework |
| `clsx` | 2.1.1 | Conditional CSS class merging |
| `typescript` | 5 | Type safety |

**Dev dependencies:** Testing (vitest, playwright, @testing-library), linting (eslint), type definitions (@types/react, @types/node).

## Styling & Color Scheme

### Design System (CSS Variables)

All colors defined as CSS custom properties in [src/app/globals.css](src/app/globals.css):

| Variable | Hex Value | Usage |
|----------|-----------|-------|
| `--accent-yellow` | `#ecad0a` | Accent lines, highlights, badges, focus indicators |
| `--primary-blue` | `#209dd7` | Links, section headers, add card button text |
| `--secondary-purple` | `#753991` | Submit buttons (Add Card CTA) |
| `--navy-dark` | `#032147` | Main headings, primary text |
| `--gray-text` | `#888888` | Supporting text, labels, secondary info |
| `--surface` | `#f7f8fb` | Body background (light blue-tint) |
| `--surface-strong` | `#ffffff` | Card and column backgrounds (white) |
| `--stroke` | `rgba(3, 33, 71, 0.08)` | Border color with transparency |
| `--shadow` | `0 18px 40px rgba(3, 33, 71, 0.12)` | Depth shadow (dark navy at 12% opacity) |

### Fonts

- **Display font:** Space Grotesk (headings, bold titles)
- **Body font:** Manrope (body text, details)
- Both imported from Google Fonts in [src/app/layout.tsx](src/app/layout.tsx)

### Component-level Styling

- Uses Tailwind CSS utility classes with custom CSS variables
- `clsx` for conditional class application (e.g., drag state styling)
- Rounded corners: `2xl` (16px) for cards, `3xl` (24px) for columns, `full` for buttons
- Shadows consistent via `--shadow` variable
- Focus states on inputs use `--primary-blue` border color

## Tests

### Unit Tests

**Location:** [src/lib/kanban.test.ts](src/lib/kanban.test.ts), [src/components/KanbanBoard.test.tsx](src/components/KanbanBoard.test.tsx)

**Coverage:**
- `moveCard()` utility: reordering within column, cross-column moves, column drop target
- `KanbanBoard` component: renders 5 columns, renames column, adds and removes card

**Testing tools:** Vitest, React Testing Library, user-event

**Run:** `npm run test:unit` or `npm run test:unit:watch`

### End-to-End Tests

**Location:** [tests/kanban.spec.ts](tests/kanban.spec.ts)

**Coverage:**
- Page loads with "Kanban Studio" heading and 5 columns
- Add card form submission with title and details
- Drag card from one column to another using Playwright's mouse API

**Testing tools:** Playwright

**Run:** `npm run test:e2e`

**Run all tests:** `npm run test:all`

## Implemented Functionality

### ✅ Drag and Drop
- Cards can be dragged within a column to reorder
- Cards can be dragged across columns
- Columns highlight with yellow ring when they are valid drop targets
- Cards show reduced opacity and enhanced shadow while dragging
- Uses dnd-kit for accessible, pointer/keyboard-friendly implementation

### ✅ Column Management
- 5 fixed columns (Backlog, Discovery, In Progress, Review, Done)
- Inline editable column titles
- Card count badge per column
- Empty state message ("Drop a card here") when column is empty

### ✅ Card Operations
- **Create:** "Add a card" button opens form with title and details fields
- **Read:** Card title and details displayed on card component
- **Update:** (Not yet implemented; cards are immutable after creation)
- **Delete:** "Remove" button deletes card from column and global state

### ✅ UI/UX Polish
- Decorative gradient overlays (blue and purple radial gradients in background)
- Smooth transitions and animations during drag
- Accessible form validation (title required, non-empty)
- Clear visual feedback (hover states, focus indicators)
- Responsive layout: grid auto-adjusts for screen size

### ❌ Not Yet Implemented (MVP Phase 2)
- Backend API integration
- User authentication
- Multi-user support
- Card editing (update title/details)
- Card details modal/expanded view
- Persistence to database
- AI chat sidebar feature
- Real-time collaboration

## Build & Development

### Scripts
```bash
npm run dev           # Start dev server (localhost:3000)
npm run build         # Build for production
npm run start         # Run production build
npm run lint          # Run ESLint
npm run test:unit    # Run unit tests
npm run test:unit:watch  # Run unit tests in watch mode
npm run test:e2e     # Run e2e tests
npm run test:all     # Run all tests
```

### TypeScript Configuration
- Target: ES2017
- Strict mode enabled
- Path alias: `@/*` → `./src/*`

### Next.js Configuration
Minimal config ([next.config.ts](next.config.ts)). No custom features needed for MVP.

## File Structure

```
src/
  app/
    layout.tsx        # Root layout, font setup
    page.tsx          # Entry point (renders KanbanBoard)
    globals.css       # CSS variables and global styles
  components/
    KanbanBoard.tsx   # Main orchestrator
    KanbanColumn.tsx  # Column container
    KanbanCard.tsx    # Card component
    KanbanCardPreview.tsx  # Drag preview
    NewCardForm.tsx   # Card creation form
  lib/
    kanban.ts         # Data model and utilities
    kanban.test.ts    # Unit tests
tests/
  kanban.spec.ts      # E2E tests
```

## Known Limitations (MVP)

- No card editing after creation
- State not persisted (resets on page refresh)
- No multi-board support
- No user context (single hardcoded user)
- Drag-and-drop works only with mouse/touch, limited keyboard support via dnd-kit defaults
