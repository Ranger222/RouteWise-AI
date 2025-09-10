import { NextResponse } from "next/server";
import { spawn } from "node:child_process";
import path from "node:path";
import fs from "node:fs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function spawnOnce(cmd: string, args: string[], cwd: string, env: NodeJS.ProcessEnv) {
  return spawn(cmd, args, { cwd, env });
}

async function callPythonServer(query: string, opts?: { sessionId?: string; messageType?: string }): Promise<{ ok: boolean; markdown?: string; error?: string }> {
  // Ensure we always POST to /plan even if PY_BACKEND_URL is just the origin
  const base = process.env.PY_BACKEND_URL || "http://127.0.0.1:8000";
  const url = `${base.replace(/\/+$/, "")}/plan`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 1000 * 110); // 110s budget; leave 10s buffer for frontend
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query, sessionId: opts?.sessionId, messageType: opts?.messageType }),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as { markdown?: string };
    const markdown = (data?.markdown || "").toString();
    if (!markdown) throw new Error("Empty markdown from Python server");
    return { ok: true, markdown };
  } catch (e: any) {
    const isAborted = e?.name === "AbortError" || String(e).includes("aborted");
    const errorMsg = isAborted ? "Python backend timed out (>110s)" : String(e?.message || e);
    return { ok: false, error: errorMsg };
  } finally {
    clearTimeout(timer);
  }
}

