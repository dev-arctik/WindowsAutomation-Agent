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
# Helper functions
# ---------------------------------------------------------------------------


def start_application(
    executable: str,
    backend: str = "uia",
) -> tuple[Any | None, str]:
    """Start an application by executable path.

    Args:
        executable: Path or name of the executable to start.
        backend: pywinauto backend ('uia' or 'win32').

    Returns:
        Tuple of (Application instance or None, status message).
    """
    try:
        app = Application(backend=backend)
        app.start(executable, timeout=10)
        return app, f"Started '{executable}' successfully"
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
                result.append({
                    "title": w.window_text(),
                    "process_id": getattr(w, "process_id", None),
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
    try:
        control.wait("enabled", timeout=timeout)
        control.type_keys(text, with_spaces=True)
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
