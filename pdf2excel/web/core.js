/* 토지세목조서 PDF → 엑셀: 추출 핵심 로직 (브라우저·Node 공용)
 *
 * land_schedule.py 와 같은 규칙을 그대로 옮긴 것이다. 파이썬 쪽을 고치면
 * 이쪽도 같이 고쳐야 한다. (tools/compare.js 로 두 결과를 대조할 수 있다)
 *
 *  1) 표 괘선(세로·가로줄)으로 칸 격자를 만든다.
 *  2) 글자를 격자에 담아 pdfplumber 와 같은 모양의 표를 얻는다.
 *  3) 머리글을 읽어 열 구성을 잡고, 여러 줄에 걸친 한 필지를 한 행으로 합친다.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.LandSchedule = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ------------------------------------------------------------------
  // 머리글 해석에 쓰는 낱말들 (land_schedule.py 와 동일)
  // ------------------------------------------------------------------
  var SUBTOTAL_LABELS = ['소계', '합계', '총계', '계'];
  var KEY_HEADERS = ['번호', '연번', '순번', '일련번호'];
  var ANCHOR_HEADERS = ['지번'];
  var GLUE_WITHOUT_SPACE = ['성명', '지목', '지번', '권리'];
  var NUMERIC_HINTS = ['면적', '지적', '㎡', 'm2'];
  var SUB_HEADERS = ['시군읍면동리', '성명', '주소', '권리의종류', '소재지', '지번'];
  var MAX_HEADER_SEARCH = 6;
  var WORD_GAP = 3;        // 이보다 벌어지면 띄어쓰기로 본다 (pdfplumber 기본값과 같다)
  var LINE_GAP = 2;        // 이보다 위아래로 벌어지면 다른 줄로 본다

  function squash(text) { return String(text == null ? '' : text).replace(/\s+/g, ''); }

  function hasAny(text, words) {
    var s = squash(text);
    for (var i = 0; i < words.length; i++) if (s.indexOf(words[i]) !== -1) return true;
    return false;
  }

  function norm(text) {
    if (text == null) return '';
    return String(text).replace(/ /g, ' ').replace(/[ \t]+/g, ' ').trim();
  }

  function flatten(text, glue) {
    var parts = String(text).split('\n').map(function (p) { return p.trim(); })
      .filter(function (p) { return p.length; });
    return parts.join(glue);
  }

  function glueFor(column) { return hasAny(column, GLUE_WITHOUT_SPACE) ? '' : ' '; }
  function isNumericColumn(column) { return hasAny(column, NUMERIC_HINTS); }

  function toNumber(value) {
    var text = String(value).replace(/,/g, '').replace(/ /g, '');
    if (!text) return '';
    if (/^-?\d+(\.\d+)?$/.test(text)) return parseFloat(text);
    return value;
  }

  // ------------------------------------------------------------------
  // 1) 표 괘선 뽑기 — 그리기 명령을 따라가며 가로·세로 선분을 모은다
  // ------------------------------------------------------------------
  function matMul(m, n) {
    return [
      m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
      m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
      m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]
    ];
  }
  function matApply(m, x, y) {
    return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  }

  function collectRulings(opList, OPS, pageHeight) {
    // 그리기 명령의 좌표는 변환행렬을 거치면 PDF 기본 좌표(아래에서 위)가 된다.
    // 글자 위치와 맞추기 위해 마지막에 '위에서부터의 거리'로 뒤집는다.
    var ctm = [1, 0, 0, 1, 0, 0];
    var stack = [];
    var verticals = [];   // {x, y0, y1}
    var horizontals = []; // {y, x0, x1}

    function addSegment(a, b) {
      var p0 = [a[0], pageHeight - a[1]];
      var p1 = [b[0], pageHeight - b[1]];
      var dx = Math.abs(p0[0] - p1[0]);
      var dy = Math.abs(p0[1] - p1[1]);
      if (dx < 0.6 && dy >= 3) {
        verticals.push({ x: (p0[0] + p1[0]) / 2, y0: Math.min(p0[1], p1[1]), y1: Math.max(p0[1], p1[1]) });
      } else if (dy < 0.6 && dx >= 3) {
        horizontals.push({ y: (p0[1] + p1[1]) / 2, x0: Math.min(p0[0], p1[0]), x1: Math.max(p0[0], p1[0]) });
      }
    }

    for (var i = 0; i < opList.fnArray.length; i++) {
      var fn = opList.fnArray[i];
      var args = opList.argsArray[i];
      if (fn === OPS.save) { stack.push(ctm.slice()); continue; }
      if (fn === OPS.restore) { ctm = stack.pop() || ctm; continue; }
      if (fn === OPS.transform) { ctm = matMul(ctm, args); continue; }
      if (fn !== OPS.constructPath) continue;

      var ops = args[0], coords = args[1], k = 0, cur = null, start = null;
      for (var j = 0; j < ops.length; j++) {
        var op = ops[j];
        if (op === OPS.moveTo) {
          cur = matApply(ctm, coords[k], coords[k + 1]); start = cur; k += 2;
        } else if (op === OPS.lineTo) {
          var next = matApply(ctm, coords[k], coords[k + 1]); k += 2;
          if (cur) addSegment(cur, next);
          cur = next;
        } else if (op === OPS.curveTo) { k += 6; cur = null; }
        else if (op === OPS.curveTo2 || op === OPS.curveTo3) { k += 4; cur = null; }
        else if (op === OPS.closePath) { if (cur && start) addSegment(cur, start); cur = start; }
        else if (op === OPS.rectangle) {
          var x = coords[k], y = coords[k + 1], w = coords[k + 2], h = coords[k + 3]; k += 4;
          var a = matApply(ctm, x, y), b = matApply(ctm, x + w, y);
          var c = matApply(ctm, x + w, y + h), d = matApply(ctm, x, y + h);
          addSegment(a, b); addSegment(b, c); addSegment(c, d); addSegment(d, a);
          cur = null;
        } else { cur = null; }
      }
    }
    return { verticals: verticals, horizontals: horizontals };
  }

  /** 비슷한 위치의 선을 하나로 묶어 경계값 목록을 만든다.
   *
   * 글자 장식 같은 아주 짧은 선이 섞여 들어와 없는 칸을 만들어내는 일이 있어서,
   * 묶음 안에 쓸 만한 길이의 선이 하나도 없으면 표 괘선으로 보지 않는다.
   */
  function clusterPositions(segments, tolerance, minLength) {
    var sorted = segments.slice().sort(function (a, b) { return a.pos - b.pos; });
    var groups = [], bucket = [];
    for (var i = 0; i < sorted.length; i++) {
      if (bucket.length && sorted[i].pos - bucket[bucket.length - 1].pos > tolerance) {
        groups.push(bucket); bucket = [];
      }
      bucket.push(sorted[i]);
    }
    if (bucket.length) groups.push(bucket);

    var out = [];
    groups.forEach(function (group) {
      var longest = 0, sum = 0;
      group.forEach(function (s) {
        longest = Math.max(longest, s.to - s.from);
        sum += s.pos;
      });
      if (longest >= (minLength || 0)) out.push(sum / group.length);
    });
    return out;
  }

  var WIDE_CHAR = /[ᄀ-ᇿ⺀-꓏ꥠ-꥿가-힣豈-﫿︰-﹏＀-｠￠-￦]/;

  /** 글자 덩어리를 한 자씩 쪼개고 각 글자의 가로 위치를 어림한다.
   *
   * PDF 안에서 '한 예' 처럼 사이를 벌려 찍고 그 틈에 '*' 를 겹쳐 찍은 이름이 있다.
   * 덩어리째 다루면 '한 예*' 가 되어 버리므로, 한 자씩 놓고 위치 순으로 다시 세운다.
   * 덩어리 안의 빈칸은 PDF가 만들어 낸 자리이므로 버리고, 나중에 글자 사이가
   * 벌어진 곳에만 띄어쓰기를 넣는다.
   */
  function splitChars(item, top) {
    var text = item.str, total = 0, weights = [];
    for (var i = 0; i < text.length; i++) {
      var weight = WIDE_CHAR.test(text[i]) ? 2 : 1;
      weights.push(weight); total += weight;
    }
    if (!total) return [];
    var x = item.transform[4], width = item.width || 0, acc = 0, out = [];
    for (var j = 0; j < text.length; j++) {
      var advance = width * weights[j] / total;
      out.push({ x: x + acc, w: advance, y: top, s: text[j], blank: !text[j].trim() });
      acc += advance;
    }
    return out;
  }

  function bandIndex(bounds, value) {
    for (var i = 0; i < bounds.length - 1; i++) {
      if (value >= bounds[i] && value < bounds[i + 1]) return i;
    }
    return -1;
  }

  /** 선분들이 [from, to] 구간을 빈틈없이 덮는지 본다. 괘선이 여러 토막일 수 있다. */
  function covers(segments, from, to, tolerance) {
    var reach = from - tolerance;
    var sorted = segments.slice().sort(function (a, b) { return a[0] - b[0]; });
    for (var i = 0; i < sorted.length; i++) {
      if (sorted[i][0] > reach + tolerance) break;      // 빈틈
      if (sorted[i][1] > reach) reach = sorted[i][1];
      if (reach >= to - tolerance) return true;
    }
    return reach >= to - tolerance;
  }

  // ------------------------------------------------------------------
  // 2) 글자를 격자에 담아 표 모양으로 만들기
  // ------------------------------------------------------------------
  function buildTable(textItems, pageHeight, rulings) {
    var MIN_RULE = 15;   // 이보다 짧은 선만 모인 자리는 표 괘선으로 보지 않는다
    var xs = clusterPositions(rulings.verticals.map(function (v) {
      return { pos: v.x, from: v.y0, to: v.y1 };
    }), 2, MIN_RULE);
    var ys = clusterPositions(rulings.horizontals.map(function (h) {
      return { pos: h.y, from: h.x0, to: h.x1 };
    }), 2, MIN_RULE);
    if (xs.length < 3 || ys.length < 2) return null;
    var nrows = ys.length - 1, ncols = xs.length - 1;

    // 어느 칸 경계에 실제로 선이 그어져 있는지 — 선이 없으면 병합된 칸이다.
    function edgeMap(bounds, segments, key, spanBounds) {
      var map = [];
      for (var i = 0; i < bounds.length; i++) {
        var here = segments.filter(function (s) { return Math.abs(s[key] - bounds[i]) <= 2; })
          .map(function (s) { return s.range; });
        var line = [];
        for (var j = 0; j < spanBounds.length - 1; j++) {
          line.push(here.length ? covers(here, spanBounds[j], spanBounds[j + 1], 1.5) : false);
        }
        map.push(line);
      }
      return map;
    }

    var hSegments = rulings.horizontals.map(function (h) { return { y: h.y, range: [h.x0, h.x1] }; });
    var vSegments = rulings.verticals.map(function (v) { return { x: v.x, range: [v.y0, v.y1] }; });
    var hEdge = edgeMap(ys, hSegments, 'y', xs);   // hEdge[r][c] : r번째 가로줄이 c열을 지나는가
    var vEdge = edgeMap(xs, vSegments, 'x', ys);   // vEdge[c][r] : c번째 세로줄이 r행을 지나는가

    // 네 변이 모두 그어진 자리만 셀로 잡는다.
    function spans(edge, index, from, to) {     // edge[index] 가 from..to 를 모두 지나는가
      for (var i = from; i < to; i++) if (!edge[index][i]) return false;
      return true;
    }

    var found = [];
    for (var r0 = 0; r0 < nrows; r0++) {
      for (var c0 = 0; c0 < ncols; c0++) {
        if (!hEdge[r0][c0] || !vEdge[c0][r0]) continue;   // 위·왼쪽 변이 없다
        var picked = null;
        for (var r1 = r0 + 1; r1 <= nrows && !picked; r1++) {
          if (!hEdge[r1][c0]) continue;                   // 아래쪽 변 후보
          for (var c1 = c0 + 1; c1 <= ncols; c1++) {
            if (!vEdge[c1][r0]) continue;                 // 오른쪽 변 후보
            if (spans(hEdge, r0, c0, c1) && spans(hEdge, r1, c0, c1) &&
                spans(vEdge, c0, r0, r1) && spans(vEdge, c1, r0, r1)) {
              picked = [r1, c1];
              break;
            }
          }
        }
        if (picked) found.push({ r0: r0, c0: c0, r1: picked[0], c1: picked[1] });
      }
    }
    if (!found.length) return null;

    // 큰 칸(페이지 테두리 등)이 표 전체를 삼키지 않도록, 겹치면 작은 칸이 이긴다.
    found.sort(function (a, b) {
      return ((b.r1 - b.r0) * (b.c1 - b.c0)) - ((a.r1 - a.r0) * (a.c1 - a.c0));
    });
    var owner = [], cells = [];
    for (var r = 0; r < nrows; r++) {
      var ownerLine = [], cellLine = [];
      for (var c = 0; c < ncols; c++) { ownerLine.push(null); cellLine.push(null); }
      owner.push(ownerLine); cells.push(cellLine);
    }
    found.forEach(function (cell) {
      for (var rr = cell.r0; rr < cell.r1; rr++) {
        for (var cc = cell.c0; cc < cell.c1; cc++) owner[rr][cc] = [cell.r0, cell.c0];
      }
      cells[cell.r0][cell.c0] = [];
    });

    for (var i = 0; i < textItems.length; i++) {
      var it = textItems[i];
      if (!it.str) continue;
      var h = it.height || 10;
      var baseline = pageHeight - it.transform[5];
      var cy = baseline - h * 0.3;                 // 글자 중심을 위에서부터의 거리로
      var ri = bandIndex(ys, cy);
      if (ri < 0) continue;
      // 글자마다 제 위치로 칸을 정한다 — 덩어리로 넣으면 열 경계에서 밀린다
      splitChars(it, baseline).forEach(function (ch) {
        var ci = bandIndex(xs, ch.x + ch.w / 2);
        if (ci < 0) return;
        var own = owner[ri][ci];
        if (own) cells[own[0]][own[1]].push(ch);
      });
    }

    // 칸 안의 글자를 줄 단위로 묶어 문자열로 만든다.
    var table = [];
    for (var r2 = 0; r2 < cells.length; r2++) {
      var row = [];
      for (var c2 = 0; c2 < cells[r2].length; c2++) {
        var parts = cells[r2][c2];
        if (!parts) { row.push(null); continue; }       // 병합된 칸의 이어지는 자리
        if (!parts.length) { row.push(''); continue; }
        parts.sort(function (a, b) { return (a.y - b.y) || (a.x - b.x); });
        var lines = [], currentY = null, buf = [];
        for (var p = 0; p < parts.length; p++) {
          if (currentY === null || Math.abs(parts[p].y - currentY) <= LINE_GAP) {
            if (currentY === null) currentY = parts[p].y;
            buf.push(parts[p]);
          } else {
            lines.push(buf); buf = [parts[p]]; currentY = parts[p].y;
          }
        }
        if (buf.length) lines.push(buf);
        // 한 줄 안에서는 글자 사이가 벌어진 곳에만 띄어쓰기를 넣는다.
        // (PDF 안의 빈 글자는 자리 맞추기용이라 그대로 쓰면 엉뚱한 곳이 띄어진다)
        var text = lines.map(function (ln) {
          ln.sort(function (a, b) { return a.x - b.x; });
          // 다른 글자가 겹쳐 찍힌 빈칸은 실제 띄어쓰기가 아니라 자리 벌림이다
          var kept = ln.filter(function (t, i) {
            if (!t.blank) return true;
            for (var j = 0; j < ln.length; j++) {
              if (j === i || ln[j].blank) continue;
              var overlap = Math.min(t.x + t.w, ln[j].x + ln[j].w) - Math.max(t.x, ln[j].x);
              if (overlap > t.w * 0.3) return false;
            }
            return true;
          });
          var out = '', reach = null;
          kept.forEach(function (t) {
            if (reach !== null && t.x - reach > WORD_GAP && !t.blank) out += ' ';
            out += t.s;
            reach = reach === null ? t.x + t.w : Math.max(reach, t.x + t.w);
          });
          return out.replace(/\s{2,}/g, ' ').trim();
        }).filter(function (t) { return t.length; }).join('\n');
        row.push(text);
      }
      table.push(row);
    }
    return table;
  }

  // ------------------------------------------------------------------
  // 3) 머리글 해석 (land_schedule.py 의 _build_layout / locate_layout)
  // ------------------------------------------------------------------
  function headerSpan(rows) {
    if (rows.length > 1) {
      var second = rows[1].map(norm);
      for (var i = 0; i < second.length; i++) {
        if (SUB_HEADERS.indexOf(squash(second[i])) !== -1) return 2;
      }
    }
    return 1;
  }

  function buildLayout(rows) {
    if (!rows.length) return null;
    var span = headerSpan(rows);
    var head = rows.slice(0, span).map(function (r) { return r.map(norm); });
    var width = Math.max.apply(null, head.map(function (r) { return r.length; }));
    head.forEach(function (r) { while (r.length < width) r.push(''); });

    var topFlat = head[0].join(' ');
    if (!(hasAny(topFlat, KEY_HEADERS) && hasAny(topFlat, ANCHOR_HEADERS))) return null;

    var top = [], carry = '';
    for (var i = 0; i < head[0].length; i++) {
      if (head[0][i]) carry = head[0][i];
      top.push(carry);
    }

    var columns = [], colIndex = [];
    for (var idx = 0; idx < width; idx++) {
      var upper = flatten(head[0][idx], '');
      var lower = span > 1 ? flatten(head[1][idx], '') : '';
      var mergedUpper = flatten(top[idx], '');
      var name;
      if (lower && mergedUpper && lower !== mergedUpper) name = mergedUpper.replace(/ /g, '') + ' ' + lower;
      else if (lower) name = lower;
      else if (upper) name = upper;
      else name = '';
      if (!name) continue;
      columns.push(name.replace(/\n/g, ' ').trim());
      colIndex.push(idx);
    }

    var seen = {};
    for (var n = 0; n < columns.length; n++) {
      if (seen[columns[n]]) { seen[columns[n]] += 1; columns[n] = columns[n] + seen[columns[n]]; }
      else seen[columns[n]] = 1;
    }

    var keyCol = -1, anchorCol = null;
    for (var c = 0; c < columns.length; c++) {
      if (keyCol < 0 && hasAny(columns[c], KEY_HEADERS)) keyCol = c;
      if (anchorCol === null && hasAny(columns[c], ANCHOR_HEADERS)) anchorCol = c;
    }
    if (keyCol < 0) return null;

    return { columns: columns, colIndex: colIndex, keyCol: keyCol, headerRows: span, anchorCol: anchorCol };
  }

  function locateLayout(table) {
    var limit = Math.min(MAX_HEADER_SEARCH, table.length);
    for (var offset = 0; offset < limit; offset++) {
      var layout = buildLayout(table.slice(offset));
      if (layout) { layout.headerRows += offset; return layout; }
    }
    return null;
  }

  // ------------------------------------------------------------------
  // 4) 여러 줄에 걸친 한 필지를 한 행으로 합치기 (_merge_rows)
  // ------------------------------------------------------------------
  function mergeRows(layout, body, pageNo) {
    var ordered = [], warnings = [];
    var current = null, currentIsSubtotal = false;
    var keyName = layout.columns[layout.keyCol];
    var anchorName = layout.anchorCol === null ? null : layout.columns[layout.anchorCol];

    function flush() {
      if (!current) return;
      var row = {};
      layout.columns.forEach(function (column) {
        var text = current[column].join(glueFor(column)).trim().replace(/\s{2,}/g, ' ');
        row[column] = isNumericColumn(column) ? toNumber(text) : text;
      });
      row['페이지'] = pageNo;
      ordered.push([currentIsSubtotal ? 'subtotal' : 'record', row]);
      current = null; currentIsSubtotal = false;
    }

    for (var i = 0; i < body.length; i++) {
      var raw = body[i];
      var cells = layout.colIndex.map(function (idx) { return norm(raw[idx]); });
      var key = squash(cells[layout.keyCol]);
      var anchor = layout.anchorCol === null ? '' : cells[layout.anchorCol];
      var isSubtotal = SUBTOTAL_LABELS.indexOf(key) !== -1;

      // 번호가 가운데 정렬 탓에 자료보다 한 줄 아래 찍힌 경우
      var numberOfCurrent = !!(current && key && !isSubtotal && !anchor && !current[keyName].length);

      var startsRecord = !numberOfCurrent && (
        !!key || (anchorName && anchor && current && current[anchorName].length > 0)
      );

      if (startsRecord) {
        flush();
        current = {};
        layout.columns.forEach(function (c) { current[c] = []; });
        currentIsSubtotal = isSubtotal;
      } else if (!current) {
        if (cells.some(function (v) { return v; })) {
          warnings.push(pageNo + '쪽: 번호 없는 행을 만나 앞 페이지 항목에 붙이지 못했습니다.');
        }
        continue;
      }

      for (var c2 = 0; c2 < layout.columns.length; c2++) {
        if (cells[c2]) current[layout.columns[c2]].push(flatten(cells[c2], glueFor(layout.columns[c2])));
      }
    }
    flush();
    return { ordered: ordered, warnings: warnings };
  }

  // ------------------------------------------------------------------
  // 5) 소계 검증 (verify)
  // ------------------------------------------------------------------
  function numericColumns(columns) { return columns.filter(isNumericColumn); }

  function groupColumn(columns) {
    for (var i = 0; i < columns.length; i++) {
      if (hasAny(columns[i], ['소재지', '시군'])) return columns[i];
    }
    return null;
  }

  function round4(v) { return Math.round(v * 10000) / 10000; }

  function verify(result) {
    if (!result.subtotals.length) return [];
    var numCols = numericColumns(result.columns);
    var groupCol = groupColumn(result.columns);
    var report = [], bucket = [];

    function summarize(row, page) {
      var entry = {
        '구간': (bucket.length && groupCol) ? bucket[0][groupCol] : '',
        '건수': bucket.length,
        '소계 페이지': page
      };
      numCols.forEach(function (col) {
        var computed = 0;
        bucket.forEach(function (r) { if (typeof r[col] === 'number') computed += r[col]; });
        var stated = row ? row[col] : '';
        entry[col + ' 합산'] = round4(computed);
        entry[col + ' 소계'] = stated;
        entry[col + ' 차이'] = (typeof stated === 'number') ? round4(computed - stated) : '';
      });
      report.push(entry);
      bucket = [];
    }

    result.sequence.forEach(function (pair) {
      if (pair[0] === 'record') bucket.push(pair[1]);
      else summarize(pair[1], pair[1]['페이지']);
    });
    if (bucket.length) summarize(null, '(소계 없음)');
    return report;
  }

  // ------------------------------------------------------------------
  // 6) PDF 한 개를 통째로 읽기
  // ------------------------------------------------------------------
  async function extract(pdfjsLib, data, onProgress) {
    var doc = await pdfjsLib.getDocument({ data: data, isEvalSupported: false }).promise;
    var result = {
      columns: [], records: [], subtotals: [], sequence: [],
      warnings: [], pagesWithTable: 0, totalPages: doc.numPages
    };
    var layout = null;

    for (var pageNo = 1; pageNo <= doc.numPages; pageNo++) {
      var page = await doc.getPage(pageNo);
      var viewport = page.getViewport({ scale: 1 });
      var content = await page.getTextContent();
      var opList = await page.getOperatorList();
      var rulings = collectRulings(opList, pdfjsLib.OPS, viewport.height);
      var table = buildTable(content.items, viewport.height, rulings);
      page.cleanup();

      if (table) {
        var pageLayout = locateLayout(table);
        if (pageLayout) {
          if (!layout) { layout = pageLayout; result.columns = pageLayout.columns.slice(); }
          else if (pageLayout.columns.join('') !== layout.columns.join('')) {
            result.warnings.push(pageNo + '쪽: 앞 페이지와 표 머리글이 다릅니다. 이 페이지 머리글 기준으로 읽습니다.');
          }
          var merged = mergeRows(pageLayout, table.slice(pageLayout.headerRows), pageNo);
          merged.ordered.forEach(function (pair) {
            result.sequence.push(pair);
            if (pair[0] === 'record') result.records.push(pair[1]);
            else result.subtotals.push(pair[1]);
          });
          result.warnings = result.warnings.concat(merged.warnings);
          result.pagesWithTable += 1;
        }
      }
      if (onProgress) await onProgress(pageNo, doc.numPages);
    }

    if (!layout) {
      throw new Error('이 PDF에서 토지세목조서 표를 찾지 못했습니다. 스캔한 이미지 PDF라면 먼저 OCR이 필요합니다.');
    }

    result.records.concat(result.subtotals).forEach(function (row) {
      result.columns.forEach(function (c) { if (!(c in row)) row[c] = ''; });
    });
    return result;
  }

  return {
    extract: extract,
    verify: verify,
    numericColumns: numericColumns,
    isNumericColumn: isNumericColumn,
    SUBTOTAL_LABELS: SUBTOTAL_LABELS,
    // 아래는 점검·시험용
    collectRulings: collectRulings,
    clusterPositions: clusterPositions,
    covers: covers,
    buildTable: buildTable,
    locateLayout: locateLayout,
    mergeRows: mergeRows
  };
});
