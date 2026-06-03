"""Click the Yes/Replace button on any open confirm dialog."""
import uiautomation as auto, time

root = auto.GetRootControl()

def _find_children(ctrl, cls_filter=None, name_contains=None, ctrl_type=None, max_depth=4):
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


confirms = _find_children(root, cls_filter='#32770', max_depth=5)
for dlg in confirms:
    name = dlg.Name if hasattr(dlg, 'Name') else ''
    print(f'Dialog: [{dlg.ClassName}] {name[:60]}')
    btns = _find_children(dlg, ctrl_type='ButtonControl', max_depth=4)
    for b in btns:
        bname = b.Name if hasattr(b, 'Name') else ''
        print(f'  Button: [{b.ControlTypeName}] {bname}')
        if '\u662f' in bname or '\u66ff\u6362' in bname or 'Yes' in bname:
            print(f'  -> Clicking: {bname}')
            b.Click()
            time.sleep(0.5)
            break

print('Done.')
