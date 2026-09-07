"""Render the real Qt layout offscreen without opening a camera or running MediaPipe.

Optional dependency folder: MIRROR_UI_DEPS. PNGs go to outputs/ui_preview.
"""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['MPLCONFIGDIR'] = str(Path(tempfile.gettempdir()) / 'codex-mirror-ui-mpl')
deps = os.environ.get('MIRROR_UI_DEPS')
if deps:
    sys.path.insert(0, deps)
root = Path(__file__).resolve().parents[1] / '05_웹캠_핸드트래킹_테스트'
sys.path.insert(0, str(root))
for name in ('cv2', 'mediapipe'):
    sys.modules[name] = types.ModuleType(name)

from PyQt6 import QtGui, QtWidgets

spec = importlib.util.spec_from_file_location('mirror_preview', root / 'Mirror_therapy.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreviewWorker(module.VideoWorker):
    def start(self):
        pass

    def stop(self):
        pass


module.VideoWorker = PreviewWorker
app = QtWidgets.QApplication([])
# The Windows offscreen Qt plugin does not discover system fonts automatically.
for font in ('malgun.ttf', 'segoeui.ttf', 'seguisym.ttf'):
    QtGui.QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / font))
app.setFont(QtGui.QFont('Malgun Gothic', 10))
window = module.ClinicalApp()
window.showFullScreen()
app.processEvents()
assert window.isFullScreen()
window._escape_fullscreen()
app.processEvents()
assert not window.isFullScreen()
window._toggle_fullscreen()
app.processEvents()
assert window.isFullScreen()
window.showNormal()
window.lbl_video.setText('카메라 미리보기 · UI 검증 중 (장치 연결 없음)')
window.lbl_session.setText('● REC (123.4초 | 3210 프레임)')
window.lbl_fps.setText('RealSense | FPS: 29.8 | Hands: 2')
window.lbl_trial.setText('🔴 [Trial #12] 유효 측정 4.8초 남음')
window.lbl_toast.setText('저장 완료! 두 방식의 측정값과 원본 RGB·깊이 데이터를 저장했습니다.')
for hand in module.HANDS:
    sample = {j: 123.0 for j in module.JOINT_DEFS}
    sample['Thumb_PalmarAbd'] = 42.0
    window._update_gauge(hand, dict(filtered=sample), .75)
window.table.setRowCount(3)
for row in range(3):
    for col, value in enumerate(['Trial #12', '오른손', 'Task 4', '5.08초', '3회', '1.65',
                                 '740.2', '32.4', '42.0', '8.1', '124.0', '-2.51']):
        window.table.setItem(row, col, QtWidgets.QTableWidgetItem(value))
out = root / 'outputs' / 'ui_preview'
out.mkdir(parents=True, exist_ok=True)
for width, height in [(1536, 864), (1280, 720), (1920, 1080)]:
    window.resize(width, height)
    window.show()
    for _ in range(8):
        app.processEvents()
    window.analysis_tabs.setCurrentIndex(0)
    for _ in range(3):
        app.processEvents()
    path = out / f'ui_{width}x{height}.png'
    window.grab().save(str(path))
    controls = [window.btn_start, window.btn_stop, window.btn_trial]
    for button in controls:
        assert button.parentWidget().rect().contains(button.geometry()), (width, button.text(), 'outside parent')
    for left, right in [(controls[0], controls[1]), (controls[0], controls[2]), (controls[1], controls[2])]:
        assert not left.geometry().intersects(right.geometry()), (width, 'buttons overlap')
    for check in [window.chk_mirror, window.chk_filter, window.chk_3d, window.chk_smooth, window.chk_hold]:
        assert check.width() >= check.minimumSizeHint().width(), (width, check.text(), 'clipped')
    print(width, height, 'actual', window.width(), window.height(),
          'left scroll', window.settings_scroll.verticalScrollBar().maximum(),
          'right scroll', window.content_scroll.verticalScrollBar().maximum(), str(path))
    assert window.content_scroll.horizontalScrollBar().maximum() == 0, (width, 'unnecessary horizontal scroll')
    # Verify all axis labels are inside the actual resized Matplotlib canvas.
    window.chart.draw()
    renderer = window.chart.get_renderer()
    for ax in window.chart.axes.values():
        for label in (ax.xaxis.label, ax.yaxis.label):
            bounds = label.get_window_extent(renderer)
            assert window.chart.fig.bbox.contains(bounds.x0, bounds.y0), (width, 'chart label clipped')
window.analysis_tabs.setCurrentIndex(2)
for _ in range(3):
    app.processEvents()
window.grab().save(str(out / 'ui_results.png'))
window.analysis_tabs.setCurrentIndex(1)
for _ in range(3):
    app.processEvents()
window.grab().save(str(out / 'ui_3d.png'))
window.close()
