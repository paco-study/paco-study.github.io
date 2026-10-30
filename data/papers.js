/* 歷屆整份試卷（目前無資料，各科歷屆試卷由 bank-trust.js、bank-futures.js 加入；正式資料請用 tools/convert_bank.py --papers 轉出覆蓋）
 * 每份試卷：id、exam（科目代碼）、examName、yROC（民國年）、yCE（西元年）、sess（第幾次）、label、qn、questions[{q, options[4], answer, note}]
 */
window.__PAPERS__ = window.__PAPERS__ || [];
