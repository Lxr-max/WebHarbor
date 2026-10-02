"""Exact process identities and fail-closed supervisor lifecycle checks."""
from __future__ import annotations

from contextlib import contextmanager
import errno
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load_module(name):
    spec = importlib.util.spec_from_file_location(
        f"supervisor_identity_test_{name}", ROOT / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stat_bytes(pid, start_time, comm="python", state="S"):
    fields = [state, *(str(number) for number in range(4, 53))]
    fields[19] = str(start_time)
    return f"{pid} ({comm}) {' '.join(fields)}\n".encode()


class SupervisorStartTime(unittest.TestCase):
    def setUp(self):
        self.runner = load_module("site_runner")
        self.pid = 424242

    @contextmanager
    def proc_stat(self, data, *, unreadable=False):
        """Redirect the proc directory while using real files and descriptors."""
        with tempfile.TemporaryDirectory() as directory:
            if data is not None:
                (Path(directory) / "stat").write_bytes(data)
            descriptors = []
            real_open = os.open

            def open_proc(path, flags, mode=0o777, *, dir_fd=None):
                if path == f"/proc/{self.pid}":
                    descriptor = real_open(directory, flags, mode)
                else:
                    self.assertEqual(path, "stat")
                    self.assertEqual(dir_fd, descriptors[0])
                    descriptor = real_open(
                        path, os.O_WRONLY if unreadable else flags, mode,
                        dir_fd=dir_fd,
                    )
                descriptors.append(descriptor)
                return descriptor

            try:
                with mock.patch.object(self.runner.os, "open", side_effect=open_proc):
                    yield descriptors
            finally:
                leaked = []
                for descriptor in descriptors:
                    try:
                        os.fstat(descriptor)
                    except OSError as error:
                        self.assertEqual(error.errno, errno.EBADF)
                    else:
                        leaked.append(descriptor)
                        os.close(descriptor)
                self.assertEqual(leaked, [], "proc descriptors must always close")

    def test_reads_exact_start_time_with_spaces_and_parentheses_in_comm(self):
        for comm in ("python", "worker ) x (y)"):
            with self.subTest(comm=comm):
                data = stat_bytes(self.pid, 61266436, comm=comm)
                with self.proc_stat(data) as descriptors:
                    self.assertEqual(self.runner._process_start_time(self.pid), 61266436)
                    self.assertEqual(len(descriptors), 2)

    def test_closes_directory_when_stat_open_fails(self):
        with self.proc_stat(None) as descriptors:
            with self.assertRaises(FileNotFoundError):
                self.runner._process_start_time(self.pid)
            self.assertEqual(len(descriptors), 1)

    def test_closes_both_descriptors_when_read_fails(self):
        with self.proc_stat(stat_bytes(self.pid, 100), unreadable=True) as descriptors:
            with self.assertRaises(OSError) as raised:
                self.runner._process_start_time(self.pid)
            self.assertEqual(raised.exception.errno, errno.EBADF)
            self.assertEqual(len(descriptors), 2)

    def test_closes_both_descriptors_when_stat_is_malformed(self):
        cases = (
            (b"missing command delimiters", ValueError),
            (b"424242 (python) S 1\n", IndexError),
            (stat_bytes(self.pid, "not-a-number"), ValueError),
        )
        for data, error in cases:
            with self.subTest(data=data):
                with self.proc_stat(data) as descriptors:
                    with self.assertRaises(error):
                        self.runner._process_start_time(self.pid)
                    self.assertEqual(len(descriptors), 2)

    def test_disappeared_process_does_not_publish_a_pid_record(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_directory = Path(directory)
            with (
                mock.patch.object(self.runner, "PID_DIR", pid_directory),
                mock.patch.object(self.runner.os, "getpid", return_value=self.pid),
                mock.patch.object(self.runner.os, "getpgid", return_value=self.pid),
                mock.patch.object(
                    self.runner, "_process_start_time",
                    side_effect=ProcessLookupError(errno.ESRCH, "process disappeared"),
                ),
            ):
                with self.assertRaises(ProcessLookupError):
                    self.runner._write_pid_record("fixture", 40000)
            self.assertEqual(list(pid_directory.iterdir()), [])

    @unittest.skipUnless(
        sys.platform.startswith("linux") and Path("/proc/self/stat").is_file(),
        "requires Linux procfs",
    )
    def test_child_self_start_time_exactly_matches_external_proc_observation(self):
        child_code = """
import importlib.util
import os
import sys
spec = importlib.util.spec_from_file_location('identity_runner', sys.argv[1])
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
print(runner._process_start_time(os.getpid()), flush=True)
sys.stdin.readline()
"""
        process = subprocess.Popen(
            [sys.executable, "-c", child_code, str(ROOT / "site_runner.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        try:
            ready, _, _ = select.select([process.stdout], [], [], 10)
            self.assertTrue(ready, "child did not publish its start time")
            own_start_time = process.stdout.readline().strip()
            self.assertTrue(own_start_time, "child exited before publishing its start time")
            external = Path(f"/proc/{process.pid}/stat").read_bytes()
            external_fields = external[external.rindex(b")") + 2:].split()
            self.assertEqual(int(own_start_time), int(external_fields[19]))
        finally:
            try:
                _, stderr = process.communicate("\n", timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                _, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, stderr)


class ControlProcessIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        real_mkdir = Path.mkdir

        def isolated_mkdir(path, *args, **kwargs):
            if path != Path("/tmp/websyn_pids"):
                return real_mkdir(path, *args, **kwargs)

        with (
            mock.patch.dict(os.environ, {"WEBSYN_CONTROL_TOKEN": "identity-test-token-" + "x" * 32}),
            mock.patch.object(Path, "mkdir", isolated_mkdir),
        ):
            self.control = load_module("control_server")
        self.control.PID_DIR = Path(self.tmp.name)
        self.site = self.control.SITES[0]
        self.record = {
            "pid": 424242, "start_time": 61266436,
            "site": self.site, "port": self.control.site_port(self.site),
        }
        self.control.pid_path(self.site).write_text(json.dumps(self.record))
        self.arguments = [
            b"python3", b"/opt/site_runner.py", self.site.encode(),
            str(self.record["port"]).encode(),
        ]

    @contextmanager
    def kernel_identity(self, *, start_time=None, pgid=None, arguments=None):
        pid = self.record["pid"]
        if start_time is None:
            start_time = self.record["start_time"]
        if pgid is None:
            pgid = pid
        if arguments is None:
            arguments = self.arguments
        observations = {
            Path(f"/proc/{pid}/stat"): stat_bytes(pid, start_time),
            Path(f"/proc/{pid}/cmdline"): b"\0".join(arguments) + b"\0",
        }

        def read_proc(path):
            return observations[path]

        with (
            mock.patch.object(Path, "read_bytes", read_proc),
            mock.patch.object(self.control.os, "getpgid", return_value=pgid),
            mock.patch.object(self.control.os, "killpg") as killpg,
            mock.patch.object(self.control, "reap_exited_children"),
        ):
            yield killpg

    def assert_refused_without_signaling(self, killpg):
        self.assertFalse(self.control.process_matches_site(self.site, self.record))
        with self.assertRaisesRegex(RuntimeError, "PID identity mismatch"):
            self.control.kill_site(self.site, reap_grace=0)
        killpg.assert_not_called()
        self.assertEqual(self.control.read_pid_record(self.site), self.record)

    def test_accepts_exact_identity_with_native_and_qemu_command_lines(self):
        for prefix in ([], [b"/usr/bin/qemu-x86_64", b"/usr/local/bin/python3"]):
            with self.subTest(prefix=prefix):
                with self.kernel_identity(arguments=prefix + self.arguments):
                    self.assertTrue(self.control.process_matches_site(self.site, self.record))

    def test_refuses_exactly_one_tick_mismatch_without_signaling(self):
        for offset in (-1, 1):
            with self.subTest(offset=offset):
                with self.kernel_identity(start_time=self.record["start_time"] + offset) as killpg:
                    self.assert_refused_without_signaling(killpg)

    def test_refuses_wrong_process_group_without_signaling(self):
        with self.kernel_identity(pgid=self.record["pid"] + 1) as killpg:
            self.assert_refused_without_signaling(killpg)

    def test_refuses_wrong_runner_site_or_port_without_signaling(self):
        for index, replacement in ((1, b"/opt/other.py"), (2, b"other"), (3, b"1")):
            with self.subTest(index=index):
                arguments = self.arguments.copy()
                arguments[index] = replacement
                with self.kernel_identity(arguments=arguments) as killpg:
                    self.assert_refused_without_signaling(killpg)


if __name__ == "__main__":
    unittest.main()
