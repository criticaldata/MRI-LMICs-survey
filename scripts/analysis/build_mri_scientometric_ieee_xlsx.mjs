import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoDir = "C:/Users/Pc/Desktop/MIT/MRI super Resolution Narrative review/MRI-LMICs-survey";
const runDir = path.join(repoDir, "analysis", "scientometrics", "multisource_20260803");
const desktopDir = "C:/Users/Pc/Desktop/MRI_LMICs_scientometric_export";
const csvPath = path.join(runDir, "MRI_LMICs_scientometric_ieee_csdl_20260804.csv");
const desktopXlsx = path.join(desktopDir, "MRI_LMICs_scientometric_ieee_csdl_20260804.xlsx");
const repoXlsx = path.join(runDir, "MRI_LMICs_scientometric_ieee_csdl_20260804.xlsx");
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
  if (name === "Title" || name.includes("Affiliation")) return 48;
  if (name.includes("Status") || name.includes("Available") || name.includes("Country")) return 24;
  return 18;
}

function styleSheet(sheet, tableName) {
  const used = sheet.getUsedRange();
  const values = used.values ?? [];
  const rowCount = values.length;
  const colCount = values[0]?.length ?? 0;
  if (!rowCount || !colCount) return;

  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(2);
  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format = {
    fill: "#5B2C6F",
    font: { bold: true, color: "#FFFFFF", size: 10 },
    wrapText: true,
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "medium", color: "#5B2C6F" },
  };
  header.format.rowHeight = 42;
  if (rowCount > 1) {
    const body = sheet.getRangeByIndexes(1, 0, rowCount - 1, colCount);
    body.format = {
      font: { color: "#1F2937", size: 9 },
      verticalAlignment: "top",
      borders: { preset: "all", style: "thin", color: "#E8DAEF" },
    };
  }
  const headers = values[0].map((value) => String(value ?? ""));
  for (let col = 0; col < colCount; col += 1) {
    const headerText = headers[col];
    const column = sheet.getRangeByIndexes(0, col, rowCount, 1);
    column.format.columnWidth = widthForHeader(headerText);
    if (headerText.includes("DOI") || headerText.includes("URL")) column.format.numberFormat = "@";
    if (headerText.includes("Affiliation") || headerText === "Title") column.format.wrapText = true;
  }
  sheet.tables.add("A1:" + columnLetters(colCount - 1) + rowCount, true, tableName);
}

await fs.mkdir(desktopDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
const csvText = (await fs.readFile(csvPath, "utf8")).replace(/^\uFEFF/, "");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "IEEE_CSDL" });
styleSheet(workbook.worksheets.getItem("IEEE_CSDL"), "MRIIEEECSDL");

const inspection = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 4000, tableMaxRows: 3, tableMaxCols: 8 });
console.log("INSPECTION");
console.log(inspection.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "IEEE CSDL auxiliary workbook formula error scan",
});
console.log("FORMULA_ERRORS");
console.log(errors.ndjson);

const used = workbook.worksheets.getItem("IEEE_CSDL").getUsedRange();
const values = used.values ?? [];
const preview = await workbook.render({ sheetName: "IEEE_CSDL", autoCrop: "all", scale: 0.9, format: "png" });
await fs.writeFile(path.join(previewDir, "IEEE_CSDL.png"), new Uint8Array(await preview.arrayBuffer()));

const desktopOutput = await SpreadsheetFile.exportXlsx(workbook);
await desktopOutput.save(desktopXlsx);
const repoOutput = await SpreadsheetFile.exportXlsx(workbook);
await repoOutput.save(repoXlsx);
const exported = await SpreadsheetFile.importXlsx(await FileBlob.load(desktopXlsx));
const exportedCheck = await exported.inspect({ kind: "sheet", include: "id,name" });
console.log("EXPORTED_CHECK");
console.log(exportedCheck.ndjson);
console.log("ROWS=" + values.length);
console.log("COLUMNS=" + (values[0]?.length ?? 0));
console.log("OUTPUT=" + desktopXlsx);
console.log("REPO_OUTPUT=" + repoXlsx);
