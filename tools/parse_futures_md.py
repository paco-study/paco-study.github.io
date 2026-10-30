#!/usr/bin/env python3
"""解析證基會「期貨商業務員資格測驗」歷屆考古題（已轉成 .md），配對官方答案。

用法：python3 tools/parse_futures_md.py 期貨考古題            → 產生 data/bank-futures.js
      python3 tools/parse_futures_md.py 期貨考古題 檢查.json  → 只輸出解析結果供檢查
資料夾結構：每年一個子資料夾（110、111…），每次測驗兩個 .md：試題（如 11001.md）與答案（11001a.md）。
試題格式：「## 期貨交易法規」「## 期貨交易理論與實務」分節，「### 1. 題幹」後接「- (A) 選項」。
答案格式：同樣分節，表格「| 題號 | 答案 |」。
目前只處理 110 年起新格式（檔名為 5 碼數字）；105～109 年舊格式之後另行補上。
"""
import json
import os
import re
import sys

ANN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'annotations')
SUBJ = {'law': ('fut-law', '期貨交易法規', 'FL'), 'prac': ('fut-prac', '期貨交易理論與實務', 'FP')}
SOURCE = '歷屆考古題'
MIN_YEAR = 110  # 105～109 年考古題尚未整理（含解析），暫不匯入


def sec_key(title):
    if '法規' in title:
        return 'law'
    if '理論' in title or '實務' in title:
        return 'prac'
    return None


def split_sections(text):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r'^##\s+(.+?)\s*$', line)
        if m and not line.startswith('###'):
            cur = sec_key(m.group(1))
            if cur:
                out[cur] = []
            continue
        if cur:
            out[cur].append(line)
    return {k: '\n'.join(v) for k, v in out.items()}


HEADER = re.compile(r'\s*\d{3}\s*年第\s*\d+\s*次期貨商業務員資格測驗試題\s*$')


def clean(s):
    s = re.sub(r'[ \t]+', ' ', s.strip())
    # 每節最後一題的選項後面會接到試卷頁首文字
    return HEADER.sub('', s)


def parse_questions(text):
    qs, problems = {}, []
    blocks = re.split(r'(?m)^###\s+', text)
    for b in blocks[1:]:
        m = re.match(r'(\d{1,2})\s*[\.．、]\s*(.*)', b, re.S)
        if not m:
            problems.append(('?', '無法辨識題號', b[:60]))
            continue
        n, body = int(m.group(1)), m.group(2)
        lines = body.split('\n')
        stem, opts, cur = [], [], None
        for l in lines:
            om = re.match(r'^\s*[-*]\s*[\(（]\s*([A-D])\s*[\)）]\s*(.*)$', l)
            if om and len(opts) < 4 and ord(om.group(1)) - 65 == len(opts):
                opts.append([om.group(2)])
                cur = opts[-1]
            elif cur is not None:
                if l.strip():
                    cur.append(l.strip())
            else:
                stem.append(l)
        stem_t = '\n'.join(stem).strip()
        stem_t = re.sub(r'\n{2,}', '\n', stem_t)
        opts = [clean(' '.join(o)) for o in opts]
        if len(opts) != 4 or not all(opts) or not stem_t:
            problems.append((n, '選項數 %d' % len(opts), stem_t[:60]))
            continue
        if n in qs:
            problems.append((n, '題號重複', stem_t[:40]))
        qs[n] = {'q': stem_t, 'options': opts}
    return qs, problems


def parse_answers(text):
    out = {}
    for k, sec in split_sections(text).items():
        out[k] = {int(n): a.strip() for n, a in re.findall(r'(?m)^\|\s*(\d{1,2})\s*\|\s*([^|]*?)\s*\|', sec)}
    return out


def norm_key(q, opts):
    return re.sub(r'\s', '', q)[:60] + '|' + re.sub(r'\s', '', '|'.join(opts))


def load_annotations():
    topics = json.load(open(os.path.join(ANN_DIR, 'topics.json'), encoding='utf-8'))
    ann = {}
    for f in sorted(os.listdir(ANN_DIR)):
        if f.startswith('fut-') and f.endswith('.tsv'):
            for line in open(os.path.join(ANN_DIR, f), encoding='utf-8'):
                p = line.rstrip('\n').split('\t')
                if len(p) >= 3:
                    ann[p[0]] = {'code': p[1], 'note': p[2], 'nv': len(p) > 3 and p[3] == '?'}
    return topics, ann


def load_excluded():
    path = os.path.join(ANN_DIR, 'excluded.tsv')
    if not os.path.exists(path):
        return {}
    return dict(l.rstrip('\n').split('\t', 1) for l in open(path, encoding='utf-8') if '\t' in l)


def qid_of(pre, p, no):
    return '%s-OF-%d%d-%02d' % (pre, p['year'], p['sess'], no)


