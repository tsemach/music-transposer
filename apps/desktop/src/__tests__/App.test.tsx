import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App, type AppProps } from "../App";
import { createMockTransport, SAMPLE_RESULT, type MockScript } from "../backend/mockTransport";

interface Sent {
  id: number;
  cmd: string;
  params?: Record<string, unknown>;
}

function setup(script: MockScript = {}, overrides: Partial<AppProps> = {}) {
  const sent: Sent[] = [];
  let transports = 0;
  const createTransport = async () => {
    transports += 1;
    const transport = createMockTransport({ stepMs: 1, ...script });
    const write = transport.write.bind(transport);
    transport.write = async (data) => {
      sent.push(JSON.parse(data) as Sent);
      return write(data);
    };
    return transport;
  };
  const props: AppProps = {
    createTransport,
    pickPdf: async () => "/music/שיר.pdf",
    pickExecutable: async () => null,
    pickFolder: async () => null,
    openPath: vi.fn(async () => undefined),
    revealPath: vi.fn(async () => undefined),
    ...overrides,
  };
  render(<App {...props} />);
  return { user: userEvent.setup(), sent, props, transportCount: () => transports };
}

async function choosePdf(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: /choose pdf/i }));
  await screen.findByText("שיר.pdf");
}

const pipelineRequests = (sent: Sent[]) => sent.filter((request) => request.cmd === "pipeline");

beforeEach(() => localStorage.clear());

test("starts in a starting state, then reports the engine and the tools as ready", async () => {
  setup();

  expect(screen.getByRole("status")).toHaveTextContent("Starting engine");
  expect(await screen.findByText("Engine ready")).toBeInTheDocument();
  expect(await screen.findByText("Audiveris: found")).toBeInTheDocument();
  expect(await screen.findByText("MuseScore: found")).toBeInTheDocument();
});

test("convert is disabled until a pdf is chosen", async () => {
  const { user } = setup();
  await screen.findByText("Engine ready");
  expect(screen.getByRole("button", { name: "Convert" })).toBeDisabled();

  await choosePdf(user);

  expect(screen.getByRole("button", { name: "Convert" })).toBeEnabled();
});

