"""Open save dialog by sending Ctrl+S to ATK-Logic via UIA."""
import uiautomation as auto, time

atk = auto.WindowControl(searchDepth=1, ClassName='FramelessWindow_QML_51')
if atk.Exists():
    print(f'ATK-Logic found: {atk.Name}')
    atk.SetFocus()
    time.sleep(0.3)
    atk.SendKeys('{Ctrl}S')
    time.sleep(1.5)
    print('Ctrl+S sent')
else:
    print('ATK-Logic not found')
