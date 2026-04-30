#!/usr/bin/env node

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const APP_DIR = path.join(os.homedir(), ".llmeter", "app");
const MENUBAR_VENV = path.join(os.homedir(), ".llmeter", "menubar-venv");
const APP_BUNDLE = "/Applications/Llmeter.app";
const SERVICE = "com.llmeter.monitor";
const MENUBAR_SERVICE = "com.llmeter.menubar";
const MENUBAR_PLIST = path.join(os.homedir(), "Library", "LaunchAgents", `${MENUBAR_SERVICE}.plist`);
const DEFAULT_HOST = process.env.LLMETER_HOST || "127.0.0.1";
const DEFAULT_PORT = process.env.LLMETER_PORT || "4001";
const URL = `http://${DEFAULT_HOST}:${DEFAULT_PORT}`;

const SOURCE_DIR = path.resolve(__dirname, "..");
const EXCLUDED = new Set([
  ".git",
  ".venv",
  ".venv-menubar",
  "data",
  "node_modules",
  ".pytest_cache",
  "__pycache__",
  "build",
  "dist",
]);

function log(message = "") {
  process.stdout.write(`${message}\n`);
}

function fail(message, code = 1) {
  process.stderr.write(`llmeter: ${message}\n`);
  process.exit(code);
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: options.capture ? "pipe" : "inherit",
    encoding: "utf8",
    ...options,
  });
  if (result.error) {
    return { ok: false, status: 1, stdout: "", stderr: result.error.message };
  }
  return {
    ok: result.status === 0,
    status: result.status || 0,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
  };
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (EXCLUDED.has(entry.name)) continue;
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(from, to);
    } else if (entry.isSymbolicLink()) {
      try {
        fs.symlinkSync(fs.readlinkSync(from), to);
      } catch (error) {
        if (error.code !== "EEXIST") throw error;
      }
    } else if (entry.isFile()) {
      fs.copyFileSync(from, to);
    }
  }
}

function cleanAppDir() {
  fs.rmSync(APP_DIR, { recursive: true, force: true });
  fs.mkdirSync(APP_DIR, { recursive: true });
}

function ensureMac() {
  if (process.platform !== "darwin") {
    fail("llmeter currently supports macOS only. Re-run with --no-menubar on Linux/Windows for the dashboard alone (also Mac-only at the moment).");
  }
}

function ensurePython() {
  const candidates = [
    process.env.LLMETER_PYTHON,
    "python3.14",
    "python3.13",
    "python3.12",
    "python3.11",
    "/opt/homebrew/bin/python3",
    "/usr/local/bin/python3",
    "python3",
  ].filter(Boolean);
  for (const candidate of candidates) {
    const result = run(candidate, ["-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"], {
      capture: true,
    });
    if (result.ok) return candidate;
  }
  fail("Python 3.11 or newer is required. Install Python, then run npx llmeter install again.");
}

function detectLogs() {
  const checks = [
    ["Claude Code", path.join(os.homedir(), ".claude", "projects")],
    ["Codex", path.join(os.homedir(), ".codex", "sessions")],
  ];
  return checks.map(([name, dir]) => ({
    name,
    dir,
    exists: fs.existsSync(dir),
  }));
}

function install(options = {}) {
  ensureMac();
  const python = ensurePython();
  const installDashboard = options.dashboard !== false;
  const installMenubar = options.menubar !== false;

  log("llmeter");
  log("");
  log(`✓ found ${python}`);

  // Always make sure source is staged at APP_DIR; dashboard install relies on it,
  // and the menu bar LaunchAgent runs the installed module from this tree.
  if (installDashboard) {
    log(`✓ installing dashboard at ${APP_DIR}`);
    stopServiceQuiet();
    stopPortListenersQuiet();
    if (path.resolve(SOURCE_DIR) !== path.resolve(APP_DIR)) {
      cleanAppDir();
      copyDir(SOURCE_DIR, APP_DIR);
    } else {
      fs.mkdirSync(APP_DIR, { recursive: true });
    }
    const env = {
      ...process.env,
      LLMETER_HOST: DEFAULT_HOST,
      LLMETER_PORT: DEFAULT_PORT,
      LLMETER_PYTHON: python,
    };
    const installer = path.join(APP_DIR, "scripts", "install.sh");
    const result = run("bash", [installer], { cwd: APP_DIR, env });
    if (!result.ok) fail("dashboard install failed");
  } else {
    log("• skipping dashboard install (--menubar-only)");
    log("  note: ingest currently runs inside the dashboard service. Without it,");
    log("  the menu bar app reads an empty/stale SQLite. Tradeoff documented in SPEC.md.");
    if (path.resolve(SOURCE_DIR) !== path.resolve(APP_DIR) && !fs.existsSync(APP_DIR)) {
      cleanAppDir();
      copyDir(SOURCE_DIR, APP_DIR);
    }
  }

  if (installMenubar) {
    log("✓ installing menu bar");
    const env = {
      ...process.env,
      LLMETER_PYTHON: python,
    };
    const result = run("bash", [path.join(APP_DIR, "scripts", "install_menubar.sh")], {
      cwd: APP_DIR,
      env,
    });
    if (!result.ok) fail("menu bar install failed");
  } else {
    log("• skipping menu bar app (--no-menubar)");
  }

  for (const item of detectLogs()) {
    log(`${item.exists ? "✓" : "•"} ${item.exists ? "found" : "did not find"} ${item.name} logs at ${item.dir}`);
  }

  log("");
  if (installDashboard) log(`Dashboard: ${URL}`);
  if (installMenubar) log("Menu bar: look for ⚡ in the macOS menu bar (top right)");
  if (installDashboard && options.open !== false) openDashboard();
}

