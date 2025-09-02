import { NextResponse } from "next/server";
import { spawn } from "node:child_process";
import path from "node:path";
import fs from "node:fs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function spawnOnce(cmd: string, args: string[], cwd: string, env: NodeJS.ProcessEnv) {
  return spawn(cmd, args, { cwd, env });
}

async function runPython(query: string): Promise<{ stdout: string; stderr: string; code: number | null }> {
  const projectRoot = path.resolve(process.cwd(), ".."); // routewise-ai dir
  const args = ["-m", "src.main", query, "--no-save"];

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
    MAX_RESULTS: process.env.MAX_RESULTS || "5",
    REQUEST_TIMEOUT: process.env.REQUEST_TIMEOUT || "12",
    PYTHONIOENCODING: "utf-8",
    FAST_MODE: "1",
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

    // Hard kill after 60s to prevent long hangs
    let timedOut = false;
    const killTimer = setTimeout(() => {
      timedOut = true;
      try { child.kill(); } catch {}
    }, 1000 * 60);

    const result = await new Promise<{ stdout: string; stderr: string; code: number | null }>((resolve) => {
      child.stdout.on("data", (d) => (stdout += d.toString()));
      child.stderr.on("data", (d) => (stderr += d.toString()));
      child.on("close", (c) => {
        clearTimeout(killTimer);
        if (timedOut) {
          resolve({ stdout, stderr: stderr + "\n[RouteWise] Planner timed out after 60s.", code: c ?? 124 });
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
    if (!query) return NextResponse.json({ error: "Missing 'query'" }, { status: 400 });

    // Quick path for greetings or trivial inputs to avoid long planner runs
    const lc = query.toLowerCase();
    if (lc === "hi" || lc === "hello" || lc === "hey" || lc.length < 4) {
      const md = `**Hi!** I can plan trips for you. Try something like:\n\n- 2-day weekend in Jaipur on a budget\n- 7-day Europe rail trip for 2, mid-range\n- Goa beach getaway, 3 days, nightlife\n\nTell me destination, days, budget, and interests.`;
      return NextResponse.json({ markdown: md });
    }

    // Always attempt the real planner first so .env in the Python project is honored
    const { stdout, stderr, code } = await runPython(query);

    if (code === 0) {
      const marker = "=== Final Itinerary (Markdown) ===";
      const idx = stdout.indexOf(marker);
      const markdown = idx >= 0 ? stdout.slice(idx + marker.length).trim() : stdout.trim();
      return NextResponse.json({ markdown });
    }

    // Fallback: return a lightweight plan so the UI stays responsive, with a hidden debug trailer
    const debug = (stderr || stdout).slice(-800).replace(/`/g, "\u0060");
    const md = `# Quick Plan\n\nYou asked: **${query}**\n\n> Using a lightweight fallback because the planner failed.\n\n## Day 1\n- Arrive and check in\n- Explore key sights downtown\n- Dinner at a well-reviewed local spot\n\n## Day 2\n- Morning activity aligned to your interests\n- Afternoon stroll/relaxation\n- Optional nightlife or cultural event\n\n<!-- debug: ${debug} -->\n`;
    return NextResponse.json({ markdown: md });
  } catch (e: any) {
    return NextResponse.json({ error: "Server error", details: String(e?.message || e) }, { status: 500 });
  }
}