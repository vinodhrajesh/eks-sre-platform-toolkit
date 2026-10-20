import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from detectors import FaultKind, classify_fault  # noqa: E402


def test_oom_killing_classified_high_severity():
    event = {
        "reason": "OOMKilling",
        "metadata": {"namespace": "platform"},
        "involvedObject": {"name": "api-7d9c4-xk2p9"},
        "source": {"host": "ip-10-0-1-23.ec2.internal"},
    }

    fault = classify_fault(event)

    assert fault is not None
    assert fault.kind == FaultKind.OOM_KILLED
    assert fault.severity == "high"
    assert fault.namespace == "platform"
    assert fault.object_name == "api-7d9c4-xk2p9"


def test_backoff_classified_medium_severity():
    event = {
        "reason": "BackOff",
        "metadata": {"namespace": "platform"},
        "involvedObject": {"name": "worker-6f8b1-abc12"},
        "source": {},
    }

    fault = classify_fault(event)

    assert fault is not None
    assert fault.kind == FaultKind.CRASH_LOOP
    assert fault.severity == "medium"


def test_unrelated_reason_is_ignored():
    event = {"reason": "Scheduled", "metadata": {}, "involvedObject": {}, "source": {}}

    assert classify_fault(event) is None
