const vaultPathEl = document.getElementById("vaultPath");
const folderListEl = document.getElementById("folderList");
const selectVaultBtn = document.getElementById("selectVault");
const runCombineBtn = document.getElementById("runCombine");
const outputFormatEl = document.getElementById("outputFormat");
const statusEl = document.getElementById("status");

let vaultPath = "";
let folderNames = [];

const setStatus = (message, tone = "muted") => {
  statusEl.textContent = message;
  statusEl.className = `status ${tone}`;
};

const renderFolderList = () => {
  folderListEl.innerHTML = "";
  if (folderNames.length === 0) {
    folderListEl.textContent = "No subfolders found in this vault.";
    folderListEl.classList.add("muted");
    return;
  }

  folderListEl.classList.remove("muted");
  folderNames.forEach((name) => {
    const label = document.createElement("label");
    label.className = "folder-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.dataset.folder = name;

    const span = document.createElement("span");
    span.textContent = name;

    label.appendChild(checkbox);
    label.appendChild(span);
    folderListEl.appendChild(label);
  });
};

const getSelectedFolders = () =>
  Array.from(folderListEl.querySelectorAll("input[type='checkbox']"))
    .filter((input) => input.checked)
    .map((input) => input.dataset.folder);

selectVaultBtn.addEventListener("click", async () => {
  const selected = await window.combineApi.selectVault();
  if (!selected) {
    return;
  }
  vaultPath = selected;
  vaultPathEl.textContent = selected;
  setStatus("Vault loaded. Choose folders to include.");
  folderNames = await window.combineApi.listFolders(selected);
  renderFolderList();
});

runCombineBtn.addEventListener("click", async () => {
  if (!vaultPath) {
    setStatus("Select a vault first.", "muted");
    return;
  }
  const selectedFolders = getSelectedFolders();
  if (selectedFolders.length === 0) {
    setStatus("Select at least one folder to include.", "muted");
    return;
  }

  setStatus("Running combine...", "muted");
  runCombineBtn.disabled = true;

  try {
    const outputPath = await window.combineApi.runCombine({
      vaultPath,
      outputFormat: outputFormatEl.value,
      includeFolders: {
        all: folderNames,
        selected: selectedFolders,
      },
    });
    setStatus(`Done: ${outputPath}`, "muted");
  } catch (error) {
    setStatus(`Error: ${error.message}`, "muted");
  } finally {
    runCombineBtn.disabled = false;
  }
});
