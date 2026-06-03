"""Dump UIA tree of all #32770 dialogs."""
import uiautomation as auto


def dump_tree(ctrl, depth=0, max_depth=5):
    if depth > max_depth:
        return
    try:
        ct = ctrl.ControlTypeName if hasattr(ctrl, "ControlTypeName") else "?"
        cls = ctrl.ClassName if hasattr(ctrl, "ClassName") else ""
        name = (ctrl.Name or "") if hasattr(ctrl, "Name") else ""
        indent = "  " * depth
        print(f"{indent}[{ct}] cls={cls} name={name!r}")
    except:
        return
    try:
        for child in ctrl.GetChildren():
            dump_tree(child, depth + 1, max_depth)
    except:
        pass


def find_and_dump(ctrl, depth=0, max_depth=5):
    """Search recursively for #32770 dialogs and dump their subtrees."""
    if depth > max_depth:
        return False
    try:
        cls = ctrl.ClassName if hasattr(ctrl, "ClassName") else ""
        if "#32770" in cls:
            print("=== #32770 dialog ===")
            dump_tree(ctrl, 0, 5)
            print()
            return True
    except:
        pass
    try:
        for child in ctrl.GetChildren():
            if find_and_dump(child, depth + 1, max_depth):
                pass  # continue searching for more
    except:
        pass
    return False


root = auto.GetRootControl()
find_and_dump(root, 0, 6)
print("Done.")