test("a conversion shows progress and then the result card", async () => {
  const { user, sent } = setup({ stepMs: 30 });
  await screen.findByText("Engine ready");
  await choosePdf(user);

  await user.click(screen.getByRole("button", { name: "Convert" }));

  expect(await screen.findByRole("progressbar")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Tenor part ready" })).toBeInTheDocument();
  expect(screen.getByText("Up a perfect 4th (same sounding pitch)")).toBeInTheDocument();
  expect(screen.getByText("1 thing to check in the original")).toBeInTheDocument();
  expect(screen.getByText("Gymnopedie.tenor.pdf")).toBeInTheDocument();
  expect(screen.getByText("/music", { exact: false })).toBeInTheDocument();
  expect(pipelineRequests(sent)[0]?.params).toMatchObject({ pdf: "/music/שיר.pdf", source: "alto", register: "auto" });
});

test("result buttons open the pdf and reveal the folder", async () => {
  const { user, props } = setup();
  await screen.findByText("Engine ready");
  await choosePdf(user);
  await user.click(screen.getByRole("button", { name: "Convert" }));
  await screen.findByRole("heading", { name: "Tenor part ready" });

  await user.click(screen.getByRole("button", { name: "Open PDF" }));
  await user.click(screen.getByRole("button", { name: "Show in folder" }));

  expect(props.openPath).toHaveBeenCalledWith(SAMPLE_RESULT.pdf);
  expect(props.revealPath).toHaveBeenCalledWith(SAMPLE_RESULT.pdf);
});

test("a failing open or reveal tells the user instead of doing nothing", async () => {
  const { user } = setup(
    {},
    {
      openPath: vi.fn(async () => Promise.reject(new Error("no viewer"))),
      revealPath: vi.fn(async () => Promise.reject(new Error("no file manager"))),
    },
  );
  await screen.findByText("Engine ready");
  await choosePdf(user);
  await user.click(screen.getByRole("button", { name: "Convert" }));
  await screen.findByRole("heading", { name: "Tenor part ready" });

  await user.click(screen.getByRole("button", { name: "Open PDF" }));
  expect(await screen.findByText("Could not open the PDF: no viewer")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Show in folder" }));
  expect(await screen.findByText("Could not show the folder: no file manager")).toBeInTheDocument();
});

test("a non-pdf choice shows a message and does not enable convert", async () => {
  const { user } = setup({}, { pickPdf: async () => "/music/photo.png" });
  await screen.findByText("Engine ready");

  await user.click(screen.getByRole("button", { name: /choose pdf/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Please choose a PDF file.");
  expect(screen.getByRole("button", { name: "Convert" })).toBeDisabled();
});

test("a validation failure lists the findings and Convert anyway resends with force", async () => {
  let calls = 0;
  const findings = [{ check: "empty-measure", severity: "error" as const, measure: "34", message: "measure has no notes or rests" }];
  const { user, sent } = setup({
    outcome: () => {
      calls += 1;
      return calls === 1
        ? { type: "error", code: "validation_failed", message: "invalid", details: { findings } }
        : { type: "result", result: SAMPLE_RESULT };
    },
  });
  await screen.findByText("Engine ready");
  await choosePdf(user);

  await user.click(screen.getByRole("button", { name: "Convert" }));

  expect(await screen.findByRole("heading", { name: "Problems found in the scanned music" })).toBeInTheDocument();
  expect(screen.getByText(/measure has no notes or rests/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Convert anyway" }));
  await screen.findByRole("heading", { name: "Tenor part ready" });
  expect(pipelineRequests(sent).map((request) => request.params?.force)).toEqual([false, true]);
});

test("a missing tool is flagged and Locate saves the chosen path and rechecks", async () => {
  const { user, sent } = setup(
    { doctor: { audiveris: null, musescore: "/m/MuseScore" } },
    { pickExecutable: async () => "/custom/Audiveris" },
  );
  expect(await screen.findByText("Audiveris: not found")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Locate Audiveris…" }));

  await waitFor(() =>
    expect(sent.filter((request) => request.cmd === "doctor").at(-1)?.params).toEqual({
      audiveris: "/custom/Audiveris",
    }),
  );
  expect(localStorage.getItem("ascurix.settings")).toContain("/custom/Audiveris");
});

test("cancel returns to a usable idle state", async () => {
  const { user } = setup({ stepMs: 100 });
  await screen.findByText("Engine ready");
  await choosePdf(user);
  await user.click(screen.getByRole("button", { name: "Convert" }));

  await user.click(await screen.findByRole("button", { name: "Cancel" }));

  expect(await screen.findByRole("button", { name: "Convert" })).toBeEnabled();
  expect(screen.queryByRole("heading", { name: /part ready/ })).not.toBeInTheDocument();
});

test("a double click starts only one job", async () => {
  const { user, sent } = setup({ stepMs: 50 });
  await screen.findByText("Engine ready");
  await choosePdf(user);

  await user.dblClick(screen.getByRole("button", { name: "Convert" }));
  await screen.findByRole("heading", { name: "Tenor part ready" });

  expect(pipelineRequests(sent)).toHaveLength(1);
});

test("a crashing engine shows a restart button and restart recovers", async () => {
  let calls = 0;
  const { user, transportCount } = setup({
    outcome: () => {
      calls += 1;
      return calls === 1 ? { type: "crash" } : { type: "result", result: SAMPLE_RESULT };
    },
  });
  await screen.findByText("Engine ready");
  await choosePdf(user);

  await user.click(screen.getByRole("button", { name: "Convert" }));

  expect(await screen.findByText("The engine stopped unexpectedly.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Restart" }));
  expect(await screen.findByText("Engine ready")).toBeInTheDocument();
  expect(transportCount()).toBe(2);
});

test("the last chosen direction is restored from settings", async () => {
  localStorage.setItem("ascurix.settings", JSON.stringify({ source: "tenor", register: "auto" }));
  setup();

  expect(await screen.findByRole("radio", { name: "Tenor → Alto" })).toBeChecked();
});

function fakePdfLoader() {
  const loaded: string[] = [];
  const loadPdf = vi.fn(async (path: string) => {
    loaded.push(path);
    return {
      pageAspects: [1.4, 1.4, 1.4],
      renderPage: () => ({ cancel: () => undefined, done: Promise.resolve() }),
      destroy: () => undefined,
    };
  });
  return { loadPdf, loaded };
}

test("choosing a pdf displays its pages", async () => {
  const { loadPdf, loaded } = fakePdfLoader();
  const { user } = setup({}, { loadPdf });
  await screen.findByText("Engine ready");
  expect(screen.getByRole("button", { name: "Open a PDF to begin" })).toBeInTheDocument();

  await choosePdf(user);

  expect(await screen.findAllByLabelText(/^Page \d$/)).toHaveLength(3);
  expect(loaded).toEqual(["/music/שיר.pdf"]);
});

test("the open button in the empty viewer also chooses a pdf", async () => {
  const { loadPdf } = fakePdfLoader();
  const { user } = setup({}, { loadPdf });

  await user.click(await screen.findByRole("button", { name: "Open a PDF to begin" }));

  expect(await screen.findAllByLabelText(/^Page \d$/)).toHaveLength(3);
});

test("splitting the view shows a second pane that continues the same document", async () => {
  const { loadPdf } = fakePdfLoader();
  const { user } = setup({}, { loadPdf });
  await choosePdf(user);
  expect(screen.queryByRole("region", { name: "Second pane" })).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Side by side" }));

  expect(screen.getByRole("region", { name: "Second pane" })).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: "Continue reading" })).toBeChecked();
  expect(screen.getByRole("separator", { name: "Resize panes" })).toBeInTheDocument();
  expect(loadPdf).toHaveBeenCalledTimes(1);
});

test("a finished conversion opens the transposed pdf next to the original", async () => {
  const { loadPdf, loaded } = fakePdfLoader();
  const { user } = setup({}, { loadPdf });
  await screen.findByText("Engine ready");
  await choosePdf(user);

  await user.click(screen.getByRole("button", { name: "Convert" }));
  await screen.findByRole("heading", { name: "Tenor part ready" });

  expect(await screen.findByRole("region", { name: "Second pane" })).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: "Second pane document" })).toHaveValue("transposed");
  expect(loaded).toContain(SAMPLE_RESULT.pdf);
});

test("a pdf that cannot be read is reported in the viewer", async () => {
  const loadPdf = vi.fn(async () => Promise.reject(new Error("corrupt file")));
  const { user } = setup({}, { loadPdf });

  await choosePdf(user);

  expect(await screen.findByText("Could not display the PDF: corrupt file")).toBeInTheDocument();
});

test("the side panel can be hidden to give the music the whole window", async () => {
  const { user } = setup();
  await screen.findByText("Engine ready");

  await user.click(screen.getByRole("button", { name: "Hide side panel" }));

  expect(screen.queryByRole("button", { name: "Convert" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Show side panel" }));
  expect(screen.getByRole("button", { name: "Convert" })).toBeInTheDocument();
});