function openDashboard() {
  if (process.platform === "darwin") {
    run("open", [URL], { capture: true });
  } else {
    log(URL);
  }
}

function serviceStatus() {
  if (process.platform !== "darwin") return { ok: false, output: "launchd unavailable on this platform" };
  const domain = `gui/${process.getuid()}`;
  const result = run("launchctl", ["print", `${domain}/${SERVICE}`], { capture: true });
  return {
    ok: result.ok,
    output: result.ok ? result.stdout : result.stderr || result.stdout,
  };
}

function stopServiceQuiet() {
  if (process.platform !== "darwin") return;
  const plist = path.join(os.homedir(), "Library", "LaunchAgents", `${SERVICE}.plist`);
  const domain = `gui/${process.getuid()}`;
  if (fs.existsSync(plist)) {
    run("launchctl", ["bootout", domain, plist], { capture: true });
  }
}

function stopPortListenersQuiet() {
  if (process.platform !== "darwin") return;
  const result = run("lsof", [`-tiTCP:${DEFAULT_PORT}`, "-sTCP:LISTEN"], { capture: true });
  if (!result.ok || !result.stdout.trim()) return;
  for (const pid of result.stdout.trim().split(/\s+/)) {
    const ps = run("ps", ["-p", pid, "-o", "command="], { capture: true });
    if (ps.stdout.includes("-m llmeter")) {
      run("kill", [pid], { capture: true });
    }
  }
}

function checkHttp(callback) {
  const req = http.get(`${URL}/api/today`, (res) => {
    res.resume();
    callback(res.statusCode >= 200 && res.statusCode < 300);
  });
  req.on("error", () => callback(false));
  req.setTimeout(1500, () => {
    req.destroy();
    callback(false);
  });
}

function menubarInstalled() {
  return fs.existsSync(MENUBAR_PLIST) || fs.existsSync(MENUBAR_VENV) || fs.existsSync(APP_BUNDLE);
}

function menubarRunning() {
  if (process.platform !== "darwin") return false;
  const r = run("pgrep", ["-f", "llmeter.menubar|/Applications/Llmeter.app"], { capture: true });
  return r.ok && r.stdout.trim().length > 0;
}

function menubarAgentLoaded() {
  if (process.platform !== "darwin") return false;
  const domain = `gui/${process.getuid()}`;
  const r = run("launchctl", ["print", `${domain}/${MENUBAR_SERVICE}`], { capture: true });
  return r.ok;
}

function startMenubar() {
  if (process.platform !== "darwin") return false;
  const domain = `gui/${process.getuid()}`;
  if (menubarAgentLoaded()) {
    const r = run("launchctl", ["kickstart", "-k", `${domain}/${MENUBAR_SERVICE}`], { capture: true });
    if (r.ok) return true;
  }
  // Fallback: bootstrap the agent if its plist is on disk, then kickstart
  if (fs.existsSync(MENUBAR_PLIST)) {
    run("launchctl", ["bootstrap", domain, MENUBAR_PLIST], { capture: true });
    const r = run("launchctl", ["kickstart", "-k", `${domain}/${MENUBAR_SERVICE}`], { capture: true });
    if (r.ok) return true;
  }
  // Last resort: open the .app directly
  if (menubarInstalled()) {
    const r = run("open", ["-a", "Llmeter"], { capture: true });
    return r.ok;
  }
  return false;
}

