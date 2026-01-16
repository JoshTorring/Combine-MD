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

## Electron UI (work in progress)

There is an initial Electron app scaffold under `electron_app/` that uses the same Python backend and still requires Pandoc.

To run the Electron UI locally:

```
cd electron_app
npm install
npm run start
```


### Ignoring Folders

add folder names to IGNORE_DIRS in combine_md.sh 

e.g.
`IGNORE_DIRS=(".obsidian" "$OUTDIR_NAME" "Config" "Old_Notes" "Todo" "US_Trip" "Unsorted" "Admin")`

> Note ".obsidian" and "$OUTDIR_NAME" are required.


## TODO

- MacOS & Windows compatibility
- output format selection
- insert images in appropriate place

- UI
- integration with Obsisian
