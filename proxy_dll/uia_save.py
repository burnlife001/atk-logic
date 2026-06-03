"""
UIA companion: detect the native #32770 save dialog and click Save.
Polling-based. Call immediately after Ctrl+S is sent.
Usage: python uia_save.py <filename>
"""
import sys
import time
import traceback
import uiautomation as auto

LOG_PATH = "D:/uia_save_debug.log"


def log(msg):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except:
        pass


def _find_children(ctrl, cls_filter=None, name_contains=None, ctrl_type=None, max_depth=4):
    """Recursively search for controls matching criteria. Returns list."""
    results = []
    if max_depth <= 0:
        return results
    try:
        for c in ctrl.GetChildren():
            try:
                cls = c.ClassName if hasattr(c, 'ClassName') else ''
                name = c.Name if hasattr(c, 'Name') else ''
                ctype = c.ControlTypeName if hasattr(c, 'ControlTypeName') else ''
                if (cls_filter is None or cls_filter in cls) and \
                   (name_contains is None or any(nc in name for nc in name_contains)) and \
                   (ctrl_type is None or ctrl_type in ctype):
                    results.append(c)
            except:
                pass
            results.extend(_find_children(c, cls_filter, name_contains, ctrl_type, max_depth - 1))
    except:
        pass
    return results


def find_save_dialog(timeout=15.0):
    """Find #32770 dialog that has a Save button. Returns (dialog, save_btn) or (None, None)."""
    log("find_save_dialog: starting search")
    start = time.time()
    while time.time() - start < timeout:
        root = auto.GetRootControl()
        dialogs = _find_children(root, cls_filter='#32770', max_depth=5)
        log(f"  found {len(dialogs)} #32770 dialogs")
        for dlg in dialogs:
            try:
                dlg_name = dlg.Name if hasattr(dlg, 'Name') else ''
                if '\u786e\u8ba4' in dlg_name or '\u66ff\u6362' in dlg_name:
                    continue
                btns = _find_children(dlg, name_contains=['\u4fdd\u5b58', 'Save'],
                                      ctrl_type='ButtonControl', max_depth=3)
                if btns:
                    log(f"  found save dialog: {dlg_name[:60]}")
                    return dlg, btns[0]
            except Exception as ex:
                log(f"  error checking dialog: {ex}")
        time.sleep(0.5)

    log("find_save_dialog: NOT FOUND")
    return None, None


def paste_and_save(dialog, save_btn, filename):
    """Fill filename ComboBox and click Save."""
    try:
        dialog.SetFocus()
        time.sleep(0.3)

        # Dump all children to log for debugging
        children = _find_children(dialog, max_depth=5)
        log(f"paste_and_save: {len(children)} total children up to depth 5")
        combo_found = False
        for e in children:
            try:
                ctype = e.ControlTypeName if hasattr(e, 'ControlTypeName') else ''
                cname = e.Name if hasattr(e, 'Name') else ''
                log(f"  child: [{ctype}] '{cname[:40]}'")
                if ctype in ('ComboBoxControl', 'EditControl'):
                    # Found the filename field
                    log(f"  -> found {ctype}: {cname}")
                    combo_found = True
                    e.Click()
                    time.sleep(0.3)
                    # Try ValuePattern first
                    try:
                        vp = e.GetValuePattern()
                        vp.SetValue(filename)
                        log(f"  ValuePattern.SetValue OK: {filename}")
                    except:
                        log(f"  ValuePattern failed, using SendKeys")
                        e.SendKeys('{Ctrl}A{Delete}')
                        time.sleep(0.1)
                        e.SendKeys(filename)
                        time.sleep(0.3)
                    log(f"  ComboBox filled")
                    break
            except Exception as ex:
                log(f"  error on child: {ex}")

        if not combo_found:
            log(f"  WARNING: no ComboBox/Edit found, clicking Save anyway")
            # Try to paste via clipboard as fallback
            try:
                import subprocess
                subprocess.run(['clip'], input=filename.encode(), check=False)
                time.sleep(0.2)
                dialog.SendKeys('{Ctrl}V')
                time.sleep(0.3)
            except:
                pass

        # Click Save
        log(f"  clicking Save: {save_btn.Name}")
        save_btn.Click()
        time.sleep(1.5)

        # Handle overwrite confirm
        root = auto.GetRootControl()
        confirms = _find_children(root, cls_filter='#32770', max_depth=5)
        log(f"  checking {len(confirms)} dialogs for confirm")
        for dlg in confirms:
            try:
                dlg_name = dlg.Name if hasattr(dlg, 'Name') else ''
                if '\u786e\u8ba4' in dlg_name or '\u66ff\u6362' in dlg_name:
                    yes_btns = _find_children(dlg, name_contains=['\u662f', '\u66ff\u6362', 'Yes'],
                                              ctrl_type='ButtonControl', max_depth=3)
                    if yes_btns:
                        log(f"  clicking confirm: {yes_btns[0].Name}")
                        yes_btns[0].Click()
                        time.sleep(0.5)
                        break
                    dlg.SendKeys('{Enter}')
                    time.sleep(0.5)
                    break
            except:
                continue

        log("paste_and_save: done")
        return True
    except Exception as ex:
        log(f"  FATAL: {ex}\n{traceback.format_exc()}")
        return False


if __name__ == '__main__':
    try:
        filename = sys.argv[1] if len(sys.argv) > 1 else 'capture.atkdl'
        log(f"=== uia_save.py started, filename={filename} ===")
        dlg, btn = find_save_dialog(timeout=15.0)
        if dlg and btn:
            log(f"Dialog found, saving...")
            ok = paste_and_save(dlg, btn, filename)
            log(f"Result: {'OK' if ok else 'FAIL'}")
            sys.exit(0 if ok else 1)
        else:
            log("Save dialog not found")
            sys.exit(1)
    except Exception as ex:
        log(f"UNHANDLED: {ex}\n{traceback.format_exc()}")
        sys.exit(1)
