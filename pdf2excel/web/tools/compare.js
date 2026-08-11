/* core.js(브라우저용)의 추출 결과를 land_schedule.py(파이썬)의 결과와 한 줄씩 대조한다.
 *
 *   1) python -c "..."  로 py_records.json / py_subtotals.json 을 먼저 만든 뒤
 *   2) node tools/compare.js <pdf> <py_records.json> <py_subtotals.json>
 */
const path = require('path');
const fs = require('fs');

const pdfjsLib = require('pdfjs-dist/legacy/build/pdf.js');
pdfjsLib.GlobalWorkerOptions.workerSrc = require.resolve('pdfjs-dist/legacy/build/pdf.worker.js');
const LandSchedule = require(path.join(__dirname, '..', 'core.js'));

(async () => {
  const [pdfPath, recordsPath, subtotalsPath] = process.argv.slice(2);
  const data = new Uint8Array(fs.readFileSync(pdfPath));

  const started = Date.now();
  const result = await LandSchedule.extract(pdfjsLib, data);
  const seconds = ((Date.now() - started) / 1000).toFixed(1);

  console.log(`열: ${result.columns.join(' | ')}`);
  console.log(`자료 ${result.records.length}건 / 소계 ${result.subtotals.length}행 / ` +
              `표 ${result.pagesWithTable}쪽 (전체 ${result.totalPages}쪽) — ${seconds}초`);
  if (result.warnings.length) console.log(`경고 ${result.warnings.length}건: ${result.warnings[0]}`);

  const checks = LandSchedule.verify(result);
  const numCols = LandSchedule.numericColumns(result.columns);
  const mismatched = checks.filter(c => numCols.some(col =>
    typeof c[col + ' 차이'] === 'number' && Math.abs(c[col + ' 차이']) > 0.05));
  console.log(`소계 검증: ${checks.length}개 구간 중 ${mismatched.length}개 불일치` +
              (mismatched.length ? ` → ${mismatched.map(m => m['구간']).join(', ')}` : ''));

  if (!recordsPath) return;

  // ---- 파이썬 결과와 대조 -------------------------------------------------
  let failures = 0;
  for (const [label, mine, theirsPath] of [
    ['자료', result.records, recordsPath],
    ['소계', result.subtotals, subtotalsPath],
  ]) {
    const theirs = JSON.parse(fs.readFileSync(theirsPath, 'utf8'));
    if (mine.length !== theirs.length) {
      console.log(`✗ ${label} 건수가 다릅니다: JS ${mine.length} vs PY ${theirs.length}`);
      failures++;
      continue;
    }
    let diffs = 0;
    const byColumn = {};
    for (let i = 0; i < mine.length; i++) {
      for (const key of Object.keys(theirs[i])) {
        const a = mine[i][key], b = theirs[i][key];
        const same = (typeof a === 'number' && typeof b === 'number')
          ? Math.abs(a - b) < 0.0001
          : String(a == null ? '' : a) === String(b == null ? '' : b);
        if (!same) {
          byColumn[key] = (byColumn[key] || 0) + 1;
          if (diffs < 8) {
            console.log(`✗ ${label} ${i + 1}행 [${key}] JS=${JSON.stringify(a)} PY=${JSON.stringify(b)}`);
          }
          diffs++;
        }
      }
    }
    if (diffs) {
      failures++;
      console.log(`✗ ${label}: 값이 다른 칸 ${diffs}개 / 전체 ${mine.length * Object.keys(theirs[0]).length}칸`);
      console.log('   열별: ' + Object.entries(byColumn).map(([k, v]) => `${k} ${v}`).join(', '));
    }
    else console.log(`✓ ${label} ${mine.length}행 전부 일치`);
  }
  process.exit(failures ? 1 : 0);
})().catch(err => { console.error(err); process.exit(2); });
