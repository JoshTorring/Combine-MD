const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs/promises");
const { execFile } = require("child_process");

const OUTDIR_NAME = "combined_output_folder";
const TMPDIR_NAME = "_tmp_md_flat";
const OUTPUT_FORMATS = ["rtf", "docx", "md"];

const resolvePython = () => {
  const envPython = process.env.PYTHON || process.env.PYTHON_PATH;
  if (envPython) {
    return envPython;
  }
  return process.platform === "win32" ? "python" : "python3";
};

const runCommand = (command, args, options = {}) =>
  new Promise((resolve, reject) => {
    execFile(command, args, options, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(stderr || error.message));
        return;
      }
      resolve({ stdout, stderr });
    });
  });

const createWindow = () => {
  const win = new BrowserWindow({
    width: 1000,
    height: 720,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
    },
  });

  win.loadFile(path.join(__dirname, "index.html"));
};

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

ipcMain.handle("select-vault", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory"],
    title: "Select Obsidian Vault",
  });
  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

ipcMain.handle("list-folders", async (_event, vaultPath) => {
  const entries = await fs.readdir(vaultPath, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => name !== OUTDIR_NAME)
    .sort((a, b) => a.localeCompare(b));
});

ipcMain.handle("run-combine", async (_event, payload) => {
  const { vaultPath, includeFolders, outputFormat } = payload;
  if (!OUTPUT_FORMATS.includes(outputFormat)) {
    throw new Error(`Unsupported output format: ${outputFormat}`);
  }

  const ignoreFolders = includeFolders.skip
    ? includeFolders.skip
    : includeFolders.all.filter((name) => !includeFolders.selected.includes(name));

  const combineScript = path.join(__dirname, "..", "combine_md.py");
  const pythonCmd = resolvePython();
  const combineArgs = [
    combineScript,
    vaultPath,
    "--outdir-name",
    OUTDIR_NAME,
    "--tmpdir-name",
    TMPDIR_NAME,
  ];
  ignoreFolders.forEach((folder) => {
    combineArgs.push("--ignore", folder);
  });

  await runCommand(pythonCmd, combineArgs);

  const tmpDir = path.join(vaultPath, OUTDIR_NAME, TMPDIR_NAME);
  const tmpFiles = await fs.readdir(tmpDir);
  const mdFiles = tmpFiles
    .filter((file) => file.toLowerCase().endsWith(".md"))
    .sort()
    .map((file) => path.join(tmpDir, file));

  if (mdFiles.length === 0) {
    throw new Error("No markdown files were generated.");
  }

  const outputName = `combined.${outputFormat}`;
  const outputPath = path.join(vaultPath, OUTDIR_NAME, outputName);
  const pandocArgs = ["-s", ...mdFiles, "-o", outputPath];

  await runCommand("pandoc", pandocArgs, { cwd: path.join(vaultPath, OUTDIR_NAME) });

  return outputPath;
});
