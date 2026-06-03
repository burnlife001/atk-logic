"""Quick UIA diagnostic: find #32770 dialogs and Save buttons."""
import uiautomation as auto

root = auto.GetRootControl()
print("=== #32770 Dialogs ===")
for w in root.GetChildren():
    try:
        cls = w.ClassName if hasattr(w, 'ClassName') else ''
        name = w.Name if hasattr(w, 'Name') else ''
        if '#32770' in cls:
            print(f"  [{cls}] '{name}' (hwd=0x{w.NativeWindowHandle:X})")
            for c in w.GetChildren():
                try:
                    ct = c.ControlTypeName if hasattr(c, 'ControlTypeName') else '?'
                    cn = c.Name if hasattr(c, 'Name') else ''
                    ccls = c.ClassName if hasattr(c, 'ClassName') else ''
                    print(f"    [{ct}] [{ccls}] '{cn}'")
                except:
                    pass
    except:
        continue

print()
print("=== Any window with '\\u4fdd\\u5b58' in name ===")
def search(ctrl, d=0):
    if d > 4:
        return
    try:
        name = ctrl.Name if hasattr(ctrl, 'Name') else ''
        if '\u4fdd\u5b58' in name or '\u53e6\u5b58' in name:
            cls = ctrl.ClassName if hasattr(ctrl, 'ClassName') else ''
            print(f"  d={d} [{cls}] '{name[:60]}'")
    except:
        pass
    try:
        for child in ctrl.GetChildren():
            search(child, d+1)
    except:
        pass

search(root, 0)
print("Done.")
