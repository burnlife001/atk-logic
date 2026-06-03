"""Quick UIA test: list windows and search for ATK-Logic dialog."""
import uiautomation as auto

print("=== Top-level windows ===")
root = auto.GetRootControl()
children = root.GetChildren()
count = 0
for c in children:
    try:
        name = c.Name
        cls = c.ClassName
        if name or cls:
            print(f"  [{cls}] {name[:80]}")
            count += 1
    except:
        continue
print(f"Total: {count} windows with name/class")

print()
print("=== ATK-Logic window ===")
atk = auto.WindowControl(searchDepth=1, ClassName="Qt5152QWindowOwnDCIcon")
print(f"Exists: {atk.Exists()}")
if atk.Exists():
    print(f"Name: {atk.Name}")
    print(f"Children:")
    for child in atk.GetChildren():
        try:
            print(f"  [{child.ControlTypeName}] [{child.ClassName}] {child.Name[:60]}")
            # Check grandchildren too
            for gc in child.GetChildren():
                try:
                    print(f"    -> [{gc.ControlTypeName}] [{gc.ClassName}] {gc.Name[:60]}")
                except:
                    pass
        except:
            continue

print()
print("=== Search for 'Save' button anywhere ===")
# Search all descendants of root
def find_save_btn(ctrl, depth=0):
    if depth > 4:
        return
    try:
        name = ctrl.Name if hasattr(ctrl, 'Name') else ""
        if "save" in name.lower() or "保存" in name:
            print(f"  depth={depth} [{ctrl.ControlTypeName}] [{ctrl.ClassName}] name='{name}'")
    except:
        pass
    try:
        for child in ctrl.GetChildren():
            find_save_btn(child, depth+1)
    except:
        pass

find_save_btn(root, 0)
print("Done.")
