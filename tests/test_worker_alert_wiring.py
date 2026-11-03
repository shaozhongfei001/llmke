"""worker 的告警装配：群机器人通道优先、secret 只从环境变量读、缺配置 fail-fast。

不测远端网关（没有账号），只测"装配对不对、密钥有没有泄露到命令行"。
"""

import importlib.util
import json
import os
from types import SimpleNamespace

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "worker_mod", os.path.join(REPO, "scripts", "v2_graph_worker.py"))
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


def args(**over):
    base = dict(alert_channel=None, alert_url=None, alert_webhook=None,
                alert_secret_env="LLMKE_ALERT_SECRET")
    base.update(over)
    return SimpleNamespace(**base)


def test_no_config_means_no_sink():
    assert worker.build_alert_sink(args()) is None


def test_wecom_channel_is_built():
    sink = worker.build_alert_sink(args(alert_channel="wecom",
                                        alert_url="http://127.0.0.1:1/x?key=k"))
    assert callable(sink)


def test_dingtalk_requires_secret_from_env(monkeypatch):
    monkeypatch.delenv("LLMKE_ALERT_SECRET", raising=False)
    with pytest.raises(SystemExit) as exc:
        worker.build_alert_sink(args(alert_channel="dingtalk",
                                     alert_url="http://127.0.0.1:1/x?access_token=t"))
    assert "LLMKE_ALERT_SECRET" in str(exc.value)


def test_dingtalk_reads_secret_by_env_name(monkeypatch):
    monkeypatch.setenv("MY_DING_SECRET", "SECtest")
    sink = worker.build_alert_sink(args(alert_channel="dingtalk",
                                        alert_url="http://127.0.0.1:1/x",
                                        alert_secret_env="MY_DING_SECRET"))
    assert callable(sink)
    # 密钥不能挂在对象的可读属性上（否则日志/repr 会带出来）
    assert "SECtest" not in repr(sink)


def test_channel_without_url_fails_fast():
    with pytest.raises(SystemExit):
        worker.build_alert_sink(args(alert_channel="wecom"))


def test_legacy_webhook_still_works():
    sink = worker.build_alert_sink(args(alert_webhook="http://127.0.0.1:1/hook"))
    assert callable(sink)


def test_channel_preferred_over_legacy_webhook():
    """两个都给时用通道：否则会同时往两个地方发，排查时说不清哪条到的。"""
    sink = worker.build_alert_sink(args(alert_channel="wecom",
                                        alert_url="http://127.0.0.1:1/x",
                                        alert_webhook="http://127.0.0.1:1/hook"))
    assert type(sink).__name__ == "WecomChannel"
