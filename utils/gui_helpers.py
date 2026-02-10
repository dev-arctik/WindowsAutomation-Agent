"""
pywinauto abstraction layer with cross-platform mock support.

On Windows: imports real pywinauto Application, Desktop.
On macOS/Linux: provides mock classes that replicate the pywinauto API
surface so graph/tool code can be developed and tested on any OS.

All helper functions return tuple[object | None, str] where the first
element is the result (or None on failure) and the second is a status message.
"""

import io
import platform
from typing import Any

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    from pywinauto import Desktop
    from pywinauto.application import Application
else:
    # --- Mock classes for non-Windows development ---

    class _MockControl:
        """Mimics a pywinauto control wrapper."""

        def __init__(self, title: str = "MockControl", control_type: str = "Button"):
            self._title = title
            self._control_type = control_type
            self._enabled = True
            self._visible = True

        def wait(self, state: str, timeout: int = 10) -> "_MockControl":
            print(f"[MOCK] Control '{self._title}' wait('{state}', timeout={timeout})")
            return self

        def click_input(self) -> None:
            print(f"[MOCK] Clicked '{self._title}'")

        def type_keys(self, text: str, with_spaces: bool = False) -> None:
            print(f"[MOCK] Typed '{text}' into '{self._title}' (with_spaces={with_spaces})")

        def set_text(self, text: str) -> None:
            print(f"[MOCK] Set text '{text}' on '{self._title}'")

        def select(self, item: str) -> None:
            print(f"[MOCK] Selected '{item}' in '{self._title}'")

        def window_text(self) -> str:
            return self._title

        def friendly_class_name(self) -> str:
            return self._control_type

        def element_info(self) -> Any:
            return _MockElementInfo(self._title, self._control_type)

        def is_enabled(self) -> bool:
            return self._enabled

        def is_visible(self) -> bool:
            return self._visible

        def texts(self) -> list[str]:
            return [self._title]

        def rectangle(self) -> Any:
            return _MockRect()

        def children(self, **kwargs: Any) -> list["_MockControl"]:
            return [
                _MockControl("OK", "Button"),
                _MockControl("Cancel", "Button"),
                _MockControl("TextInput", "Edit"),
            ]

        def print_control_identifiers(self, depth: int = 3) -> None:
            print(f"[MOCK] Control tree (depth={depth}):")
            print(f"  {self._control_type} - '{self._title}'")
            print(f"    Button - 'OK'")
            print(f"    Button - 'Cancel'")
            print(f"    Edit - 'TextInput'")

        def child_window(self, **kwargs: Any) -> "_MockControl":
            title = kwargs.get("title", kwargs.get("auto_id", "ChildControl"))
            control_type = kwargs.get("control_type", "Button")
            print(f"[MOCK] child_window({kwargs})")
            return _MockControl(str(title), str(control_type))

        def capture_as_image(self) -> Any:
            print("[MOCK] Captured screenshot (returning mock image)")
            try:
                from PIL import Image
                return Image.new("RGB", (800, 600), color=(200, 200, 200))
            except ImportError:
                return None

        def menu_select(self, path: str) -> None:
            print(f"[MOCK] Menu select: '{path}'")

    class _MockElementInfo:
        """Mimics pywinauto element_info."""

        def __init__(self, name: str = "", control_type: str = ""):
            self.name = name
            self.control_type = control_type
            self.automation_id = f"auto_{name}"
            self.class_name = control_type

    class _MockRect:
        """Mimics pywinauto RECT."""

        left = 0
        top = 0
        right = 800
        bottom = 600

        def __repr__(self) -> str:
            return f"(L0, T0, R800, B600)"

    class _MockWindow(_MockControl):
        """Mimics a pywinauto window wrapper."""

        def __init__(self, title: str = "MockWindow", process_id: int = 1234):
            super().__init__(title, "Window")
            self._process_id = process_id

        def is_dialog(self) -> bool:
            return False

        @property
        def process_id(self) -> int:
            return self._process_id

        def close(self) -> None:
            print(f"[MOCK] Closed window '{self._title}'")

    class _MockApp:
        """Mimics pywinauto Application."""

        def __init__(self, backend: str = "uia"):
            self._backend = backend
            self._process = 1234

        def start(self, cmd: str, timeout: int = 10) -> "_MockApp":
            print(f"[MOCK] Started application: '{cmd}' (backend={self._backend})")
            return self

        def connect(self, **kwargs: Any) -> "_MockApp":
            print(f"[MOCK] Connected to application: {kwargs}")
            return self

        def window(self, **kwargs: Any) -> _MockWindow:
            title = kwargs.get("title", kwargs.get("title_re", "MockWindow"))
            return _MockWindow(str(title))

        @property
        def process(self) -> int:
            return self._process

    class _MockDesktop:
        """Mimics pywinauto Desktop."""

        def __init__(self, backend: str = "uia"):
            self._backend = backend

        def windows(self) -> list[_MockWindow]:
            return [
                _MockWindow("Notepad", 1001),
                _MockWindow("Calculator", 1002),
                _MockWindow("File Explorer", 1003),
            ]

    # Alias so import paths match real pywinauto
    Application = _MockApp  # type: ignore[misc, assignment]
    Desktop = _MockDesktop  # type: ignore[misc, assignment]


