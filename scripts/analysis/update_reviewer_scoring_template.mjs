import fs from "fs";
import os from "os";
import path from "path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const repoRoot = path.resolve(process.cwd());
const canonicalPath = path.join(
  repoRoot,
  "analysis",
  "reproducibility",
  "reviewer_scoring",
  "Reviewer_Scoring_Template.xlsx",
);
const desktopPath = "C:/Users/Pc/Desktop/MRI_LMICs_Reviewer_Packet/MRI_LMICs_Reviewer_Scoring_Template.xlsx";

if (!fs.existsSync(canonicalPath) || !fs.existsSync(desktopPath)) {
  throw new Error("Reviewer scoring template was not found at one or both required locations.");
}

const sourceBytes = fs.readFileSync(canonicalPath);
const workbook = await SpreadsheetFile.importXlsx(new FileBlob(sourceBytes));
const before = workbook.worksheets.items.map((sheet) => sheet.name);

if (before.includes("TR_Criteria")) {
  const trCriteria = workbook.worksheets.getItem("TR_Criteria");
  trCriteria.delete();
}

const instructionsSheet = workbook.worksheets.getItem("Instructions");
instructionsSheet.getRange("B5").values = [[
  "1) Score every Paper_ID in LMIC_Score. 2) Add evidence notes for uncertain decisions. 3) Return only your own workbook.",
]];

const codebookSheet = workbook.worksheets.getItem("Codebook");
codebookSheet.getRange("A6:D11").values = Array.from({ length: 6 }, () => ["", "", "", ""]);

const after = workbook.worksheets.items.map((sheet) => sheet.name);
const expected = ["Instructions", "Papers", "LMIC_Score", "Codebook"];
if (after.length !== expected.length || after.some((name, index) => name !== expected[index])) {
  throw new Error(`Unexpected worksheet order after update: ${after.join(", ")}`);
}

const scoreSheet = workbook.worksheets.getItem("LMIC_Score");
const scoreRows = await scoreSheet.getRange("A5:A200").values;
const paperIds = scoreRows.flat().filter((value) => value !== null && value !== "");
if (paperIds.length !== 48 || new Set(paperIds).size !== 48) {
  throw new Error(`LMIC_Score must retain 48 unique Paper_ID values; found ${paperIds.length}.`);
}
const scoreInputs = await scoreSheet.getRange("D5:D200").values;
if (scoreInputs.flat().some((value) => value !== null && value !== "")) {
  throw new Error("LMIC_Score must not contain pre-filled reviewer scores.");
}

const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(canonicalPath);
await exported.save(desktopPath);

const verifiedBlob = await FileBlob.load(desktopPath);
const verifiedWorkbook = await SpreadsheetFile.importXlsx(verifiedBlob);
const verifiedSheets = verifiedWorkbook.worksheets.items.map((sheet) => sheet.name);
if (JSON.stringify(verifiedSheets) !== JSON.stringify(expected)) {
  throw new Error(`Exported reviewer template has unexpected worksheets: ${verifiedSheets.join(", ")}`);
}
const verifiedScoreRows = await verifiedWorkbook.worksheets.getItem("LMIC_Score").getRange("A5:A200").values;
const verifiedPaperIds = verifiedScoreRows.flat().filter((value) => value !== null && value !== "");
if (verifiedPaperIds.length !== 48 || new Set(verifiedPaperIds).size !== 48) {
  throw new Error("Exported reviewer template does not retain 48 unique Paper_ID values.");
}
const verifiedScoreInputs = await verifiedWorkbook.worksheets.getItem("LMIC_Score").getRange("D5:D200").values;
if (verifiedScoreInputs.flat().some((value) => value !== null && value !== "")) {
  throw new Error("Exported reviewer template contains pre-filled reviewer scores.");
}
const formulaErrors = await verifiedWorkbook.inspect({
  kind: "match",
  search_term: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { use_regex: true, max_results: 100 },
  summary: "formula error scan",
});
if (formulaErrors.matches?.length) {
  throw new Error(`Formula error scan found ${formulaErrors.matches.length} issue(s).`);
}
const retiredTrTerms = await verifiedWorkbook.inspect({
  kind: "match",
  search_term: "TR_Criteria|TR_Score|Low-Field Domain|Open Science|Clinical Evaluation|Hardware Awareness|Data Diversity",
  options: { use_regex: true, max_results: 100 },
  summary: "retired TR criteria scan",
});
if (retiredTrTerms.matches?.length) {
  throw new Error(`Retired TR criteria text remains in ${retiredTrTerms.matches.length} cell(s).`);
}
const previewDir = fs.mkdtempSync(path.join(os.tmpdir(), "mri-reviewer-template-"));
for (const sheetName of expected) {
  const preview = await verifiedWorkbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  fs.writeFileSync(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

console.log(JSON.stringify({
  before,
  after,
  paperIds: paperIds.length,
  blankScoreInputs: true,
  previewDir,
  canonicalPath,
  desktopPath,
}, null, 2));
