/* 만들어진 단독 실행 HTML 을 실제 브라우저에서 열어 확인한다.
 * 파일을 그냥 여는 상황(file://)과 같게 두고, PDF 를 넣어 엑셀이 나오는지까지 본다.
 *
 *   npm install -D playwright && node tools/browser-test.js <pdf> [html]
 */
const fs = require('fs');
const os = require('os');
const path = require('path');

const { chromium } = require('playwright');

const DEFAULT_HTML = path.join(__dirname, '..', '..', '토지세목조서_변환기.html');

(async () => {
  const pdfPath = process.argv[2];
  const htmlPath = path.resolve(process.argv[3] || DEFAULT_HTML);
  if (!pdfPath) {
    console.error('사용법: node tools/browser-test.js <pdf> [html]');
    process.exit(2);
  }

  const downloadDir = fs.mkdtempSync(path.join(os.tmpdir(), 'land-schedule-'));
  const browser = await chromium.launch(
    process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}
  );
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();

  const problems = [];
  page.on('pageerror', e => problems.push('페이지 오류: ' + e.message));

  await page.goto('file://' + htmlPath);
  console.log('제목:', await page.title());

  const started = Date.now();
  await page.setInputFiles('#file', pdfPath);
  await page.waitForSelector('.card button.dl, .card .err', { timeout: 300000 });
  console.log('처리 시간:', ((Date.now() - started) / 1000).toFixed(1) + '초');
  console.log(await page.locator('.card').innerText());

  if (await page.locator('.card .err').count()) {
    problems.push('변환 실패 메시지가 표시되었습니다.');
  } else {
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 120000 }),
      page.click('.card button.dl')
    ]);
    const saved = path.join(downloadDir, download.suggestedFilename());
    await download.saveAs(saved);
    const size = fs.statSync(saved).size;
    console.log('내려받은 파일:', saved, `(${(size / 1024).toFixed(0)}KB)`);
    if (size < 10000) problems.push('내려받은 엑셀이 너무 작습니다.');
  }

  await browser.close();
  if (problems.length) { problems.forEach(p => console.error('✗ ' + p)); process.exit(1); }
  console.log('✓ 브라우저에서 정상 동작');
})().catch(err => { console.error(err); process.exit(2); });
