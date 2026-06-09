# Tolerant Bad Scan Format Update

## What changed

The exported VBA source now allows damaged labels to recover when the loaded delivery-list data makes the order/item safe to identify.

- `T200234481001000` remains the normal exact format.
- `TDEX234481001000` can recover to `T200234481001000` when order `234481` item `001` exists on the loaded list.
- `TDEXRTY481001000` can recover to `T200234481001000` only when exactly one visible delivery-list order ending in `481` has item `001`.
- Ambiguous or missing matches still fail instead of guessing.

The recovered value is converted back into the normal canonical barcode format before being queued or sent to Power Automate.

## Files changed in exported VBA source

- `VBA Source\Intake_Scanning_Test (version 1)\modIntakeStation.bas`
- `VBA Source\Multi User Scanner Queue Testing (version 2)\ScannerValidation.bas`
- `VBA Source\Multi User Scanner Queue Testing (version 2)\ThisWorkbook.cls`

## Import commands

Close the live workbooks first, then run these from PowerShell in the local project folder:

```powershell
Set-Location "C:\Users\brandon.m.smith\My Projects\Delivery List Scanning Project"

.\tools\import_vba_source.ps1 `
  -ProjectRoot "." `
  -WorkbookName "Intake_Scanning_Test (version 1).xlsm" `
  -Files "modIntakeStation.bas" `
  -DryRun

.\tools\import_vba_source.ps1 `
  -ProjectRoot "." `
  -WorkbookName "Intake_Scanning_Test (version 1).xlsm" `
  -Files "modIntakeStation.bas"

.\tools\import_vba_source.ps1 `
  -ProjectRoot "." `
  -WorkbookName "Multi User Scanner Queue Testing (version 2).xlsm" `
  -Files "ScannerValidation.bas","ThisWorkbook.cls" `
  -OpenPassword "BFSGlass" `
  -WritePassword "BFSGlass" `
  -DryRun

.\tools\import_vba_source.ps1 `
  -ProjectRoot "." `
  -WorkbookName "Multi User Scanner Queue Testing (version 2).xlsm" `
  -Files "ScannerValidation.bas","ThisWorkbook.cls" `
  -OpenPassword "BFSGlass" `
  -WritePassword "BFSGlass"
```

If Excel reports that the master workbook or VBA project is locked, open the workbook, unlock the VBA project with the project password, save/close it, and rerun the import. The `-OpenPassword` and `-WritePassword` parameters are for the workbook file password, not the VBA project password.

## Smoke tests

Use a test delivery list that contains order `234481`, item `001`.

1. Scan `T200234481001000`.
   Expected: normal pass.
2. Scan `TDEX234481001000`.
   Expected: pass as order `234481`, item `001`, stored/sent as `T200234481001000`.
3. Scan `TDEXRTY481001000`.
   Expected: pass only if exactly one loaded visible row matches suffix `481` and item `001`.
4. Scan `TDEX999999001000`.
   Expected: still rejected or reported as not found.
5. Add another visible order ending in `481` with item `001`, then rescan `TDEXRTY481001000`.
   Expected: reject as unsafe/ambiguous rather than guessing.
