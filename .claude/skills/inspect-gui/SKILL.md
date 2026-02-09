---
name: inspect-gui
description: Generate pywinauto code to inspect a Windows application's GUI control tree. Use when exploring app structure or finding control selectors.
argument-hint: "[app-name-or-window-title]"
---

# Inspect GUI Controls

Generate and run pywinauto inspection code for a Windows application.

## Generate Inspection Script

Create a script that dumps the GUI tree of `$ARGUMENTS`:

```python
"""Inspect GUI controls for: $ARGUMENTS"""
from pywinauto import Application, Desktop

def inspect_app(title: str):
    """Connect to app and dump control tree."""
    # Try UIA backend first (richer control info)
    try:
        app = Application(backend='uia').connect(title_re=f'.*{title}.*', timeout=5)
        window = app.window(title_re=f'.*{title}.*')

        print(f"=== Window: {window.window_text()} ===")
        print(f"Backend: UIA")
        print(f"Class: {window.class_name()}")
        print(f"Handle: {window.handle}")
        print(f"Rectangle: {window.rectangle()}")
        print()

        print("--- Control Tree ---")
        window.print_control_identifiers(depth=4)

        print("\n--- Actionable Controls ---")
        for ctrl in window.descendants():
            ctrl_type = ctrl.element_info.control_type
            if ctrl_type in ('Button', 'Edit', 'MenuItem', 'ComboBox', 'CheckBox', 'RadioButton', 'Hyperlink', 'TabItem'):
                name = ctrl.window_text()
                auto_id = getattr(ctrl.element_info, 'automation_id', '')
                enabled = ctrl.is_enabled()
                print(f"  [{ctrl_type}] '{name}' auto_id='{auto_id}' enabled={enabled}")

    except Exception as e:
        print(f"UIA failed: {e}")
        print("Trying Win32 backend...")
        try:
            app = Application(backend='win32').connect(title_re=f'.*{title}.*', timeout=5)
            window = app.window(title_re=f'.*{title}.*')
            print(f"=== Window: {window.window_text()} (Win32) ===")
            window.print_control_identifiers(depth=4)
        except Exception as e2:
            print(f"Win32 also failed: {e2}")

def list_windows():
    """List all visible top-level windows."""
    print("=== All Visible Windows ===")
    desktop = Desktop(backend='uia')
    for win in desktop.windows():
        if win.is_visible():
            print(f"  '{win.window_text()}' class='{win.class_name()}'")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "$ARGUMENTS"
    if target == "--list":
        list_windows()
    else:
        inspect_app(target)
```

## Usage Notes

- This generates a script. On macOS, pywinauto won't run — save the script and run it on Windows
- Use `--list` to see all open windows first
- Increase `depth` parameter for deeply nested controls
- Look for `automation_id` — it's the most reliable selector for UIA controls
