# Control templates used by `app/build_app.py`

These files are Power Apps **control definitions**, not app content. Power Apps needs them inside any `.msapp`. They were copied unchanged from public sample apps, choosing the newest version of each control:
- Microsoft's `PowerApps-Language-Tooling` test apps
- the PnP community `powerplatform-samples` repository (MIT licence)

| File | What it is |
|---|---|
| `ControlTemplates.json`, `pkgs/*.xml` | Definitions of label, button, gallery, container, text input, combo box, date picker, attachments and the other controls |
| `Themes.json` | The standard Power Apps theme |
| `CanvasManifest.base.json` | Manifest skeleton. Name, IDs and description are blanked, and `build_app.py` fills them in |
| `sp_list_base.json` | SharePoint connector metadata for the built-in list columns (ID, Title, Created, Modified, Author, Editor and so on). The site URL is replaced by a placeholder |

Nothing here is tenant-specific. To update a control, take the newer `pkgs/<control>_<version>.xml` and its `ControlTemplates.json` entry from an app exported from Studio.
