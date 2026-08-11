/* 추출 결과를 엑셀 파일(.xlsx)로 만든다. land_schedule.py 의 to_excel 과 같은 구성.
 * 시트: 토지세목조서 / 소계 / 검증 / 지목별 요약
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('xlsx-js-style'), require('./core.js'));
  else root.LandExcel = factory(root.XLSX, root.LandSchedule);
})(typeof self !== 'undefined' ? self : this, function (XLSX, LandSchedule) {
  'use strict';

  var HEADER_STYLE = {
    fill: { patternType: 'solid', fgColor: { rgb: '1F4E78' } },
    font: { color: { rgb: 'FFFFFF' }, bold: true, sz: 10 },
    alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
    border: box('BFBFBF')
  };

  function box(rgb) {
    var side = { style: 'thin', color: { rgb: rgb } };
    return { top: side, bottom: side, left: side, right: side };
  }

  function bodyStyle(numeric) {
    return {
      font: { sz: 10 },
      alignment: { vertical: 'center', horizontal: numeric ? 'right' : 'left' },
      border: box('BFBFBF')
    };
  }

  function displayWidth(value) {
    var text = value == null ? '' : String(value), width = 0;
    for (var i = 0; i < text.length; i++) width += text.charCodeAt(i) > 0x1100 ? 2 : 1;
    return width;
  }

  function makeSheet(columns, rows) {
    var aoa = [columns.slice()];
    rows.forEach(function (row) {
      aoa.push(columns.map(function (c) { return row[c] === undefined || row[c] === '' ? null : row[c]; }));
    });
    var ws = XLSX.utils.aoa_to_sheet(aoa);
    var widths = columns.map(displayWidth);

    for (var c = 0; c < columns.length; c++) {
      var numeric = LandSchedule.isNumericColumn(columns[c]) || columns[c] === '건수' || columns[c] === '페이지' || columns[c] === '연번';
      for (var r = 0; r <= rows.length; r++) {
        var ref = XLSX.utils.encode_cell({ r: r, c: c });
        var cell = ws[ref];
        if (!cell) { ws[ref] = { t: 's', v: '', s: bodyStyle(false) }; cell = ws[ref]; }
        if (r === 0) { cell.s = HEADER_STYLE; continue; }
        // 숫자는 서식 없이('일반') 둔다. 자릿점·소수 자릿수는 쓰는 사람이 정하게 한다.
        cell.s = bodyStyle(numeric && typeof cell.v === 'number');
        widths[c] = Math.max(widths[c], Math.min(displayWidth(cell.v), 84));
      }
    }

    ws['!cols'] = widths.map(function (w) { return { wch: Math.max(6, Math.min(42, w / 1.6 + 2)) }; });
    if (rows.length) {
      ws['!autofilter'] = {
        ref: 'A1:' + XLSX.utils.encode_cell({ r: rows.length, c: columns.length - 1 })
      };
    }
    return ws;
  }

  /** 추출 결과 → 엑셀 통합문서. 요약 정보도 함께 돌려준다. */
  function build(result) {
    var checks = LandSchedule.verify(result);
    var numCols = LandSchedule.numericColumns(result.columns);
    var wb = XLSX.utils.book_new();

    var mainColumns = ['연번'].concat(result.columns).concat(['페이지']);
    var body = result.records.map(function (row, i) {
      var item = { '연번': i + 1 };
      Object.keys(row).forEach(function (k) { item[k] = row[k]; });
      return item;
    });
    XLSX.utils.book_append_sheet(wb, makeSheet(mainColumns, body), '토지세목조서');

    if (result.subtotals.length) {
      XLSX.utils.book_append_sheet(wb, makeSheet(result.columns.concat(['페이지']), result.subtotals), '소계');
    }

    var mismatched = [];
    if (checks.length) {
      var checkColumns = Object.keys(checks[0]);
      var ws = makeSheet(checkColumns, checks);
      checks.forEach(function (entry, i) {
        var bad = numCols.some(function (col) {
          var diff = entry[col + ' 차이'];
          return typeof diff === 'number' && Math.abs(diff) > 0.05;
        });
        if (!bad) return;
        mismatched.push(entry);
        for (var c = 0; c < checkColumns.length; c++) {
          var cell = ws[XLSX.utils.encode_cell({ r: i + 1, c: c })];
          if (!cell) continue;
          cell.s = {
            font: { sz: 10, bold: checkColumns[c].slice(-2) === '차이', color: { rgb: 'C0392B' } },
            fill: { patternType: 'solid', fgColor: { rgb: 'FCE4E4' } },
            alignment: { vertical: 'center', horizontal: typeof cell.v === 'number' ? 'right' : 'left' },
            border: box('BFBFBF')
          };
        }
      });
      XLSX.utils.book_append_sheet(wb, ws, '검증');
    }

    var jimokColumn = null;
    result.columns.forEach(function (c) { if (!jimokColumn && c.indexOf('지목') !== -1) jimokColumn = c; });
    if (jimokColumn) {
      var buckets = {};
      result.records.forEach(function (row) {
        var key = String(row[jimokColumn] || '') || '(미기재)';
        if (!buckets[key]) buckets[key] = { '지목': key, '건수': 0 };
        buckets[key]['건수'] += 1;
        numCols.forEach(function (col) {
          if (typeof row[col] === 'number') {
            buckets[key][col] = Math.round(((buckets[key][col] || 0) + row[col]) * 10000) / 10000;
          }
        });
      });
      var summary = Object.keys(buckets).map(function (k) { return buckets[k]; })
        .sort(function (a, b) { return b['건수'] - a['건수']; });
      var total = { '지목': '합계', '건수': result.records.length };
      numCols.forEach(function (col) {
        total[col] = Math.round(summary.reduce(function (s, r) { return s + (r[col] || 0); }, 0) * 10000) / 10000;
      });
      summary.push(total);
      XLSX.utils.book_append_sheet(wb, makeSheet(['지목', '건수'].concat(numCols), summary), '지목별 요약');
    }

    return {
      workbook: wb,
      summary: {
        records: result.records.length,
        subtotals: result.subtotals.length,
        pagesWithTable: result.pagesWithTable,
        totalPages: result.totalPages,
        checks: checks.length,
        mismatches: mismatched.length,
        mismatchedGroups: mismatched.map(function (m) { return String(m['구간'] || ''); }),
        warnings: result.warnings
      }
    };
  }

  return { build: build };
});
