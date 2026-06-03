"""Dismiss any #32770 save dialogs by clicking Cancel."""
import uiautomation as auto

root = auto.GetRootControl()


def find_all(ctrl, cls, d=0, out=None, max_d=5):
    if d > max_d or out is None:
        return
    try:
        if cls in (ctrl.ClassName or ""):
            out.append(ctrl)
    except:
        pass
    try:
        for c in ctrl.GetChildren():
            find_all(c, cls, d + 1, out, max_d)
    except:
        pass


dlgs = []
find_all(root, "#32770", 0, dlgs, 6)
for dlg in dlgs:
    name = dlg.Name or "?"
    print(f"Dialog: [{dlg.ClassName}] {name[:60]}")
    for c in dlg.GetChildren():
        try:
            ctype = c.ControlTypeName or "?"
            cname = c.Name or "?"
            if ctype == "ButtonControl" and "\u53d6\u6d88" in cname:
                print(f"  Clicking Cancel: {cname}")
                c.Click()
        except:
            pass
print("Done.")
