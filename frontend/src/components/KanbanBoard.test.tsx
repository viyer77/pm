import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import type { ApiBoard } from "@/lib/api";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    getBoard: vi.fn(),
    renameColumn: vi.fn(),
    createCard: vi.fn(),
    updateCard: vi.fn(),
    deleteCard: vi.fn(),
    moveCard: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

const getBoardResponse = (): ApiBoard => ({
  id: 1,
  title: "My Project Board",
  columns: [
    { id: 1, board_id: 1, title: "Backlog", position: 0 },
    { id: 2, board_id: 1, title: "Discovery", position: 1 },
    { id: 3, board_id: 1, title: "In Progress", position: 2 },
    { id: 4, board_id: 1, title: "Review", position: 3 },
    { id: 5, board_id: 1, title: "Done", position: 4 },
  ],
  cards: [
    {
      id: 1,
      column_id: 1,
      title: "Align roadmap themes",
      description: "Draft quarterly themes with impact statements and metrics.",
      position: 0,
    },
    {
      id: 2,
      column_id: 2,
      title: "Prototype analytics view",
      description: "Sketch initial dashboard layout and key drill-downs.",
      position: 0,
    },
  ],
});

const getFirstColumn = async () => {
  await waitFor(() => expect(screen.getAllByTestId(/column-/i)).toHaveLength(5));
  return screen.getAllByTestId(/column-/i)[0];
};

describe("KanbanBoard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getBoard).mockResolvedValue(getBoardResponse());
    vi.mocked(api.renameColumn).mockResolvedValue({
      id: 1,
      board_id: 1,
      title: "Renamed",
      position: 0,
    });
    vi.mocked(api.createCard).mockResolvedValue({
      id: 99,
      column_id: 1,
      title: "New card",
      description: "Notes",
      position: 1,
    });
    vi.mocked(api.deleteCard).mockResolvedValue({ success: true });
    vi.mocked(api.moveCard).mockResolvedValue({
      id: 1,
      column_id: 1,
      title: "Align roadmap themes",
      description: "Draft quarterly themes with impact statements and metrics.",
      position: 0,
    });
  });

  it("renders board data from the backend", async () => {
    render(<KanbanBoard />);
    expect(await screen.findByRole("heading", { name: "My Project Board" })).toBeInTheDocument();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column via API", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const input = within(column).getByLabelText("Column title");

    await userEvent.clear(input);
    await userEvent.type(input, "Renamed");
    await userEvent.tab();

    expect(api.renameColumn).toHaveBeenCalledWith(1, "Renamed");
    await waitFor(() => expect(input).toHaveValue("Renamed"));
  });

  it("adds and removes a card via API", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(api.createCard).toHaveBeenCalledWith(1, "New card", "Notes");
    await waitFor(() => expect(within(column).getByText("New card")).toBeInTheDocument());

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(api.deleteCard).toHaveBeenCalledWith(99);
  });

  it("edits a card via API", async () => {
    render(<KanbanBoard />);
    const column = await getFirstColumn();
    await userEvent.click(
      within(column).getByRole("button", { name: /edit align roadmap themes/i })
    );

    const titleInput = within(column).getByDisplayValue("Align roadmap themes");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated from test");
    await userEvent.click(within(column).getByText("Save", { selector: "button" }));

    expect(api.updateCard).toHaveBeenCalledWith(1, {
      title: "Updated from test",
      description: "Draft quarterly themes with impact statements and metrics.",
    });
    await waitFor(() =>
      expect(within(column).getByText("Updated from test")).toBeInTheDocument()
    );
  });
});
