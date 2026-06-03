"""Test interacting with filename ComboBox in save dialog."""
import uiautomation as auto
import time

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
if not dlgs:
    print("No #32770 dialogs found")
else:
    for dlg in dlgs:
        name = dlg.Name or "?"
        print(f"Dialog: {name[:60]}")

        # Find ComboBox with 文件名
        combos = []
        find_all(dlg, "AppControlHost", 0, combos, 5)
        for combo in combos:
            cname = combo.Name or "?"
            if "\u6587\u4ef6\u540d" in cname or "filename" in cname.lower():
                print(f"  Found filename ComboBox: {cname}")
                print(f"    ControlType: {combo.ControlTypeName}")

                # Try GetValuePattern
                try:
                    vp = combo.GetValuePattern()
                    print(f"    ValuePattern available: current={vp.Value}")
                except:
                    print(f"    No ValuePattern")

                # Try GetTextPattern
                try:
                    tp = combo.GetTextPattern()
                    print(f"    TextPattern available")
                except:
                    print(f"    No TextPattern")

                # Try to find Edit child inside
                for child in combo.GetChildren():
                    try:
                        print(f"    Child: [{child.ControlTypeName}] {child.Name or '?'}")
                    except:
                        pass

                # Try LegacyIAccessible pattern
                try:
                    leg = combo.GetLegacyIAccessiblePattern()
                    print(f"    LegacyIAccessible: value={leg.Value}")
                except:
                    print(f"    No LegacyIAccessible")

                # Try SetFocus + SendKeys
                try:
                    combo.SetFocus()
                    time.sleep(0.3)
                    combo.SendKeys("test_file.atkdl")
                    time.sleep(0.5)
                    print(f"    SendKeys sent")
                except Exception as ex:
                    print(f"    SendKeys failed: {ex}")

print("Done.")
