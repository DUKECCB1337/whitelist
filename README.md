# whitelist

HWID 白名单库。客户端用**只读细粒度 PAT** 读取本库的 `whitelist.json`，校验本机 HWID 是否在名单内；不在则退出。

## 设计要点

- **只读、单库**：给客户端的 PAT 只能读 `DUKECCB1337/whitelist`，权限仅 `Contents: Read`，不能读任何其他库、不能写。
- **只存哈希**：`whitelist.json` 里只放 `sha256(hwid)` 十六进制字符串，不放原始 HWID。
  这样即使 PAT 泄露 + 库被读光，泄露的也只是一堆单向哈希，无法还原设备 HWID，
  也无法用来伪造其他设备（伪造者仍需知道名单之外的原始 HWID 才能算出合法哈希）。
- **失败即拒绝**：客户端网络失败 / 401 / 403 / 解析失败 / 未命中 → 一律退出，不放行。

## 文件

```jsonc
{
  "_schema": 1,
  "_hash": "sha256",
  "hwids": [
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    { "id": "<sha256hex>", "note": "谁在用", "added": "2026-10-18", "enabled": true }
  ]
}
```

`hwids` 每项可以是纯字符串，也可以是带 `note` / `enabled` 的对象；`enabled: false` 表示已禁用。

## 客户端读取方式

私有库必须带 `Authorization` 头，两种等价写法：

```bash
# 1) raw（有 CDN 缓存，约 5 分钟，加时间戳绕过）
curl -sS -H "Authorization: Bearer $WL_TOKEN" \
  "https://raw.githubusercontent.com/DUKECCB1337/whitelist/main/whitelist.json?t=$(date +%s)"

# 2) Contents API（更稳、可强制不吃缓存，推荐）
curl -sS -H "Authorization: Bearer $WL_TOKEN" \
  -H "Accept: application/vnd.github.raw" \
  -H "Cache-Control: no-cache" \
  "https://api.github.com/repos/DUKECCB1337/whitelist/contents/whitelist.json"
```

`raw.githubusercontent.com` 在国内/某些网络下可能不可达，客户端应做双通道回退（raw → api）。

## 维护

用管理员 token（**不要**发到客户端）改 `whitelist.json` 后 push，或跑本地工具：

```bash
python3 ~/whitelist-kit/wl_admin.py add   <HWID> --note "谁"
python3 ~/whitelist-kit/wl_admin.py list
python3 ~/whitelist-kit/wl_admin.py disable <HWID>
```

## 安全提醒

客户端内嵌 PAT = PAT 会随 APK / 程序分发，反编译必得。因此：
1. 本库内容按"公开可读也不心疼"的标准写（即只放哈希）；
2. PAT 设最长有效期并及时轮换；
3. 若将来要放敏感数据，改成自建代理（Cloudflare Worker）持有 PAT，客户端只拿一次性签名。
