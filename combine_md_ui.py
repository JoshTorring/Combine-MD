#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

OUTDIR_NAME = "combined_output_folder"
TMPDIR_NAME = "_tmp_md_flat"
OUTFILE_BASENAME = "combined"
OUTPUT_FORMATS = ("rtf", "docx", "md")


class CombineMDApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Combine MD")
        self.vault_path = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Select a vault to begin.")
        self.folder_vars = {}
        self.output_format = tk.StringVar(value=OUTPUT_FORMATS[0])
        self.stats_vars = {
            "total_size": tk.StringVar(value="0 B"),
            "total_files": tk.StringVar(value="0"),
            "total_dirs": tk.StringVar(value="0"),
            "md_chars": tk.StringVar(value="0"),
        }

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self.root)
        header.pack(fill="x", padx=12, pady=8)

        select_button = tk.Button(header, text="Select Vault", command=self.select_vault)
        select_button.pack(side="left")

        vault_label = tk.Label(header, textvariable=self.vault_path, anchor="w")
        vault_label.pack(side="left", padx=10)

        content = tk.Frame(self.root)
        content.pack(fill="both", expand=True, padx=12)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        subfolders_frame = tk.LabelFrame(content, text="Subfolders")
        subfolders_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        subfolders_frame.bind(
            "<Enter>",
            lambda event: Tooltip.show(
                event.widget, "Select the subfolders to include in the Combination"
            ),
        )
        subfolders_frame.bind("<Leave>", lambda event: Tooltip.hide())

        self.canvas = tk.Canvas(subfolders_frame, borderwidth=0)
        self.scrollbar = tk.Scrollbar(subfolders_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.checkbox_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        self.checkbox_frame.bind(
            "<Configure>",
            lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        sidebar = tk.Frame(content)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)

        stats_frame = tk.LabelFrame(sidebar, text="Stats")
        stats_frame.grid(row=0, column=0, sticky="new", pady=(0, 10))
        stats_frame.columnconfigure(1, weight=1)

        stats_rows = [
            ("Total file size:", "total_size"),
            ("Total files included:", "total_files"),
            ("Total sub-subfolders:", "total_dirs"),
            ("Estimated output characters:", "md_chars"),
        ]
        for row, (label_text, key) in enumerate(stats_rows):
            label = tk.Label(stats_frame, text=label_text, anchor="w")
            label.grid(row=row, column=0, sticky="w", padx=6, pady=2)
            value = tk.Label(stats_frame, textvariable=self.stats_vars[key], anchor="e")
            value.grid(row=row, column=1, sticky="e", padx=6, pady=2)

        format_frame = tk.LabelFrame(sidebar, text="Output Format")
        format_frame.grid(row=1, column=0, sticky="new")
        for row, fmt in enumerate(OUTPUT_FORMATS):
            radio = tk.Radiobutton(
                format_frame,
                text=f".{fmt}",
                value=fmt,
                variable=self.output_format,
            )
            radio.grid(row=row, column=0, sticky="w", padx=6, pady=2)

        footer = tk.Frame(self.root)
        footer.pack(fill="x", padx=12, pady=8)

        run_button = tk.Button(footer, text="Run Combine", command=self.run_combine)
        run_button.pack(side="left")

        status_label = tk.Label(footer, textvariable=self.status_text, anchor="w")
        status_label.pack(side="left", padx=10)

    def select_vault(self) -> None:
        path = filedialog.askdirectory(title="Select Obsidian Vault")
        if not path:
            return
        self.vault_path.set(path)
        self.status_text.set("Vault loaded. Choose folders to include.")
        self._populate_folders(path)
        self._update_stats()

    def _populate_folders(self, vault: str) -> None:
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()
        self.folder_vars.clear()

        try:
            entries = sorted(
                [
                    entry
                    for entry in os.listdir(vault)
                    if os.path.isdir(os.path.join(vault, entry))
                ],
                key=str.lower,
            )
        except OSError as exc:
            messagebox.showerror("Error", f"Unable to read vault contents: {exc}")
            return

        row = 0
        for folder in entries:
            if folder == OUTDIR_NAME:
                continue
            var = tk.BooleanVar(value=True)
            checkbox = tk.Checkbutton(
                self.checkbox_frame,
                text=folder,
                variable=var,
                command=self._update_stats,
            )
            checkbox.grid(row=row, column=0, sticky="w", pady=2)
            self.folder_vars[folder] = var
            row += 1

        if not self.folder_vars:
            label = tk.Label(self.checkbox_frame, text="No subfolders found in vault.")
            label.grid(row=0, column=0, sticky="w")
        self._update_stats()

    def _update_stats(self) -> None:
        stats = self._calculate_stats()
        self.stats_vars["total_size"].set(self._format_size(stats["total_size"]))
        self.stats_vars["total_files"].set(f"{stats['total_files']}")
        self.stats_vars["total_dirs"].set(f"{stats['total_dirs']}")
        self.stats_vars["md_chars"].set(f"{stats['md_chars']}")

    def _calculate_stats(self) -> dict:
        vault = self.vault_path.get()
        if not vault:
            return {"total_size": 0, "total_files": 0, "total_dirs": 0, "md_chars": 0}

        selected_folders = [
            name for name, var in self.folder_vars.items() if var.get()
        ]
        if not selected_folders:
            return {"total_size": 0, "total_files": 0, "total_dirs": 0, "md_chars": 0}

        total_size = 0
        total_files = 0
        total_dirs = 0
        md_chars = 0

        for folder in selected_folders:
            folder_path = os.path.join(vault, folder)
            for root, dirs, files in os.walk(folder_path):
                total_dirs += len(dirs)
                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
                    total_files += 1
                    if filename.lower().endswith(".md"):
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                                md_chars += len(handle.read())
                        except OSError:
                            continue

        return {
            "total_size": total_size,
            "total_files": total_files,
            "total_dirs": total_dirs,
            "md_chars": md_chars,
        }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def run_combine(self) -> None:
        vault = self.vault_path.get()
        if not vault:
            messagebox.showwarning("Missing Vault", "Please select a vault first.")
            return

        ignore_dirs = [name for name, var in self.folder_vars.items() if not var.get()]
        self.status_text.set("Running combine...")
        self.root.update_idletasks()

        outdir = os.path.join(vault, OUTDIR_NAME)
        try:
            if os.path.exists(outdir):
                shutil.rmtree(outdir)

            combine_cmd = [
                sys.executable,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "combine_md.py"),
                vault,
                "--outdir-name",
                OUTDIR_NAME,
                "--tmpdir-name",
                TMPDIR_NAME,
            ]
            for ignore in ignore_dirs:
                combine_cmd.extend(["--ignore", ignore])

            subprocess.run(combine_cmd, check=True)

            tmpdir = os.path.join(outdir, TMPDIR_NAME)
            md_files = [
                os.path.join(tmpdir, f)
                for f in os.listdir(tmpdir)
                if f.lower().endswith(".md")
            ]
            if not md_files:
                messagebox.showerror("Error", "No markdown files were generated.")
                self.status_text.set("No markdown files generated.")
                return

            output_ext = self.output_format.get()
            output_name = f"{OUTFILE_BASENAME}.{output_ext}"
            pandoc_cmd = ["pandoc", "-s", *sorted(md_files), "-o", output_name]
            subprocess.run(pandoc_cmd, check=True, cwd=outdir)

        except FileNotFoundError as exc:
            messagebox.showerror("Missing Dependency", f"Required tool not found: {exc}")
            self.status_text.set("Missing dependencies.")
            return
        except subprocess.CalledProcessError as exc:
            messagebox.showerror("Error", f"Combine failed: {exc}")
            self.status_text.set("Combine failed.")
            return

        self.status_text.set(f"Done: {os.path.join(outdir, output_name)}")
        messagebox.showinfo(
            "Complete", f"Output created at:\n{os.path.join(outdir, output_name)}"
        )


class Tooltip:
    _tooltip = None

    @classmethod
    def show(cls, widget: tk.Widget, text: str) -> None:
        cls.hide()
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.attributes("-topmost", True)
        label = tk.Label(
            tooltip,
            text=text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=2,
        )
        label.pack()
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        tooltip.wm_geometry(f"+{x}+{y}")
        cls._tooltip = tooltip

    @classmethod
    def hide(cls) -> None:
        if cls._tooltip is not None:
            cls._tooltip.destroy()
            cls._tooltip = None


def main() -> None:
    root = tk.Tk()
    root.geometry("860x520")
    app = CombineMDApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
