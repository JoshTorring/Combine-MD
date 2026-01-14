# Combine MD

simple tool to combine obsidian vault notes into one .rtf file preserving folder and file names as headers.


## Requirements

install Pandoc:

Mac OS
`brew install pandoc`

Windows
`choco install pandoc`


## Usage

to use, run:

`./combine_md.sh "PATH TO VAULT"`

will work with any folder containing .md files (loose or in folders)

## Simple UI

Run the Tkinter UI to select a vault folder, choose which top-level folders to include, and generate the combined RTF:

`python3 combine_md_ui.py`


### Ignoring Folders

add folder names to IGNORE_DIRS in combine_md.sh 

e.g.
`IGNORE_DIRS=(".obsidian" "Config" "Old_Notes" "Todo" "US_Trip" "Unsorted" "Admin" "$OUTDIR_NAME")`