# ---------------------------------------------------------------------------
# App name → executable mapping for common Windows apps
# ---------------------------------------------------------------------------

APP_EXECUTABLES: dict[str, tuple[str, str]] = {
    # name → (executable_path, window_title_keyword)
    "chrome": (r"C:\Program Files\Google\Chrome\Application\chrome.exe", "chrome"),
    "google chrome": (r"C:\Program Files\Google\Chrome\Application\chrome.exe", "chrome"),
    "firefox": (r"C:\Program Files\Mozilla Firefox\firefox.exe", "firefox"),
    "brave": (r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe", "brave"),
    "edge": (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "edge"),
    "microsoft edge": (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "edge"),
    "notepad": ("notepad", "notepad"),
    "calculator": ("calc", "calculator"),
    "calc": ("calc", "calculator"),
    "explorer": ("explorer", "explorer"),
    "file explorer": ("explorer", "explorer"),
    "cmd": ("cmd", "command prompt"),
    "powershell": ("powershell", "powershell"),
    "terminal": ("wt", "powershell"),
    "windows terminal": ("wt", "powershell"),
    "snippingtool": ("SnippingTool", "snipping"),
    "snipping tool": ("SnippingTool", "snipping"),
    "stickynotes": ("explorer shell:AppsFolder\\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe!App", "sticky"),
    "sticky notes": ("explorer shell:AppsFolder\\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe!App", "sticky"),
}


def _resolve_executable(name: str) -> tuple[str, str]:
    """Resolve a friendly app name to (executable_path, window_title_keyword).

    Returns the original name as both if no mapping exists.
    """
    key = name.lower().replace(".exe", "").strip()
    if key in APP_EXECUTABLES:
        return APP_EXECUTABLES[key]
    return (name, key)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _get_pid(window: Any) -> int | None:
    """Safely extract process ID from a pywinauto window wrapper."""
    pid = getattr(window, "process_id", None)
    if callable(pid):
        pid = pid()
    return pid


def start_application(
    executable: str,
    backend: str = "uia",
) -> tuple[Any | None, str]:
    """Start an application and connect to its new window.

    Windows 11 modern apps (like Notepad) use a launcher process,
    so app.start() may capture the wrong PID. We start the process
    externally, detect the new window, and connect to it.

    Handles Win11 Notepad tab restoration by detecting existing windows
    before launch and connecting to genuinely new processes.

    Args:
        executable: Path or name of the executable to start.
        backend: pywinauto backend ('uia' or 'win32').

    Returns:
        Tuple of (Application instance or None, status message).
    """
    import subprocess
    import time

    exe_path, title_keyword = _resolve_executable(executable)
    app_base = title_keyword

    try:
        # Record ALL existing window handles and PIDs BEFORE starting
        desktop_before = Desktop(backend=backend)
        existing_handles = set()
        existing_pids = set()
        for w in desktop_before.windows():
            try:
                existing_handles.add(w.handle)
                if app_base in w.window_text().lower():
                    pid = _get_pid(w)
                    if pid:
                        existing_pids.add(pid)
            except Exception:
                continue

        # Start the process
        subprocess.Popen(exe_path)

        # Wait with polling — check every 0.5s for up to 8s
        new_app = None
        for _ in range(16):
            time.sleep(0.5)
            desktop_after = Desktop(backend=backend)
            for w in desktop_after.windows():
                try:
                    if app_base in w.window_text().lower():
                        pid = _get_pid(w)
                        handle = w.handle
                        # Prefer windows that are genuinely NEW (new handle)
                        if handle not in existing_handles and pid:
                            app = Application(backend=backend)
                            app.connect(process=pid, timeout=15)
                            return app, f"Started '{executable}' successfully"
                        # Also accept new PID even if handle existed (Win11 reuse)
                        if pid and pid not in existing_pids:
                            app = Application(backend=backend)
                            app.connect(process=pid, timeout=15)
                            return app, f"Started '{executable}' successfully"
                except Exception:
                    continue

        # Fallback: if no NEW window found (Win11 apps reuse process),
        # connect to the first matching window we can find
        desktop_final = Desktop(backend=backend)
        for w in desktop_final.windows():
            try:
                title = w.window_text()
                if app_base in title.lower():
                    pid = _get_pid(w)
                    if pid:
                        app = Application(backend=backend)
                        app.connect(process=pid, timeout=15)
                        return app, f"Started '{executable}' (reused existing process)"
            except Exception:
                continue

        return None, f"Started '{executable}' but could not find its window"
    except Exception as e:
        return None, f"Failed to start '{executable}': {e}"


def connect_to_application(
    title: str | None = None,
    title_re: str | None = None,
    process: int | None = None,
    backend: str = "uia",
    timeout: int = 10,
) -> tuple[Any | None, str]:
    """Connect to a running application.

    Args:
        title: Exact window title to match.
        title_re: Regex pattern for window title.
        process: Process ID to connect to.
        backend: pywinauto backend ('uia' or 'win32').
        timeout: Connection timeout in seconds.

    Returns:
        Tuple of (Application instance or None, status message).
    """
    try:
        app = Application(backend=backend)
        connect_kwargs: dict[str, Any] = {}
        if title:
            connect_kwargs["title"] = title
        if title_re:
            connect_kwargs["title_re"] = title_re
        if process:
            connect_kwargs["process"] = process
        if timeout:
            connect_kwargs["timeout"] = timeout
        app.connect(**connect_kwargs)
        return app, f"Connected to application successfully"
    except Exception as e:
        return None, f"Failed to connect: {e}"


def get_window(
    app: Any,
    title: str | None = None,
    title_re: str | None = None,
    timeout: int = 10,
) -> tuple[Any | None, str]:
    """Get a window from an application and wait for it to be ready.

    Args:
        app: pywinauto Application instance.
        title: Exact window title.
        title_re: Regex pattern for title.
        timeout: Wait timeout in seconds.

    Returns:
        Tuple of (window wrapper or None, status message).
    """
    try:
        kwargs: dict[str, Any] = {}
        if title:
            kwargs["title"] = title
        if title_re:
            kwargs["title_re"] = title_re
        window = app.window(**kwargs)
        window.wait("ready", timeout=timeout)
        return window, f"Found window: '{window.window_text()}'"
    except Exception as e:
        return None, f"Failed to get window: {e}"


def find_control(
    window: Any,
    control_type: str | None = None,
    title: str | None = None,
    auto_id: str | None = None,
    timeout: int = 10,
) -> tuple[Any | None, str]:
    """Find a specific control within a window.

    Args:
        window: pywinauto window wrapper.
        control_type: Type of control (Button, Edit, MenuItem, etc.).
        title: Control title text.
        auto_id: Automation ID of the control.
        timeout: Wait timeout in seconds.

    Returns:
        Tuple of (control wrapper or None, status message).
    """
    try:
        kwargs: dict[str, Any] = {}
        if control_type:
            kwargs["control_type"] = control_type
        if title:
            kwargs["title"] = title
        if auto_id:
            kwargs["auto_id"] = auto_id
        control = window.child_window(**kwargs)
        control.wait("visible", timeout=timeout)
        return control, f"Found control: {kwargs}"
    except Exception as e:
        return None, f"Failed to find control {kwargs}: {e}"


def list_all_windows(backend: str = "uia") -> list[dict[str, Any]]:
    """List all visible top-level windows.

    Args:
        backend: pywinauto backend ('uia' or 'win32').

    Returns:
        List of dicts with window info (title, process_id, rectangle).
    """
    try:
        desktop = Desktop(backend=backend)
        windows = desktop.windows()
        result = []
        for w in windows:
            try:
                pid = getattr(w, "process_id", None)
                if callable(pid):
                    pid = pid()
                result.append({
                    "title": w.window_text(),
                    "process_id": pid,
                    "rectangle": str(w.rectangle()),
                    "class_name": w.friendly_class_name(),
                })
            except Exception:
                continue
        return result
    except Exception:
        return []


def safe_click(control: Any, timeout: int = 10) -> str:
    """Wait for a control to be enabled, then click it.

    Args:
        control: pywinauto control wrapper.
        timeout: Wait timeout in seconds.

    Returns:
        Status message.
    """
    try:
        control.wait("enabled", timeout=timeout)
        if hasattr(control, "set_focus"):
            control.set_focus()
        control.click_input()
        return f"Clicked '{control.window_text()}'"
    except Exception as e:
        return f"Click failed: {e}"


def safe_type(control: Any, text: str, timeout: int = 10) -> str:
    """Wait for a control to be enabled, then type text into it.

    Args:
        control: pywinauto control wrapper.
        text: Text to type (supports pywinauto key syntax).
        timeout: Wait timeout in seconds.

    Returns:
        Status message.
    """
    import time as _time

    try:
        control.wait("enabled", timeout=timeout)
        if hasattr(control, "set_focus"):
            control.set_focus()
        # Small pause before typing to let focus settle
        _time.sleep(0.3)
        control.type_keys(text, with_spaces=True, pause=0.05)
        return f"Typed text into '{control.window_text()}'"
    except Exception as e:
        return f"Type failed: {e}"


def capture_control_tree(window: Any, depth: int = 3) -> str:
    """Capture the control tree output as a string.

    Args:
        window: pywinauto window wrapper.
        depth: How deep to inspect the control tree.

    Returns:
        String representation of the control tree.
    """
    buffer = io.StringIO()
    try:
        import sys
        old_stdout = sys.stdout
        sys.stdout = buffer
        window.print_control_identifiers(depth=depth)
        sys.stdout = old_stdout
    except Exception as e:
        return f"Failed to capture control tree: {e}"
    return buffer.getvalue()