function status() {
  log("llmeter status");
  log("");
  log(`app source: ${fs.existsSync(APP_DIR) ? APP_DIR : "not installed"}`);
  const svc = serviceStatus();
  log(`dashboard service: ${svc.ok ? "running/loaded" : "not loaded"}`);
  const mbState = menubarInstalled()
    ? (menubarRunning() ? "installed and running" : "installed (not running)")
    : "not installed";
  log(`menu bar app: ${mbState}`);
  log(`menu bar LaunchAgent: ${menubarAgentLoaded() ? "loaded" : "not loaded"}`);
  for (const item of detectLogs()) {
    log(`${item.name}: ${item.exists ? item.dir : "not found"}`);
  }
  checkHttp((ok) => {
    log(`dashboard: ${ok ? URL : "not responding"}`);
  });
}

function start() {
  ensureMac();
  const plist = path.join(os.homedir(), "Library", "LaunchAgents", `${SERVICE}.plist`);
  const domain = `gui/${process.getuid()}`;
  if (fs.existsSync(plist)) {
    run("launchctl", ["bootstrap", domain, plist], { capture: true });
    run("launchctl", ["kickstart", "-k", `${domain}/${SERVICE}`], { capture: true });
    log(`✓ started llmeter at ${URL}`);
  }
  if (menubarInstalled()) {
    if (startMenubar()) {
      log("✓ launched menu bar app");
    }
  }
  if (!fs.existsSync(plist) && !menubarInstalled()) {
    fail("llmeter is not installed yet. Run: npx llmeter install");
  }
}

function stop() {
  ensureMac();
  stopServiceQuiet();
  stopPortListenersQuiet();
  run("osascript", ["-e", 'tell application "Llmeter" to quit'], { capture: true });
  run("pkill", ["-x", "Llmeter"], { capture: true });
  run("pkill", ["-f", "llmeter.menubar"], { capture: true });
  log("✓ stopped llmeter");
}

function uninstall() {
  stop();
  const menubarUninstaller = path.join(APP_DIR, "scripts", "uninstall_menubar.sh");
  if (fs.existsSync(menubarUninstaller)) {
    run("bash", [menubarUninstaller], { capture: false });
  } else if (process.platform === "darwin") {
    run("osascript", ["-e", 'tell application "Llmeter" to quit'], { capture: true });
    if (fs.existsSync(MENUBAR_PLIST)) {
      run("launchctl", ["bootout", `gui/${process.getuid()}`, MENUBAR_PLIST], { capture: true });
      fs.rmSync(MENUBAR_PLIST, { force: true });
    }
    run("pkill", ["-x", "Llmeter"], { capture: true });
    run("pkill", ["-f", "llmeter.menubar"], { capture: true });
    fs.rmSync(APP_BUNDLE, { recursive: true, force: true });
    fs.rmSync(MENUBAR_VENV, { recursive: true, force: true });
  }
  fs.rmSync(APP_DIR, { recursive: true, force: true });
  log(`✓ removed ${APP_DIR}`);
}

function help() {
  log(`llmeter

Usage:
  npx llmeter              Install and open the dashboard + menu bar app
  npx llmeter install      Install dashboard service + menu bar app
  npx llmeter open         Open the dashboard
  npx llmeter status       Show service, log, dashboard, and menu bar status
  npx llmeter start        Start the launchd service and menu bar app
  npx llmeter stop         Stop the launchd service and menu bar app
  npx llmeter uninstall    Remove dashboard, menu bar app, LaunchAgent, and ~/.llmeter

Options:
  --no-menubar            Install only the dashboard (skip menu bar)
  --menubar-only          Install only the menu bar app (skip the dashboard service).
                          NOTE: ingest currently runs inside the dashboard service,
                          so the menu bar will show no new data without it.
                          See SPEC.md "Open Questions".
  --no-open               Install without opening the browser
  --version, -v           Print the llmeter version
  --help                  Show this help
`);
}

function version() {
  const pkg = require(path.join(__dirname, "..", "package.json"));
  log(pkg.version);
}

const args = process.argv.slice(2);
if (args.includes("--help") || args.includes("-h")) {
  help();
  process.exit(0);
}
if (args.includes("--version") || args.includes("-v")) {
  version();
  process.exit(0);
}

const command = args.find((arg) => !arg.startsWith("-")) || "install";
const noOpen = args.includes("--no-open");
const noMenubar = args.includes("--no-menubar");
const menubarOnly = args.includes("--menubar-only");

if (noMenubar && menubarOnly) {
  fail("--no-menubar and --menubar-only are mutually exclusive");
}

switch (command) {
  case "install":
    install({
      open: !noOpen,
      menubar: !noMenubar,
      dashboard: !menubarOnly,
    });
    break;
  case "open":
    openDashboard();
    break;
  case "status":
    status();
    break;
  case "start":
    start();
    break;
  case "stop":
    stop();
    break;
  case "uninstall":
    uninstall();
    break;
  case "help":
    help();
    break;
  default:
    help();
    fail(`unknown command: ${command}`);
}
