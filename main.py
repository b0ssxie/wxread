# main.py 主逻辑：包括字段拼接、模拟请求（支持多账号顺序执行，每账号独立推送）
import copy
import json
import time
import random
import logging
import hashlib
import requests
import urllib.parse
from datetime import datetime
from push import push
from log_utils import setup_logging
from config import data, headers, cookies, READ_NUM, PUSH_METHOD, book, chapter, get_accounts


# 加密盐及其它默认值
KEY = "3c5c8717f3daf09iop3423zafeqoi"
READ_URL = "https://weread.qq.com/web/book/read"
RENEW_URL = "https://weread.qq.com/web/login/renewal"
FIX_SYNCKEY_URL = "https://weread.qq.com/web/book/chapterInfos"
COOKIE_DATA_VARIANTS = [{"rq": "%2Fweb%2Fbook%2Fread", "ql": False},{"rq": "%2Fweb%2Fbook%2Fread", "ql": True},{"rq": "%2Fweb%2Fbook%2Fread"},]


def encode_data(data):
    """数据编码"""
    return '&'.join(f"{k}={urllib.parse.quote(str(data[k]), safe='')}" for k in sorted(data.keys()))


def cal_hash(input_string):
    """计算哈希值"""
    _7032f5 = 0x15051505
    _cc1055 = _7032f5
    length = len(input_string)
    _19094e = length - 1

    while _19094e > 0:
        _7032f5 = 0x7fffffff & (_7032f5 ^ ord(input_string[_19094e]) << (length - _19094e) % 30)
        _cc1055 = 0x7fffffff & (_cc1055 ^ ord(input_string[_19094e - 1]) << _19094e % 30)
        _19094e -= 2

    return hex(_7032f5 + _cc1055)[2:].lower()

def get_wr_skey(headers, cookies):
    """刷新cookie密钥"""
    for cookie_data in COOKIE_DATA_VARIANTS:
        try:
            response = requests.post(RENEW_URL,headers=headers,cookies=cookies,data=json.dumps(cookie_data, separators=(',', ':')),timeout=10)

            if 'wr_skey' in response.cookies:
                return response.cookies['wr_skey'][:8]
            else:
                continue
        except requests.RequestException as exc:
            logging.warning(f"refresh_cookie 请求失败，payload={cookie_data}，原因：{exc}")
            continue


    return None

def fix_no_synckey(headers, cookies):
    requests.post(FIX_SYNCKEY_URL, headers=headers, cookies=cookies,data=json.dumps({"bookIds":["3300060341"]}, separators=(',', ':')))

refresh_print = setup_logging()

def refresh_cookie(headers, cookies, label=""):
    prefix = f"{label} " if label else ""
    logging.info(f"{prefix}刷新 cookie")
    new_skey = get_wr_skey(headers, cookies)
    if new_skey:
        cookies['wr_skey'] = new_skey
        logging.info(f"{prefix}密钥刷新成功，新密钥：{new_skey[:2]}***")
        logging.info(f"{prefix}重新本次阅读。")
    else:
        ERROR_CODE = f"{prefix}无法获取新密钥或者 WXREAD_CURL_BASH 配置有误，终止运行。"
        logging.error(ERROR_CODE)
        raise Exception(ERROR_CODE)


def format_label(index, total):
    return f"账号{index}/{total}" if total > 1 else ""


def build_success_report(label, minutes):
    """组装阅读成功推送正文，各推送渠道共用。"""
    lines = ["微信读书自动阅读完成"]
    if label:
        lines.append(f"账号：{label}")
    lines.append(f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"阅读次数：{READ_NUM} 次")
    lines.append(f"阅读时长：{minutes} 分钟")
    return "\n".join(lines)


def build_failure_report(label, error):
    """组装阅读失败推送正文，各推送渠道共用。"""
    lines = ["微信读书自动阅读失败"]
    if label:
        lines.append(f"账号：{label}")
    lines.append(f"失败时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"原因：{error}")
    return "\n".join(lines)


def run_account(headers, cookies, index=1, total=1):
    """运行单个账号的阅读循环，返回阅读分钟数。"""
    label = format_label(index, total)
    prefix = f"{label} " if label else ""
    account_data = copy.deepcopy(data)

    refresh_cookie(headers, cookies, label)
    read_index = 1
    lastTime = int(time.time()) - 30
    logging.info(f"{prefix}一共需要阅读 {READ_NUM} 次。")

    while read_index <= READ_NUM:
        account_data.pop('s')
        account_data['b'] = random.choice(book)
        account_data['c'] = random.choice(chapter)
        thisTime = int(time.time())
        account_data['ct'] = thisTime
        account_data['rt'] = thisTime - lastTime
        account_data['ts'] = int(thisTime * 1000) + random.randint(0, 1000)
        account_data['rn'] = random.randint(0, 1000)
        account_data['sg'] = hashlib.sha256(f"{account_data['ts']}{account_data['rn']}{KEY}".encode()).hexdigest()
        account_data['s'] = cal_hash(encode_data(account_data))

        refresh_print(f"{prefix}阅读进度: 第 {read_index}/{READ_NUM} 次，已完成 {(read_index - 1) * 0.5:.1f} 分钟")
        logging.debug("data: %s", account_data)
        response = requests.post(READ_URL, headers=headers, cookies=cookies, data=json.dumps(account_data, separators=(',', ':')))
        resData = response.json()
        logging.debug("response: %s", resData)

        if 'succ' in resData:
            if 'synckey' in resData:
                lastTime = thisTime
                read_index += 1
                time.sleep(30)
                refresh_print(f"{prefix}阅读进度: 第 {min(read_index, READ_NUM + 1) - 1}/{READ_NUM} 次，已完成 {(read_index - 1) * 0.5:.1f} 分钟")
            else:
                logging.warning(f"{prefix}无 synckey，尝试修复...")
                fix_no_synckey(headers, cookies)
        else:
            logging.warning(f"{prefix}cookie 已过期，尝试刷新...")
            refresh_cookie(headers, cookies, label)

    logging.info(f"{prefix}阅读脚本已完成。")
    return (read_index - 1) * 0.5


def main():
    accounts = get_accounts()
    total = len(accounts)
    logging.info(f"共检测到 {total} 个账号，顺序执行。")

    for i, (account_headers, account_cookies) in enumerate(accounts, start=1):
        label = format_label(i, total)
        prefix = f"{label} " if label else ""
        try:
            minutes = run_account(account_headers, account_cookies, i, total)
        except Exception as exc:
            logging.error(f"{prefix}运行失败：{exc}")
            if PUSH_METHOD not in (None, ''):
                logging.info(f"{prefix}开始推送失败通知...")
                push(build_failure_report(label, exc), PUSH_METHOD, is_success=False)
            continue

        if PUSH_METHOD not in (None, ''):
            logging.info(f"{prefix}开始推送...")
            push(build_success_report(label, minutes), PUSH_METHOD, is_success=True)
        else:
            logging.info(f"{prefix}未配置推送渠道，跳过推送。")


if __name__ == "__main__":
    main()
