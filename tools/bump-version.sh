#!/bin/sh
# 更新 index.html 內 CSS／JS 的版本號，讓瀏覽器在每次部署後重新抓取新檔（避免快取舊版）
cd "$(dirname "$0")/.." || exit 1
V=$(date +%Y%m%d%H%M)
sed -i '' -E "s#\?v=[0-9a-z]+\"#?v=$V\"#g" index.html
echo "assets version: $V"
