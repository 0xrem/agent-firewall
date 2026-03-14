import io
import subprocess
import unittest
from unittest.mock import patch

from agentfirewall.integrations.langgraph import LangGraphGuardedToolBuilder
from agentfirewall.runtime_context import tool_runtime_context


def passthrough_tool_decorator(*, name: str, description: str):
    def decorator(func):
        func.__tool_name__ = name
        func.__tool_description__ = description
        return func

    return decorator


class RecordingFirewall:
    def __init__(self) -> None:
        self.events = []

    def enforce(self, event) -> None:
        self.events.append(event)


class RecordingHandle:
    def __init__(self) -> None:
        self.writes: list[str] = []
        self.closed = False

    def write(self, content: str) -> None:
        self.writes.append(content)

    def close(self) -> None:
        self.closed = True


class LangGraphGuardedToolBuilderTests(unittest.TestCase):
    def test_create_shell_tool_uses_command_surface_source(self) -> None:
        instances = []

        class FakeGuardedRunner:
            def __init__(self, *, firewall, source, runner=None) -> None:
                self.firewall = firewall
                self.source = source
                self.runner = runner
                self.calls = []
                instances.append(self)

            def run(self, command, *, shell=False, **kwargs):
                self.calls.append((command, shell, dict(kwargs)))
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="repo files\n",
                )

        with patch(
            "agentfirewall.integrations.langgraph._langgraph_tool_decorator",
            side_effect=passthrough_tool_decorator,
        ), patch(
            "agentfirewall.integrations.langgraph.GuardedSubprocessRunner",
            FakeGuardedRunner,
        ):
            firewall = RecordingFirewall()
            builder = LangGraphGuardedToolBuilder(firewall=firewall)
            shell_tool = builder.create_shell_tool(
                name="repo_shell",
                description="Run repo shell commands.",
                source="adapter.shell",
                runner=lambda *args, **kwargs: None,
                run_kwargs={"timeout": 5},
            )

            result = shell_tool("ls", cwd="/tmp/repo")

        self.assertEqual(result, "repo files")
        self.assertEqual(shell_tool.__tool_name__, "repo_shell")
        self.assertEqual(shell_tool.__tool_description__, "Run repo shell commands.")
        self.assertEqual(len(instances), 1)
        self.assertIs(instances[0].firewall, firewall)
        self.assertEqual(instances[0].source, "adapter.shell.command")
        self.assertEqual(
            instances[0].calls,
            [
                (
                    "ls",
                    True,
                    {
                        "capture_output": True,
                        "text": True,
                        "check": False,
                        "timeout": 5,
                        "cwd": "/tmp/repo",
                    },
                )
            ],
        )

    def test_create_http_tool_uses_request_surface_source(self) -> None:
        instances = []

        class FakeGuardedHttpClient:
            def __init__(self, *, firewall, source, opener=None) -> None:
                self.firewall = firewall
                self.source = source
                self.opener = opener
                self.calls = []
                instances.append(self)

            def request(self, url: str, *, method: str = "GET", **kwargs):
                self.calls.append((url, method, dict(kwargs)))
                return io.BytesIO(b"trusted-response")

        with patch(
            "agentfirewall.integrations.langgraph._langgraph_tool_decorator",
            side_effect=passthrough_tool_decorator,
        ), patch(
            "agentfirewall.integrations.langgraph.GuardedHttpClient",
            FakeGuardedHttpClient,
        ):
            firewall = RecordingFirewall()
            builder = LangGraphGuardedToolBuilder(firewall=firewall)
            http_tool = builder.create_http_tool(
                name="egress",
                description="Send approved HTTP requests.",
                source="adapter.http",
                opener=lambda *args, **kwargs: None,
                request_kwargs={"timeout": 3},
            )

            result = http_tool("https://example.com/api", method="POST")

        self.assertEqual(result, "trusted-response")
        self.assertEqual(http_tool.__tool_name__, "egress")
        self.assertEqual(instances[0].source, "adapter.http.request")
        self.assertEqual(
            instances[0].calls,
            [
                (
                    "https://example.com/api",
                    "POST",
                    {"timeout": 3},
                )
            ],
        )

    def test_create_file_reader_tool_uses_file_surface_source(self) -> None:
        instances = []

        class FakeGuardedFileAccess:
            def __init__(self, *, firewall, source, opener=None) -> None:
                self.firewall = firewall
                self.source = source
                self.opener = opener
                self.calls = []
                instances.append(self)

            def open(self, path: str, mode: str = "r", **kwargs):
                self.calls.append((path, mode, dict(kwargs)))
                return io.StringIO("README CONTENT")

        with patch(
            "agentfirewall.integrations.langgraph._langgraph_tool_decorator",
            side_effect=passthrough_tool_decorator,
        ), patch(
            "agentfirewall.integrations.langgraph.GuardedFileAccess",
            FakeGuardedFileAccess,
        ):
            firewall = RecordingFirewall()
            builder = LangGraphGuardedToolBuilder(firewall=firewall)
            read_tool = builder.create_file_reader_tool(
                source="adapter.file",
                read_kwargs={"newline": ""},
            )

            result = read_tool("README.md")

        self.assertEqual(result, "README CONTENT")
        self.assertEqual(instances[0].source, "adapter.file.file")
        self.assertEqual(
            instances[0].calls,
            [("README.md", "r", {"newline": "", "encoding": "utf-8"})],
        )

    def test_create_file_writer_tool_uses_file_surface_source_for_default_writes(self) -> None:
        instances = []
        handle = RecordingHandle()

        class FakeGuardedFileAccess:
            def __init__(self, *, firewall, source, opener=None) -> None:
                self.firewall = firewall
                self.source = source
                self.opener = opener
                self.calls = []
                instances.append(self)

            def open(self, path: str, mode: str = "r", **kwargs):
                self.calls.append((path, mode, dict(kwargs)))
                return handle

        with patch(
            "agentfirewall.integrations.langgraph._langgraph_tool_decorator",
            side_effect=passthrough_tool_decorator,
        ), patch(
            "agentfirewall.integrations.langgraph.GuardedFileAccess",
            FakeGuardedFileAccess,
        ):
            firewall = RecordingFirewall()
            builder = LangGraphGuardedToolBuilder(firewall=firewall)
            write_tool = builder.create_file_writer_tool(
                source="adapter.file",
                write_kwargs={"newline": ""},
            )

            result = write_tool("notes.txt", "hello")

        self.assertEqual(result, "wrote 5 chars to notes.txt")
        self.assertEqual(instances[0].source, "adapter.file.file")
        self.assertEqual(
            instances[0].calls,
            [("notes.txt", "w", {"newline": "", "encoding": "utf-8"})],
        )
        self.assertEqual(handle.writes, ["hello"])
        self.assertTrue(handle.closed)

    def test_create_file_writer_tool_enforces_file_access_for_custom_writer(self) -> None:
        calls = []

        with patch(
            "agentfirewall.integrations.langgraph._langgraph_tool_decorator",
            side_effect=passthrough_tool_decorator,
        ):
            firewall = RecordingFirewall()
            builder = LangGraphGuardedToolBuilder(firewall=firewall)
            write_tool = builder.create_file_writer_tool(
                source="adapter.file",
                writer=lambda path, content, **kwargs: calls.append(
                    (path, content, dict(kwargs))
                ),
                write_kwargs={"newline": ""},
            )

            with tool_runtime_context(
                runtime="langgraph",
                tool_name="write_file",
                tool_call_id="call_write_custom",
                tool_event_source="langgraph.tool",
            ):
                result = write_tool("notes.txt", "hello")

        self.assertEqual(result, "wrote 5 chars to notes.txt")
        self.assertEqual(calls, [("notes.txt", "hello", {"newline": ""})])
        self.assertEqual(len(firewall.events), 1)
        event = firewall.events[0]
        self.assertEqual(event.kind.value, "file_access")
        self.assertEqual(event.operation, "write")
        self.assertEqual(event.source, "adapter.file.file")
        self.assertEqual(event.payload["path"], "notes.txt")
        self.assertEqual(
            event.payload["runtime_context"],
            {
                "runtime": "langgraph",
                "tool_name": "write_file",
                "tool_call_id": "call_write_custom",
                "tool_event_source": "langgraph.tool",
            },
        )
