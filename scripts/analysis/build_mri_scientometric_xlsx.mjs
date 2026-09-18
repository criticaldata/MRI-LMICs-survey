import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoDir = "C:/Users/Pc/Desktop/MIT/MRI super Resolution Narrative review/MRI-LMICs-survey";
const runDir = path.join(repoDir, "analysis", "scientometrics", "multisource_20260803");
const desktopDir = "C:/Users/Pc/Desktop/MRI_LMICs_scientometric_export";
const resultCsv = path.join(runDir, "MRI_LMICs_scientometric_results_20260803.csv");
const coverageCsv = path.join(runDir, "MRI_LMICs_scientometric_source_coverage_20260803.csv");
const desktopXlsx = path.join(desktopDir, "MRI_LMICs_scientometric_results_20260803.xlsx");
const repoXlsx = path.join(runDir, "MRI_LMICs_scientometric_results_20260803.xlsx");
const previewDir = path.join(desktopDir, "xlsx_previews");

function columnLetters(index) {
  let n = index + 1;
  let output = "";
  while (n > 0) {
    const remainder = (n - 1) % 26;
    output = String.fromCharCode(65 + remainder) + output;
    n = Math.floor((n - 1) / 26);
  }
  return output;
}

function widthForHeader(header) {
  const name = String(header ?? "");
  if (name === "Paper_ID") return 10;
  if (name === "DOI") return 29;
  if (name === "Title" || name.includes("Title")) return 48;
  if (name.includes("URL") || name.includes("Affiliation")) return 38;
  if (
    name.includes("Summary")
    || name.includes("Reason")
    || name.includes("Evidence")
    || name.includes("Details")
    || name.includes("Justification")
    || name.includes("Performance")
    || name.includes("Limitation")
    || name.includes("Finding")
    || name.includes("Candidates")
  ) return 42;
  if (
    name.includes("Country")
    || name.includes("Status")
    || name.includes("Required")
    || name.includes("Resolution")
    || name.includes("Group")
    || name.includes("Source")
  ) return 24;
  if (name.includes("Year") || name.includes("Count") || name.includes("Score")) return 14;
  return 18;
}

function styleTableSheet(sheet, tableName, options = {}) {
  const used = sheet.getUsedRange();
  const values = used.values ?? [];
  const rowCount = values.length;
  const colCount = values[0]?.length ?? 0;
  if (!rowCount || !colCount) return;

  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(options.freezeColumns ?? 2);

  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format = {
    fill: options.headerFill ?? "#1F4E78",
    font: { bold: true, color: "#FFFFFF", size: 10 },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "medium", color: options.headerFill ?? "#1F4E78" },
  };
  header.format.rowHeight = 42;

  if (rowCount > 1) {
    const body = sheet.getRangeByIndexes(1, 0, rowCount - 1, colCount);
    body.format = {
      font: { color: "#1F2937", size: 9 },
      verticalAlignment: "top",
      borders: { preset: "all", style: "thin", color: "#D9E2F3" },
    };
  }

  const headers = values[0].map((value) => String(value ?? ""));
  for (let col = 0; col < colCount; col += 1) {
    const headerText = headers[col];
    const column = sheet.getRangeByIndexes(0, col, rowCount, 1);
    column.format.columnWidth = widthForHeader(headerText);
    if (headerText === "DOI" || headerText.includes("DOI") || headerText.includes("URL")) {
      column.format.numberFormat = "@";
    }
    if (headerText.includes("Reason") || headerText.includes("Evidence") || headerText === "Title") {
      column.format.wrapText = true;
    }
  }

  const manualIndex = headers.indexOf("Review_DOI");
  if (manualIndex >= 0 && rowCount > 1) {
    const manualColumn = sheet.getRangeByIndexes(1, manualIndex, rowCount - 1, 1);
    manualColumn.format = {
      fill: "#FFF2CC",
      font: { bold: true, color: "#7F6000", size: 9 },
      horizontalAlignment: "center",
      verticalAlignment: "top",
    };
  }

  try {
    sheet.tables.add(
      "A1:" + columnLetters(colCount - 1) + rowCount,
      true,
      tableName,
    );
  } catch (error) {
    console.log("table_skipped=" + tableName + "; reason=" + error.message);
  }
}

await fs.mkdir(desktopDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const resultText = (await fs.readFile(resultCsv, "utf8")).replace(/^\uFEFF/, "");
const coverageText = (await fs.readFile(coverageCsv, "utf8")).replace(/^\uFEFF/, "");
const workbook = await Workbook.fromCSV(resultText, { sheetName: "Results" });
await workbook.fromCSV(coverageText, { sheetName: "Source_Coverage" });

styleTableSheet(workbook.worksheets.getItem("Results"), "MRIResults", {
  headerFill: "#1F4E78",
  freezeColumns: 2,
});
styleTableSheet(workbook.worksheets.getItem("Source_Coverage"), "SourceCoverage", {
  headerFill: "#2F75B5",
  freezeColumns: 1,
});

const resultsSheet = workbook.worksheets.getItem("Results");
const resultsValues = resultsSheet.getUsedRange().values ?? [];
const resultsRows = resultsValues.length;
const resultsCols = resultsValues[0]?.length ?? 0;

const overview = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 5000,
  tableMaxRows: 3,
  tableMaxCols: 8,
});
console.log("INSPECTION");
console.log(overview.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "flat scientometric export formula error scan",
});
console.log("FORMULA_ERRORS");
console.log(errors.ndjson);

const resultsPreview = await workbook.render({
  sheetName: "Results",
  range: "A1:" + columnLetters(Math.min(resultsCols, 14) - 1) + Math.min(resultsRows, 20),
  scale: 0.8,
  format: "png",
});
await fs.writeFile(
  path.join(previewDir, "Results.png"),
  new Uint8Array(await resultsPreview.arrayBuffer()),
);

const coveragePreview = await workbook.render({
  sheetName: "Source_Coverage",
  autoCrop: "all",
  scale: 0.9,
  format: "png",
});
await fs.writeFile(
  path.join(previewDir, "Source_Coverage.png"),
  new Uint8Array(await coveragePreview.arrayBuffer()),
);

const desktopOutput = await SpreadsheetFile.exportXlsx(workbook);
await desktopOutput.save(desktopXlsx);
const repoOutput = await SpreadsheetFile.exportXlsx(workbook);
await repoOutput.save(repoXlsx);

const exported = await SpreadsheetFile.importXlsx(await FileBlob.load(desktopXlsx));
const exportedCheck = await exported.inspect({ kind: "sheet", include: "id,name" });
console.log("EXPORTED_CHECK");
console.log(exportedCheck.ndjson);
console.log("ROWS=" + resultsRows);
console.log("COLUMNS=" + resultsCols);
console.log("OUTPUT=" + desktopXlsx);
console.log("REPO_OUTPUT=" + repoXlsx);
console.log("PREVIEWS=" + previewDir);
