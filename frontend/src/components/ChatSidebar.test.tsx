import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ChatSidebar } from "@/components/ChatSidebar";
import { api } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  api: {
    chatAI: vi.fn(),
    clearChatAI: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

describe("ChatSidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.clearChatAI).mockResolvedValue({ cleared: true });
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it("renders the empty state prompt", () => {
    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    expect(screen.getByText(/ask the ai/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Message input")).toBeInTheDocument();
    expect(screen.getByLabelText("Send message")).toBeInTheDocument();
  });

  it("send button is disabled when input is empty", () => {
    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    expect(screen.getByLabelText("Send message")).toBeDisabled();
  });

  it("send button enables when input has text", async () => {
    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Message input"), "hello");
    expect(screen.getByLabelText("Send message")).toBeEnabled();
  });

  it("displays user message and AI response after sending", async () => {
    vi.mocked(api.chatAI).mockResolvedValue({
      response: "Hello! How can I help?",
      actions_executed: 0,
    });

    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Message input"), "hello");
    await userEvent.click(screen.getByLabelText("Send message"));

    expect(screen.getByText("hello")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText("Hello! How can I help?")).toBeInTheDocument()
    );
  });

  it("clears the input after sending", async () => {
    vi.mocked(api.chatAI).mockResolvedValue({
      response: "Done",
      actions_executed: 0,
    });

    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    const input = screen.getByLabelText("Message input");
    await userEvent.type(input, "hello");
    await userEvent.click(screen.getByLabelText("Send message"));

    expect(input).toHaveValue("");
  });

  it("calls onBoardChanged when AI executes actions", async () => {
    vi.mocked(api.chatAI).mockResolvedValue({
      response: "Created a card for you.",
      actions_executed: 1,
    });

    const onBoardChanged = vi.fn();
    render(<ChatSidebar onBoardChanged={onBoardChanged} />);
    await userEvent.type(screen.getByLabelText("Message input"), "add a card");
    await userEvent.click(screen.getByLabelText("Send message"));

    await waitFor(() => expect(onBoardChanged).toHaveBeenCalledTimes(1));
  });

  it("does not call onBoardChanged when AI executes no actions", async () => {
    vi.mocked(api.chatAI).mockResolvedValue({
      response: "Here is some info.",
      actions_executed: 0,
    });

    const onBoardChanged = vi.fn();
    render(<ChatSidebar onBoardChanged={onBoardChanged} />);
    await userEvent.type(screen.getByLabelText("Message input"), "what columns do I have?");
    await userEvent.click(screen.getByLabelText("Send message"));

    await waitFor(() => screen.getByText("Here is some info."));
    expect(onBoardChanged).not.toHaveBeenCalled();
  });

  it("shows an error message when the API call fails", async () => {
    vi.mocked(api.chatAI).mockRejectedValue(new Error("network error"));

    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Message input"), "hello");
    await userEvent.click(screen.getByLabelText("Send message"));

    await waitFor(() =>
      expect(screen.getByText(/failed to get a response/i)).toBeInTheDocument()
    );
  });

  it("sends message on Enter key", async () => {
    vi.mocked(api.chatAI).mockResolvedValue({
      response: "Got it.",
      actions_executed: 0,
    });

    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Message input"), "hello{Enter}");

    expect(api.chatAI).toHaveBeenCalledWith("hello");
  });

  it("does not send on Shift+Enter", async () => {
    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    await userEvent.type(
      screen.getByLabelText("Message input"),
      "line one{Shift>}{Enter}{/Shift}line two"
    );

    expect(api.chatAI).not.toHaveBeenCalled();
  });

  it("clears messages and calls clearChatAI on Clear", async () => {
    vi.mocked(api.chatAI).mockResolvedValue({
      response: "Hello!",
      actions_executed: 0,
    });

    render(<ChatSidebar onBoardChanged={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("Message input"), "hi");
    await userEvent.click(screen.getByLabelText("Send message"));
    await waitFor(() => screen.getByText("Hello!"));

    await userEvent.click(screen.getByLabelText("Clear conversation"));

    expect(api.clearChatAI).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Hello!")).not.toBeInTheDocument();
    expect(screen.queryByText("hi")).not.toBeInTheDocument();
  });
});