async function runPython(query: string, opts?: { sessionId?: string; messageType?: string }): Promise<{ stdout: string; stderr: string; code: number | null }> {
  const projectRoot = path.resolve(process.cwd(), ".."); // routewise-ai dir
  const args = ["-m", "src.main", query, "--no-save", ...(opts?.sessionId ? ["--session-id", opts.sessionId] : []), ...(opts?.messageType ? ["--message-type", opts.messageType] : [])];

  // Choose a single best Python interpreter to avoid multi-attempt timeouts
  let chosen: [string, string[]] | null = null;
  const venvPython = path.resolve(projectRoot, ".venv", "Scripts", "python.exe");
  const parentVenvPython = path.resolve(projectRoot, "..", ".venv", "Scripts", "python.exe");
  const pyExe1 = "C:/Windows/py.exe";
  const pyExe2 = "C:/Windows/System32/py.exe";
  if (fs.existsSync(venvPython)) {
    chosen = [venvPython, args];
  } else if (fs.existsSync(parentVenvPython)) {
    chosen = [parentVenvPython, args];
  } else if (process.platform === "win32" && fs.existsSync(pyExe1)) {
    chosen = [pyExe1, ["-3", ...args]];
  } else if (process.platform === "win32" && fs.existsSync(pyExe2)) {
    chosen = [pyExe2, ["-3", ...args]];
  } else if (process.platform === "win32") {
    chosen = ["py", ["-3", ...args]]; // rely on PATH
  } else {
    chosen = ["python", args];
  }

  // Conservative overrides to keep responses snappy in dev
  const childEnv: NodeJS.ProcessEnv = {
    ...process.env,
    ROUTEWISE_MODE: "mcp",
    MAX_RESULTS: process.env.MAX_RESULTS || "3", // tighten for speed
    REQUEST_TIMEOUT: process.env.REQUEST_TIMEOUT || "12",
    PYTHONIOENCODING: "utf-8",
    PYTHONUNBUFFERED: "1",
    FAST_MODE: "1",
    SEARCH_PROVIDER: process.env.SEARCH_PROVIDER || "duckduckgo",
  };

  let stdout = "";
  let stderr = "";
  let code: number | null = 1;

  try {
    await new Promise<void>((resolve) => setImmediate(resolve));
    const [cmd, a] = chosen!;

    const child = spawnOnce(cmd, a, projectRoot, childEnv);
    stdout = "";
    stderr = "";
    code = null;

    // Hard kill after 90s to prevent long hangs
    let timedOut = false;
    const killTimer = setTimeout(() => {
      timedOut = true;
      try { child.kill(); } catch {}
    }, 1000 * 90);

    const result = await new Promise<{ stdout: string; stderr: string; code: number | null }>((resolve) => {
      child.stdout.on("data", (d) => (stdout += d.toString()));
      child.stderr.on("data", (d) => (stderr += d.toString()));
      child.on("close", (c) => {
        clearTimeout(killTimer);
        if (timedOut) {
          resolve({ stdout, stderr: (stderr || "") + "\n[RouteWise] Planner timed out after 90s.", code: c ?? 124 });
        } else {
          resolve({ stdout, stderr, code: c });
        }
      });
      child.on("error", (err) => {
        clearTimeout(killTimer);
        resolve({ stdout: "", stderr: `Failed to start ${cmd}: ${String(err?.message || err)}`, code: 1 });
      });
    });

    code = result.code;
    stdout = result.stdout;
    stderr = result.stderr;

    if (code === 0) {
      console.log(`[api/plan] Succeeded with ${cmd}`);
    } else {
      console.warn(`[api/plan] ${cmd} exited code ${code}. stderr(last 200):`, (stderr || "").slice(-200));
    }
  } catch (e: any) {
    stderr += `\nSpawn error for ${String(chosen?.[0])}: ${String(e?.message || e)}`;
    code = 1;
  }

  return { stdout, stderr, code };
}

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const query = (body?.query ?? "").toString().trim();
    const sessionId = (body?.sessionId ?? "").toString().trim();
    if (!query) return NextResponse.json({ error: "Missing 'query'" }, { status: 400 });

    // Quick path for greetings or trivial inputs to avoid long planner runs
    const lc = query.toLowerCase();
    if (lc === "hi" || lc === "hello" || lc === "hey" || lc.length < 4) {
      const md = `**Hi!** I can plan trips for you. Try something like:\n\n- 2-day weekend in Jaipur on a budget\n- 7-day Europe rail trip for 2, mid-range\n- Goa beach getaway, 3 days, nightlife\n\nTell me destination, days, budget, and interests.`;
      return NextResponse.json({ markdown: md });
    }

    // Choose message type heuristically for now; frontend may pass an explicit intent later
    const isRefine = /refine|adjust|change|reduce|increase|why|add|remove|swap/i.test(query);
    const messageType = isRefine ? "refinement" : "text";

    // 1) Try persistent Python backend first
    const pythonServer = await callPythonServer(query, { sessionId, messageType });
    if (pythonServer.ok && pythonServer.markdown) {
      return NextResponse.json({ markdown: pythonServer.markdown });
    }

    // If the Python server timed out, return a quick fallback immediately to stay within client timeout
    if (!pythonServer.ok && (pythonServer.error || '').toLowerCase().includes('timed out')) {
      const debug = (pythonServer.error || '').slice(-800).replace(/`/g, "\u0060");
      const md = `# Quick Plan\n\nYou asked: **${query}**\n\n> The backend is busy and timed out. Showing a lightweight plan; please try again or refine your query.\n\n## Day 1\n- Arrive and check in\n- Explore key sights downtown\n- Dinner at a well-reviewed local spot\n\n## Day 2\n- Morning activity aligned to your interests\n- Afternoon stroll/relaxation\n- Optional nightlife or cultural event\n\n<!-- debug: ${debug} -->`;
      return NextResponse.json({ markdown: md });
    }

    // 2) Fallback to spawning the CLI once to keep current behavior working
    const { stdout, stderr, code } = await runPython(query, { sessionId, messageType });

    if (code === 0) {
      const marker = "=== Final Itinerary (Markdown) ===";
      const idx = stdout.indexOf(marker);
      const markdown = idx >= 0 ? stdout.slice(idx + marker.length).trim() : stdout.trim();
      return NextResponse.json({ markdown });
    }

    // Fallback: return a lightweight plan so the UI stays responsive, with a hidden debug trailer
    const debug = ((pythonServer.error || "") + "\n" + (stderr || stdout)).slice(-800).replace(/`/g, "\u0060");
    const md = `# Quick Plan\n\nYou asked: **${query}**\n\n> Using a lightweight fallback because the planner failed.\n\n## Day 1\n- Arrive and check in\n- Explore key sights downtown\n- Dinner at a well-reviewed local spot\n\n## Day 2\n- Morning activity aligned to your interests\n- Afternoon stroll/relaxation\n- Optional nightlife or cultural event\n\n<!-- debug: ${debug} -->`;
    return NextResponse.json({ markdown: md });
  } catch (e: any) {
    return NextResponse.json({ error: "Server error", details: String(e?.message || e) }, { status: 500 });
  }
}