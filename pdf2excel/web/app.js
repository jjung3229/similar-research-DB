/* 화면 동작: PDF를 끌어다 놓으면 변환해서 엑셀을 내려받게 한다. */
(function () {
  'use strict';

  // pdf.js 의 해석기(pdf.worker)는 이 파일 안에 함께 담겨 이미 실행돼 있다.
  // 별도 파일을 받아오지 않으므로 인터넷 연결 없이, 파일을 그냥 열어도 동작한다.
  if (!window.pdfjsWorker) {
    document.getElementById('out').innerHTML =
      '<div class="card"><div class="err">PDF 해석기를 불러오지 못했습니다. 파일이 온전한지 확인해 주세요.</div></div>';
    return;
  }

  var drop = document.getElementById('drop');
  var picker = document.getElementById('file');
  var out = document.getElementById('out');

  ['dragenter', 'dragover'].forEach(function (type) {
    drop.addEventListener(type, function (e) { e.preventDefault(); drop.classList.add('hot'); });
  });
  ['dragleave', 'drop'].forEach(function (type) {
    drop.addEventListener(type, function (e) { e.preventDefault(); drop.classList.remove('hot'); });
  });
  drop.addEventListener('drop', function (e) { handle(e.dataTransfer.files); });
  picker.addEventListener('change', function () { handle(picker.files); });

  function escapeHtml(text) {
    return String(text).replace(/[&<>]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
    });
  }

  function readFile(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(new Uint8Array(reader.result)); };
      reader.onerror = function () { reject(new Error('파일을 읽지 못했습니다.')); };
      reader.readAsArrayBuffer(file);
    });
  }

  function card(name) {
    var el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = '<h3>' + escapeHtml(name) + '</h3><div class="body muted">준비 중…</div>';
    out.appendChild(el);
    return {
      set: function (html) { el.querySelector('.body').innerHTML = html; },
      element: el
    };
  }

  async function handle(files) {
    if (!files || !files.length) return;
    out.innerHTML = '';
    for (var i = 0; i < files.length; i++) await convert(files[i]);
  }

  async function convert(file) {
    var view = card(file.name);
    if (!/\.pdf$/i.test(file.name)) {
      view.set('<div class="err">PDF 파일이 아닙니다.</div>');
      return;
    }

    try {
      var data = await readFile(file);
      var result = await LandSchedule.extract(pdfjsLib, data, function (page, total) {
        view.set('<div class="muted">읽는 중… ' + page + ' / ' + total + '쪽</div>');
        return new Promise(function (r) { setTimeout(r, 0); });   // 진행 상황이 보이도록 잠깐 양보
      });

      view.set('<div class="muted">엑셀 만드는 중…</div>');
      await new Promise(function (r) { setTimeout(r, 0); });

      var built = LandExcel.build(result);
      var summary = built.summary;
      var name = file.name.replace(/\.pdf$/i, '') + '.xlsx';

      var html = '<div>자료 <b>' + summary.records.toLocaleString() + '건</b> · 소계 ' +
        summary.subtotals + '행 · 표가 있는 쪽 ' + summary.pagesWithTable + ' / 전체 ' +
        summary.totalPages + '쪽</div>';
      if (summary.checks) {
        html += summary.mismatches === 0
          ? '<div class="ok">소계 검증: ' + summary.checks + '개 구간 모두 일치 (빠진 항목 없음)</div>'
          : '<div class="warn">소계 검증: ' + summary.checks + '개 구간 중 ' + summary.mismatches +
            '개가 고시문 소계와 다릅니다 (' + escapeHtml(summary.mismatchedGroups.join(', ')) +
            '). 엑셀 「검증」 시트에서 확인하세요.</div>';
      }
      if (summary.warnings.length) {
        html += '<div class="warn">확인이 필요한 부분 ' + summary.warnings.length + '건<ul>' +
          summary.warnings.slice(0, 5).map(function (w) { return '<li>' + escapeHtml(w) + '</li>'; }).join('') +
          '</ul></div>';
      }
      html += '<button class="dl">엑셀 내려받기</button>';
      view.set(html);

      view.element.querySelector('.dl').addEventListener('click', function () {
        XLSX.writeFile(built.workbook, name, { bookType: 'xlsx', compression: true });
      });
    } catch (err) {
      view.set('<div class="err">' + escapeHtml(err && err.message ? err.message : err) + '</div>');
    }
  }
})();