def emit_js(papers, dst):
    """產生 data/bank-futures.js：題庫（歷屆考古題）＋整份歷屆試卷（以題號引用題庫）。"""
    bank, plist = {'fut-law': [], 'fut-prac': []}, []
    topics, ann = load_annotations()
    excluded = load_excluded()
    # 解析只寫在每組重複題的其中一題，依題目內容套用到所有重複題
    by_key, all_q = {}, []
    for p in papers:
        _, _, pre = SUBJ[p['subject']]
        for q in p['questions']:
            qid = qid_of(pre, p, q['no'])
            all_q.append((qid, norm_key(q['q'], q['options'])))
            if qid in ann:
                by_key[norm_key(q['q'], q['options'])] = ann[qid]
    missing = [qid for qid, k in all_q if k not in by_key]
    if missing:
        print('⚠️  尚無解析與主題的題目 %d 題：%s' % (len(missing), ', '.join(missing[:10])))
    for p in sorted(papers, key=lambda x: (-x['year'], -x['sess'], x['subject'])):
        exam, name, pre = SUBJ[p['subject']]
        ids, dropped = [], []
        for q in p['questions']:
            qid = qid_of(pre, p, q['no'])
            if q['answer'] is None or qid in excluded:
                dropped.append({'no': q['no'], 'why': excluded.get(qid) or '官方答案：%s' % q.get('ansRaw', '')})
                continue
            ids.append(qid)
            a = by_key.get(norm_key(q['q'], q['options']))
            item = {
                'id': qid, 'exam': exam, 'subject': SOURCE,
                'topic': topics[exam][a['code']] if a else '%d 年第 %d 次' % (p['year'], p['sess']), 'kind': 'off',
                'difficulty': 2, 'q': q['q'], 'options': q['options'], 'answer': q['answer'],
                'explain': ['', '', '', ''], 'note': a['note'] if a else '',
                'src': '民國 %d 年第 %d 次期貨商業務員資格測驗｜%s 第 %d 題（證基會公布之試題與答案）' % (p['year'], p['sess'], name, q['no'])}
            if a and a['nv']:
                item['nv'] = 1
            bank[exam].append(item)
        pp = {'id': '%s-p%d%d' % (exam, p['year'], p['sess']), 'exam': exam, 'examName': name,
              'yROC': p['year'], 'yCE': p['year'] + 1911, 'sess': p['sess'],
              'label': '%d 年第 %d 次' % (p['year'], p['sess']), 'sessUnit': '次', 'qn': len(ids), 'qids': ids}
        if dropped:
            pp['dropped'] = dropped
        plist.append(pp)
    for k in bank:
        order = {v: i for i, v in enumerate(topics.get(k, {}).values())}
        bank[k].sort(key=lambda x: (order.get(x['topic'], 99), x['id']))
    with open(dst, 'w', encoding='utf-8') as f:
        f.write('/* 由 tools/parse_futures_md.py 產生（來源：期貨考古題/*.md），請勿手動編輯 */\n')
        f.write('(function (B, P) {\n')
        for k, v in bank.items():
            f.write('B[%s] = (B[%s] || []).concat(%s);\n' % (json.dumps(k), json.dumps(k), json.dumps(v, ensure_ascii=False, separators=(',', ':'))))
        f.write('P.push.apply(P, %s);\n' % json.dumps(plist, ensure_ascii=False, separators=(',', ':')))
        f.write('})(window.__BANK__ = window.__BANK__ || {}, window.__PAPERS__ = window.__PAPERS__ || []);\n')
    print('已寫入 %s：期貨交易法規 %d 題、期貨交易理論與實務 %d 題、試卷 %d 份' % (dst, len(bank['fut-law']), len(bank['fut-prac']), len(plist)))


def main(root, dst):
    papers, report = [], []
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            m = re.fullmatch(r'(\d{3})(\d{2})\.md', f)
            if not m:
                continue
            af = os.path.join(p, '%s%sa.md' % m.groups())
            if not os.path.exists(af):
                report.append('%s：找不到答案檔' % f)
                continue
            year, sess = int(m.group(1)), int(m.group(2))
            if year < MIN_YEAR:
                continue
            secs = split_sections(open(os.path.join(p, f), encoding='utf-8').read())
            ans = parse_answers(open(af, encoding='utf-8').read())
            for key in ('law', 'prac'):
                qs, problems = parse_questions(secs.get(key, ''))
                a = ans.get(key, {})
                items = []
                for i in sorted(qs):
                    av = a.get(i, '')
                    item = dict(no=i, **qs[i])
                    if re.fullmatch(r'[A-D]', av):
                        item['answer'] = ord(av) - 65
                    else:
                        item['answer'] = None
                        item['ansRaw'] = av
                        problems.append((i, '答案非單一選項', av))
                    items.append(item)
                missing = [i for i in range(1, 51) if i not in qs]
                report.append('%d 年第 %d 次 %s：題目 %d，答案 %d，缺題 %s，問題 %d' % (
                    year, sess, '法規' if key == 'law' else '實務', len(qs), len(a), missing or '無', len(problems)))
                for pr in problems:
                    report.append('    ⚠️ 第 %s 題：%s ─ %s' % pr)
                papers.append({'year': year, 'sess': sess, 'subject': key, 'questions': items})
    print('\n'.join(report))
    if dst.endswith('.js'):
        emit_js(papers, dst)
    else:
        json.dump(papers, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'data/bank-futures.js')
