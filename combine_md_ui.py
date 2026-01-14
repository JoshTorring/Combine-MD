#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

OUTDIR_NAME = "combined_output_folder"
TMPDIR_NAME = "_tmp_md_flat"
OUTRTF_NAME = "combined.rtf"


class CombineMDApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Combine MD")
        self.root.configure(bg="#000000")
        self.vault_path = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Select a vault to begin.")
        self.folder_vars = {}
        self.select_button: tk.Button | None = None
        self.background_canvas: tk.Canvas | None = None
        self.content_window: int | None = None
        self.style = ttk.Style()

        self._build_ui()

    def _build_ui(self) -> None:
        bg_color = "#000000"
        text_color = "#ffffff"
        hover_color = "#7ecbff"
        plus_color = "#ff3333"

        self.style.theme_use("clam")
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabel", background=bg_color, foreground=text_color)
        self.style.configure("App.TFrame", background=bg_color)
        self.style.configure("App.TLabel", background=bg_color, foreground=text_color)
        self.style.configure(
            "App.TButton",
            background=bg_color,
            foreground=text_color,
            borderwidth=0,
            focusthickness=0,
            padding=(14, 6),
        )
        self.style.map(
            "App.TButton",
            background=[("active", hover_color)],
            foreground=[("active", text_color)],
        )
        self.style.configure(
            "Run.TButton",
            background=bg_color,
            foreground=text_color,
            borderwidth=0,
            focusthickness=0,
            padding=(10, 4),
        )
        self.style.map(
            "Run.TButton",
            background=[("active", hover_color)],
            foreground=[("active", text_color)],
        )
        self.style.configure(
            "App.TCheckbutton",
            background=bg_color,
            foreground=text_color,
        )
        self.style.map(
            "App.TCheckbutton",
            background=[("active", bg_color)],
            foreground=[("active", text_color)],
        )
        self.style.configure(
            "App.Vertical.TScrollbar",
            background=bg_color,
            troughcolor=bg_color,
            bordercolor=bg_color,
            lightcolor=bg_color,
            darkcolor=bg_color,
        )

        self.background_canvas = tk.Canvas(self.root, bg=bg_color, highlightthickness=0)
        self.background_canvas.pack(fill="both", expand=True)
        self.root.bind("<Configure>", self._on_root_resize)

        content = ttk.Frame(self.background_canvas, style="App.TFrame")
        self.content_window = self.background_canvas.create_window((0, 0), window=content, anchor="nw")

        header = ttk.Frame(content, style="App.TFrame")
        header.pack(fill="x", padx=12, pady=8)

        self.select_button = ttk.Button(
            header,
            text="Select Vault",
            command=self.select_vault,
            style="App.TButton",
        )
        self.select_button.pack(side="left")

        vault_label = ttk.Label(
            header,
            textvariable=self.vault_path,
            anchor="w",
            style="App.TLabel",
        )
        vault_label.pack(side="left", padx=10)

        list_container = ttk.Frame(content, style="App.TFrame")
        list_container.pack(fill="both", expand=True, padx=12)

        self.canvas = tk.Canvas(list_container, borderwidth=0, highlightthickness=0, bg=bg_color)
        self.scrollbar = ttk.Scrollbar(
            list_container,
            orient="vertical",
            command=self.canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set, bg=bg_color)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.checkbox_frame = ttk.Frame(self.canvas, style="App.TFrame")
        self.canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        self.checkbox_frame.bind(
            "<Configure>",
            lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        footer = ttk.Frame(content, style="App.TFrame")
        footer.pack(fill="x", padx=12, pady=8)

        run_button = ttk.Button(
            footer,
            text="Run Combine",
            command=self.run_combine,
            style="Run.TButton",
        )
        run_button.pack(side="left")

        status_label = ttk.Label(
            footer,
            textvariable=self.status_text,
            anchor="w",
            style="App.TLabel",
        )
        status_label.pack(side="left", padx=10)

        self._refresh_background(plus_color)

    def _on_root_resize(self, event: tk.Event) -> None:
        if not self.background_canvas or self.content_window is None:
            return
        self._refresh_background("#ff3333")

    def _refresh_background(self, plus_color: str) -> None:
        if not self.background_canvas or self.content_window is None:
            return
        self.root.update_idletasks()
        width = self.background_canvas.winfo_width()
        height = self.background_canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        self.background_canvas.coords(self.content_window, 0, 0)
        self.background_canvas.itemconfigure(self.content_window, width=width, height=height)
        self._draw_background_pattern(width, height, plus_color)

    def _draw_background_pattern(self, width: int, height: int, plus_color: str) -> None:
        if not self.background_canvas:
            return
        self.background_canvas.delete("pattern")
        spacing = 24
        size = 3
        for x in range(0, width, spacing):
            for y in range(0, height, spacing):
                self.background_canvas.create_line(
                    x - size,
                    y,
                    x + size,
                    y,
                    fill=plus_color,
                    width=1,
                    tags="pattern",
                )
                self.background_canvas.create_line(
                    x,
                    y - size,
                    x,
                    y + size,
                    fill=plus_color,
                    width=1,
                    tags="pattern",
                )
        self.background_canvas.tag_lower("pattern")

    def select_vault(self) -> None:
        path = filedialog.askdirectory(title="Select Obsidian Vault")
        if not path:
            return
        self.vault_path.set(path)
        vault_name = os.path.basename(path.rstrip(os.sep)) or path
        if self.select_button:
            self.select_button.config(text=vault_name)
        self.status_text.set("Vault loaded. Choose folders to include.")
        self._populate_folders(path)

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
            checkbox = ttk.Checkbutton(
                self.checkbox_frame,
                text=folder,
                variable=var,
                style="App.TCheckbutton",
            )
            checkbox.grid(row=row, column=0, sticky="w", pady=2)
            self.folder_vars[folder] = var
            row += 1

        if not self.folder_vars:
            label = ttk.Label(
                self.checkbox_frame,
                text="No subfolders found in vault.",
                style="App.TLabel",
            )
            label.grid(row=0, column=0, sticky="w")

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

            pandoc_cmd = ["pandoc", "-s", *sorted(md_files), "-o", OUTRTF_NAME]
            subprocess.run(pandoc_cmd, check=True, cwd=outdir)

        except FileNotFoundError as exc:
            messagebox.showerror("Missing Dependency", f"Required tool not found: {exc}")
            self.status_text.set("Missing dependencies.")
            return
        except subprocess.CalledProcessError as exc:
            messagebox.showerror("Error", f"Combine failed: {exc}")
            self.status_text.set("Combine failed.")
            return

        self.status_text.set(f"Done: {os.path.join(outdir, OUTRTF_NAME)}")
        messagebox.showinfo("Complete", f"RTF created at:\n{os.path.join(outdir, OUTRTF_NAME)}")


def main() -> None:
    root = tk.Tk()
    root.geometry("640x480")
    app = CombineMDApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
