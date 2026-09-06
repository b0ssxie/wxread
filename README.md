# wxread · 微信读书自动阅读

通过复用官网 `read` 接口自动刷阅读时长、保挑战赛天数。支持**多账号**、**Cookie 自动续签**、**多渠道推送**，可跑在 GitHub Actions 或 Docker/服务器上，仅依赖 `requests` + `urllib3`，无需挂阅读器或 ADB。

## 功能特性

- **时长可调**：每次成功请求计约 30 秒，`READ_NUM=40` 即约 20 分钟
- **多账号**：一个变量配多条 curl，顺序执行、每账号独立推送
- **Cookie 自动续签**：`wr_skey` 失效自动刷新，`synckey` 缺失自动修复
- **推送**：pushplus / wxpusher / telegram / serverchan，失败自动重试（5 次，3–6 分钟退避）
- **轻量定时**：GitHub Actions 每天 01:00（北京时间）自动运行；Docker 内置 cron 同步执行

## 快速开始：抓包

1. 打开 [微信读书](https://weread.qq.com/)，搜索《三体》进入阅读并翻页
2. 抓到 `https://weread.qq.com/web/book/read`，确认返回正常：
   ```json
   {"succ": 1, "synckey": 564589834}
   ```
3. 右键复制为 cURL（bash 格式），后续填入配置

> 注意：`config.py` 中的 `data` 模板按《三体》调优，其他书籍可能不涨时长，**建议保留不要改**。

## 部署一：GitHub Actions（推荐）

1. Fork 本仓库
2. 仓库 **Settings** → **Secrets and variables** → **Actions**：
   - **Secrets**（必填）：`WXREAD_CURL_BASH`（上一步复制的 curl bash）
   - **Secrets**（推送时必填）：`PUSH_METHOD`（`pushplus` / `wxpusher` / `telegram` / `serverchan` 四选一）及对应 token
   - **Variables**（可选）：`READ_NUM`（阅读次数，默认 40）
3. **Actions** 页手动触发验证一次；之后每天 01:00（北京时间）自动运行

### 多账号配置

`WXREAD_CURL_BASH` 中放入多条 curl 即可（每条对应一个账号），分隔方式任选其一：

- 显式分隔符：`|||` 或 `&&&`
- 多条 `curl ...` 换行粘贴
- 单行 `curl ... && curl ...`

各账号顺序执行、互不干扰，每账号单独推送，推送正文自动带 `账号1/2` 标识。

### 环境变量

| 变量 | 说明 | 属性 |
| --- | --- | --- |
| `WXREAD_CURL_BASH` | `read` 接口的 curl bash，必填，多账号见上 | Secrets |
| `READ_NUM` | 阅读次数，每次约 30 秒，默认 40（约 20 分钟） | Variables |
| `PUSH_METHOD` | `pushplus` / `wxpusher` / `telegram` / `serverchan`，不填则不推送 | Secrets |
| `PUSHPLUS_TOKEN` | `PUSH_METHOD=pushplus` 时必填（[获取](https://www.pushplus.plus/uc.html)） | Secrets |
| `WXPUSHER_SPT` | `PUSH_METHOD=wxpusher` 时必填（[获取](https://wxpusher.zjiecode.com/docs/#/?id=获取spt)） | Secrets |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`（可选 `http_proxy` / `https_proxy`） | `PUSH_METHOD=telegram` 时必填（[配置参考](https://www.nodeseek.com/post-22475-1)） | Secrets |
| `SERVERCHAN_SPT` | `PUSH_METHOD=serverchan` 时必填（[获取](https://sct.ftqq.com/sendkey)） | Secrets |

**提醒：除 `READ_NUM` 放 Variables 外，其余都放 Secrets；需要推送时 `PUSH_METHOD` 必填。**

### 视频教程

[![视频教程](https://github.com/user-attachments/assets/ec144869-3dbb-40fe-9bc5-f8bf1b5fce3c)](https://www.bilibili.com/video/BV1kJ6gY3En3/ "点击查看视频")

## 部署二：服务器 / Docker

```bash
git clone https://github.com/b0ssxie/wxread.git
```

1. 直接运行：按抓包结果填写 `config.py` 中的 `headers`、`cookies`（可用 [curlconverter](https://curlconverter.com/python/) 把 curl 转成 Python 字典，`data` 不用动），然后：
   ```bash
   python main.py
   ```
   或用 `cron` 定时执行。
2. Docker（内置 cron，每天 01:00 北京时间执行）：
   ```bash
   docker rm -f wxread && docker build -t wxread . && docker run -d --name wxread -v $(pwd)/logs:/app/logs --restart always wxread
   docker exec -it wxread python /app/main.py
   ```

## 推送内容示例

成功（多账号时首行下方自动带账号标识，单账号省略）：

```text
微信读书自动阅读完成
账号：账号1/2
完成时间：2026-09-06 01:23:45
阅读次数：40 次
阅读时长：20.0 分钟
```

失败：

```text
微信读书自动阅读失败
账号：账号2/2
失败时间：2026-09-06 01:45:10
原因：无法获取新密钥或者 WXREAD_CURL_BASH 配置有误，终止运行。
```

## 常见问题

1. **阅读时长没涨**：保留 `data` 三体模板；先确认抓到的 `read` 接口返回含 `succ` + `synckey`。
2. **只需保天数/签到**：把 `READ_NUM` 调小（如 2，即约 1 分钟）即可。
3. **Cookie 失效**：脚本会自动续签 `wr_skey`；若原始 Cookie 已彻底过期，需重新抓包更新。
4. **推送没收到**：检查渠道名小写是否正确、token 是否配对；推送自带 5 次重试，偶发失败会延迟补发。

## 项目结构

| 文件 | 说明 |
| --- | --- |
| `main.py` | 入口：阅读循环、Cookie 刷新、多账号调度与推送 |
| `config.py` | 配置：headers/cookies、`READ_NUM`、推送 token、`data` 模板、curl 解析与多账号切分 |
| `push.py` | 推送：pushplus / wxpusher / telegram / serverchan |
| `log_utils.py` | 日志：同行进度刷新 |
| `Dockerfile` | Docker 构建 + 每日 01:00（北京时间）cron |
| `.github/workflows/deploy.yml` | GitHub Actions 定时任务 |

## read 接口字段解释

| 字段 | 示例值 | 解释 |
| --- | --- | --- |
| `appId` | `"wbxxxxxxxxxxxxxxxxxxxxxxxx"` | 应用的唯一标识符 |
| `b` | `"ce032b305a9bc1ce0b0dd2a"` | 书籍唯一标识符 |
| `c` | `"0723244023c072b030ba601"` | 内容唯一标识符（页面/段落） |
| `ci` | `60` | 章节索引 |
| `co` | `336` | 内容位置/页码 |
| `sm` | `"[插图]威慑纪元61年……"` | 当前阅读内容摘要 |
| `pr` | `65` | 页码/段落索引 |
| `rt` / `ct` / `ts` | 时间相关 | 阅读间隔/秒级时间戳/毫秒级时间戳 |
| `rn` | `114` | 随机数，标识唯一请求 |
| `sg` | `"bfdf7de2……"` | 安全签名，验证请求合法性 |
| `ps` / `pc` | `"xxx"` | 用户/设备标识 |
| `s` | `"fadcb9de"` | 校验和，验证数据完整性 |
