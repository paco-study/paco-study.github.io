#!/usr/bin/env python3
"""解析「115 期貨題庫」（書籍題庫，已轉成 .md），產生 data/bank-futures-book.js。

用法：python3 tools/parse_futures_bank.py 期貨題庫/期貨實務MD檔/期貨實務-題目            → 產生 data/bank-futures-book.js
      python3 tools/parse_futures_bank.py 期貨題庫/期貨實務MD檔/期貨實務-題目 檢查.json  → 只輸出解析結果供檢查
檔案格式：每章一個 .md（期貨實務-題1.md…），每題為
  ## 1. 題幹
  **答案：(2)**
  (1) 選項 … (4) 選項
  《解析》…（書上原文，僅供分類與改寫參考，不輸出到網站）
解析與主題：tools/annotations/fbk-prac-*.tsv（題號<TAB>主題代碼<TAB>本站改寫之解析[<TAB>?]）。
解析中引用之圖片（![說明](./xxx_images/檔名.png)）複製到 assets/qimg/，於解析下方顯示。
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANN_DIR = os.path.join(ROOT, 'tools', 'annotations')
IMG_OUT = os.path.join(ROOT, 'assets', 'qimg')
SUBJECT = '115 題庫'
EXAM = 'fut-prac'
CHAPTERS = {1: '期貨交易概論', 2: '國外期貨交易實務', 3: '期貨避險交易', 4: '期貨投機交易與價差交易',
            5: '選擇權基本概念與交易策略', 6: '臺灣期貨交易所期貨與選擇權交易實務', 7: '臺灣期貨交易所股份有限公司業務規則'}


def parse_file(path):
    text = open(path, encoding='utf-8').read()
    blocks = re.split(r'(?m)^##\s+', text)[1:]
    out, problems = [], []
    for b in blocks:
        m = re.match(r'(\d{1,3})\s*[\.．]\s*(.*)', b, re.S)
        if not m:
            problems.append(('?', '無法辨識題號', b[:40]))
            continue
        no, body = int(m.group(1)), m.group(2)
        exp = ''
        if '《解析》' in body:
            body, exp = body.split('《解析》', 1)
        imgs = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', body + exp)
        body = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', body)
        am = re.search(r'\*\*答案[：:]\s*[\(（]?\s*([1-4])\s*[\)）]?\s*\*\*', body)
        ans = int(am.group(1)) - 1 if am else None
        if am:
            body = body[:am.start()] + '\n' + body[am.end():]
        stem_lines, opts = [], []
        for line in body.split('\n'):
            om = re.match(r'^\s*[\(（]\s*([1-4])\s*[\)）]\s*(.*)$', line)
            if om and int(om.group(1)) == len(opts) + 1:
                opts.append(om.group(2).strip())
            elif opts and line.strip():
                opts[-1] += line.strip()
            elif not opts:
                stem_lines.append(line.rstrip())
        stem = '\n'.join(l for l in stem_lines if l.strip()).strip()
        if ans is None:
            problems.append((no, '找不到答案', stem[:40]))
        if len(opts) != 4 or not all(opts):
            problems.append((no, '選項數 %d' % len(opts), stem[:40]))
        out.append({'no': no, 'q': stem, 'options': opts, 'answer': ans, 'exp': exp.strip(), 'imgs': imgs})
    return out, problems


def tidy(t):
    """修正轉檔常見錯字：分數黏在一起（6422/4→642 2/4）、選項代號改為 (A)(B)(C)、± 符號等。"""
    t = re.sub(r'(?<![\d/])(\d{3})(\d{1,2})/(4|32)(?!\d)', lambda m: '%s %s/%s' % m.groups() if int(m.group(2)) < int(m.group(3)) else m.group(0), t)
    t = re.sub(r'選項((?:\s*(?:[\(（][1-4][\)）]|[、與及和或,，]))+)',
               lambda m: '選項' + re.sub(r'[\(（]([1-4])[\)）]', lambda d: '(%s)' % 'ABCD'[int(d.group(1)) - 1], m.group(1)), t)
    t = re.sub(r'(\([A-D]\))\1+', r'\1', t)
    t = re.sub(r'[士土](?=\d)', '±', t)
    for a_, b_ in (('MIIT', 'MIT'), ('DJLA', 'DJIA'), ('MITT', 'MIT'), ('RHIF', 'RHF'), ('TMIF', 'TMF'), ('S0Q', 'SOQ')):
        t = t.replace(a_, b_)
    return t.strip()


def load_fixes():
    path = os.path.join(ANN_DIR, 'fbk-fixes.tsv')
    fx = {}
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            p = line.rstrip('\n').split('\t')
            if len(p) == 3:
                fx.setdefault(p[0], {})[p[1]] = p[2]
    return fx


def load_annotations():
    topics = json.load(open(os.path.join(ANN_DIR, 'topics.json'), encoding='utf-8'))
    ann = {}
    for f in sorted(os.listdir(ANN_DIR)):
        if f.startswith('fbk-') and f.endswith('.tsv'):
            for line in open(os.path.join(ANN_DIR, f), encoding='utf-8'):
                p = line.rstrip('\n').split('\t')
                if len(p) >= 3:
                    ann[p[0]] = {'code': p[1], 'note': p[2].replace('\\n', '\n'), 'nv': len(p) > 3 and p[3] == '?'}
    return topics, ann


def main(src, dst):
    chapters, report = {}, []
    for f in sorted(os.listdir(src)):
        m = re.fullmatch(r'期貨實務-題(\d+)\.md', f)
        if not m:
            continue
        ch = int(m.group(1))
        qs, problems = parse_file(os.path.join(src, f))
        nos = [q['no'] for q in qs]
        gaps = [n for n in range(1, max(nos) + 1) if n not in nos] if nos else []
        dup = sorted({n for n in nos if nos.count(n) > 1})
        report.append('第 %d 章：%d 題，缺號 %s，重號 %s，問題 %d' % (ch, len(qs), gaps or '無', dup or '無', len(problems)))
        for pr in problems:
            report.append('    ⚠️ 第 %s 題：%s ─ %s' % pr)
        chapters[ch] = qs
    print('\n'.join(report))
    if not dst.endswith('.js'):
        json.dump(chapters, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        return
    topics, ann = load_annotations()
    fixes = load_fixes()
    os.makedirs(IMG_OUT, exist_ok=True)
    bank, missing = [], []
    for ch in sorted(chapters):
        for q in chapters[ch]:
            qid = 'FP-BK-%d-%03d' % (ch, q['no'])
            if q['answer'] is None or len(q['options']) != 4:
                continue
            fx = fixes.get(qid, {})
            q['q'] = fx.get('q') or tidy(q['q'])
            q['options'] = [fx.get('ABCD'[i]) or tidy(o) for i, o in enumerate(q['options'])]
            a = ann.get(qid)
            if not a:
                missing.append(qid)
            item = {'id': qid, 'exam': EXAM, 'subject': SUBJECT,
                    'topic': topics[EXAM][a['code']] if a else '第 %d 章 %s' % (ch, CHAPTERS.get(ch, '')), 'kind': 'book',
                    'difficulty': 2, 'q': q['q'], 'options': q['options'], 'answer': q['answer'],
                    'explain': ['', '', '', ''], 'note': a['note'] if a else '',
                    'src': '115 期貨商業務員題庫｜期貨交易理論與實務 第 %d 章 %s 第 %d 題' % (ch, CHAPTERS.get(ch, ''), q['no'])}
            if a and a['nv']:
                item['nv'] = 1
            imgs = []
            for p in q['imgs']:
                name = os.path.basename(p)
                s = os.path.join(src, p)
                if os.path.exists(s):
                    out = os.path.join(IMG_OUT, name)
                    shutil.copyfile(s, out)
                    if shutil.which('sips'):  # 縮成最長邊 900px，減少網頁載入量
                        subprocess.run(['sips', '-Z', '900', out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    imgs.append('assets/qimg/' + name)
            if imgs:
                item['img'] = imgs
            bank.append(item)
    if missing:
        print('⚠️  尚無解析與主題的題目 %d 題：%s' % (len(missing), ', '.join(missing[:10])))
    order = {v: i for i, v in enumerate(topics[EXAM].values())}
    bank.sort(key=lambda x: (order.get(x['topic'], 99), x['id']))
    with open(dst, 'w', encoding='utf-8') as f:
        f.write('/* 由 tools/parse_futures_bank.py 產生（來源：期貨題庫/*.md），請勿手動編輯 */\n')
        f.write('(function (B) {\n')
        f.write('B[%s] = (B[%s] || []).concat(%s);\n' % (json.dumps(EXAM), json.dumps(EXAM), json.dumps(bank, ensure_ascii=False, separators=(',', ':'))))
        f.write('})(window.__BANK__ = window.__BANK__ || {});\n')
    print('已寫入 %s：%s %d 題' % (dst, SUBJECT, len(bank)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'data', 'bank-futures-book.js'))
