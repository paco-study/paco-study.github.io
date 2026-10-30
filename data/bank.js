/* 自編／書籍題庫（目前無資料；信託歷屆題在 data/bank-trust.js、期貨歷屆考古題在 data/bank-futures.js；題庫可用 tools/convert_bank.py 由 Excel／CSV 轉出並覆蓋本檔）
 *
 * 每題欄位
 *   id         唯一代碼（收藏、錯題本、作答紀錄都靠它對應，題庫更新時請保持不變）
 *   exam       科目代碼，需對應 data/meta.js 的 exams[].id
 *   subject    （選用）大分類，例如書名「證基會題庫｜期貨交易法規」
 *   topic      主題／章節／「官方題庫 ─ 2025 年」
 *   kind       self＝自編詳解題（逐選項解析）　off＝官方歷屆試題　book＝書籍題庫（依章節）
 *   difficulty 1～3
 *   q          題目　options 四個選項　answer 正確選項索引（0＝A … 3＝D）
 *   explain    逐選項解析（四格，可空字串）　note 整題解析　src 出處
 */
window.__BANK__ = window.__BANK__ || {};
