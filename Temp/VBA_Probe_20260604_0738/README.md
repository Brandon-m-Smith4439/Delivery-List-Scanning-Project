# VBA Source

This folder contains extracted VBA source for the active scanner system workbooks.

## Workbooks exported

- Intake_Scanning_Test (version 1).xlsm: 28 modules/forms/classes
- Multi User Scanner Queue Testing (version 2).xlsm: 27 modules/forms/classes

## Workflow

1. Export fresh source from the active workbooks before starting a change.
2. Edit the `.bas`, `.cls`, and `.frm` source files here.
3. Run the import tool in dry-run mode to confirm which modules will be touched.
4. Import changed code back into the workbook after confirming the workbook is closed by other users.
5. Test the workbook, then export source again so this folder matches the workbook.

## Tools

- `tools/export_vba_source.py` extracts readable VBA source from the `.xlsm` workbooks.
- `tools/import_vba_source.ps1` imports source files back into a workbook through Excel automation.

Example dry run:

```powershell
.\tools\import_vba_source.ps1 -ProjectRoot "I:\BAREFOOT-INSTALL\Glass Production\Brandon\Delivery List Scanning Project" -WorkbookName "Multi User Scanner Queue Testing (version 2).xlsm" -DryRun
```

Example dry run for only changed files:

```powershell
.\tools\import_vba_source.ps1 -ProjectRoot "I:\BAREFOOT-INSTALL\Glass Production\Brandon\Delivery List Scanning Project" -WorkbookName "Multi User Scanner Queue Testing (version 2).xlsm" -Files "modMasterQueueProcessor.bas","TemplateImporter.bas" -DryRun
```

Example real import:

```powershell
.\tools\import_vba_source.ps1 -ProjectRoot "I:\BAREFOOT-INSTALL\Glass Production\Brandon\Delivery List Scanning Project" -WorkbookName "Multi User Scanner Queue Testing (version 2).xlsm"
```

For a workbook that requires a password to open for editing, add `-WritePassword "..."`.

## Notes

- The `_metadata/vbaProject.bin` file is a raw copy of the workbook VBA project at export time.
- The exported `.frm` files contain UserForm code/attributes. The import tool updates form code in the existing workbook component so the designer layout stays in the workbook.
- Sheet modules and `ThisWorkbook` are updated in place so their workbook bindings are preserved.
- Power Automate trigger URLs and other workbook secrets may appear in source files, so keep this folder in the same restricted location as the workbooks.
