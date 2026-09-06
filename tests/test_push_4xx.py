"""验证 push.py 的 4xx 鉴权快速失败。

设计目标（来自优化任务）：
- pushplus / wxpusher / serverchan 在响应 status_code ∈ [400, 500) 时**立即停止重试**，
  返回 False，不再 sleep。
- 5xx / 网络异常（ConnectionError / Timeout）仍走原有 5 次重试 + 180-360s 退避路径。
- push_telegram 不在本轮改动范围内，不在本测试覆盖。

锚点：
- push.py:push_pushplus L22-40（5 次 attempts，raise_for_status 抛 HTTPError）
- push.py:push_wxpusher L52-71（同上）
- push.py:push_serverChan L73-93（同上）
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

# 让 tests/ 能 import 同级目录的 push.py / config.py
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from push import PushNotification  # noqa: E402


def _make_response(status_code, text="{}"):
    """构造一个 requests.Response 的最小替身：raise_for_status() + status_code。"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if 400 <= status_code < 500:
        import requests
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} Client Error"
        )
    elif 500 <= status_code < 600:
        import requests
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} Server Error"
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class PushPlus4xxTests(unittest.TestCase):
    """pushplus：POST，4xx 必须立即停止重试。"""

    @patch("push.time.sleep")
    @patch("push.requests.post")
    def test_pushplus_401_stops_retrying(self, mock_post, mock_sleep):
        mock_post.return_value = _make_response(401, text='{"code":901,"msg":"token无效"}')
        notifier = PushNotification()
        result = notifier.push_pushplus("hello", "bad-token", is_success=True)
        self.assertFalse(result)
        self.assertEqual(
            mock_post.call_count, 1,
            f"401 时不应重试，期望 1 次调用，实际 {mock_post.call_count}",
        )
        self.assertEqual(
            mock_sleep.call_count, 0,
            f"401 时不应 sleep，期望 0 次，实际 {mock_sleep.call_count}",
        )

    @patch("push.time.sleep")
    @patch("push.requests.post")
    def test_pushplus_500_still_retries_5_times(self, mock_post, mock_sleep):
        mock_post.return_value = _make_response(500, text="server boom")
        notifier = PushNotification()
        result = notifier.push_pushplus("hello", "tok", is_success=True)
        self.assertFalse(result)
        self.assertEqual(
            mock_post.call_count, 5,
            f"500 应保持 5 次尝试，实际 {mock_post.call_count}",
        )
        self.assertEqual(
            mock_sleep.call_count, 4,
            f"500 应在 5 次间 sleep 4 次，实际 {mock_sleep.call_count}",
        )


class WxPusher4xxTests(unittest.TestCase):
    """wxpusher：GET（注意是 requests.get），4xx 必须立即停止。"""

    @patch("push.time.sleep")
    @patch("push.requests.get")
    def test_wxpusher_404_stops_retrying(self, mock_get, mock_sleep):
        mock_get.return_value = _make_response(404, text="not found")
        notifier = PushNotification()
        result = notifier.push_wxpusher("hello", "bad-spt")
        self.assertFalse(result)
        self.assertEqual(
            mock_get.call_count, 1,
            f"404 时不应重试，期望 1 次调用，实际 {mock_get.call_count}",
        )
        self.assertEqual(
            mock_sleep.call_count, 0,
            f"404 时不应 sleep，期望 0 次，实际 {mock_sleep.call_count}",
        )

    @patch("push.time.sleep")
    @patch("push.requests.get")
    def test_wxpusher_502_still_retries_5_times(self, mock_get, mock_sleep):
        mock_get.return_value = _make_response(502, text="bad gateway")
        notifier = PushNotification()
        result = notifier.push_wxpusher("hello", "tok")
        self.assertFalse(result)
        self.assertEqual(
            mock_get.call_count, 5,
            f"502 应保持 5 次尝试，实际 {mock_get.call_count}",
        )
        self.assertEqual(
            mock_sleep.call_count, 4,
            f"502 应在 5 次间 sleep 4 次，实际 {mock_sleep.call_count}",
        )


class ServerChan4xxTests(unittest.TestCase):
    """serverchan：POST，4xx 必须立即停止。"""

    @patch("push.time.sleep")
    @patch("push.requests.post")
    def test_serverchan_403_stops_retrying(self, mock_post, mock_sleep):
        mock_post.return_value = _make_response(403, text="forbidden")
        notifier = PushNotification()
        result = notifier.push_serverChan("hello", "bad-spt", is_success=True)
        self.assertFalse(result)
        self.assertEqual(
            mock_post.call_count, 1,
            f"403 时不应重试，期望 1 次调用，实际 {mock_post.call_count}",
        )
        self.assertEqual(
            mock_sleep.call_count, 0,
            f"403 时不应 sleep，期望 0 次，实际 {mock_sleep.call_count}",
        )

    @patch("push.time.sleep")
    @patch("push.requests.post")
    def test_serverchan_timeout_still_retries_5_times(self, mock_post, mock_sleep):
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("read timed out")
        notifier = PushNotification()
        result = notifier.push_serverChan("hello", "tok", is_success=True)
        self.assertFalse(result)
        self.assertEqual(
            mock_post.call_count, 5,
            f"Timeout 应保持 5 次尝试，实际 {mock_post.call_count}",
        )
        self.assertEqual(
            mock_sleep.call_count, 4,
            f"Timeout 应在 5 次间 sleep 4 次，实际 {mock_sleep.call_count}",
        )


if __name__ == "__main__":
    unittest.main()