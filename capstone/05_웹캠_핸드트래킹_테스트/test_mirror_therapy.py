"""Offline regression tests. No camera, Qt window, or model download is used.

Run: python -B -m unittest discover -s 05_웹캠_핸드트래킹_테스트 -p test_mirror_therapy.py -v
"""
import ast
import csv
import hashlib
import json
import math
import os
import queue
import tempfile
import time
import unittest
from collections import deque
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch

import numpy as np
from mirror_capture import (RawFrameWriter, measure_hand, sample_depth,
                            contiguous_segments, MAX_FRAME_GAP_S,
                            DEPTH_MIN_M, DEPTH_MAX_M, DEPTH_EDGE_M)


def load_logic():
    """Load original functions/classes with UI base classes stubbed, without imports/main."""
    source = Path(__file__).with_name('Mirror_therapy.py')
    tree = ast.parse(source.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, (ast.Assign, ast.FunctionDef, ast.ClassDef))]
    namespace = dict(np=np, math=math, os=os, csv=csv, json=json, time=time, queue=queue,
                     datetime=datetime, deque=deque, hashlib=hashlib, Path=Path,
                     __file__=str(source), sys=__import__('sys'), re=__import__('re'), uuid=__import__('uuid'),
                     RawFrameWriter=RawFrameWriter, measure_hand=measure_hand,
                     contiguous_segments=contiguous_segments, MAX_FRAME_GAP_S=MAX_FRAME_GAP_S,
                     DEPTH_MIN_M=DEPTH_MIN_M, DEPTH_MAX_M=DEPTH_MAX_M, DEPTH_EDGE_M=DEPTH_EDGE_M,
                     QThread=object, QMainWindow=object, FigureCanvas=object, QWidget=object,
                     pyqtSignal=lambda *args: None, plt=NS(rcParams={}))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


LOGIC = load_logic()
APP = LOGIC['ClinicalApp']


def hand_fixture():
    world = np.zeros((21, 3))
    world[:, 0] = np.linspace(-.04, .04, 21)
    world[:, 1] = np.linspace(.01, .10, 21)
    world[0], world[9] = [0, 0, 0], [0, .08, 0]
    world[4], world[8] = [-.025, .09, 0], [.025, .09, 0]
    pixels = np.tile([50., 50.], (21, 1))
    pixels[4], pixels[8] = [45., 50.], [55., 50.]
    return world, pixels


def measurement(depth=True):
    world, pixels = hand_fixture()
    return measure_hand(world, pixels, np.full((101, 101), .6) if depth else None,
                        lambda uv, z: [(uv[0]-50)*z/100, (uv[1]-50)*z/100, z], 80)


def records(values, times=None):
    times = np.arange(len(values)) / 30 if times is None else times
    return [dict(time=float(t), frame_id=i+1, hand='Right', task=APP.TASKS[0], protocol_valid=True,
                 raw={j: float(v) for j in LOGIC['JOINT_DEFS']},
                 filtered={**{j: float(v) for j in LOGIC['JOINT_DEFS']}, 'Grip_Aperture': 5.0},
                 metrics3d={}, angles3d={}, canon=None, measurement=measurement(),
                 capture_monotonic_s=100+float(t), capture_unix_s=1000+float(t))
            for i, (t, v) in enumerate(zip(times, values))]


class MeasurementTests(unittest.TestCase):
    def test_independent_metric_scales(self):
        result = measurement()
        self.assertAlmostEqual(result['mp_aperture_mm'], 50)
        self.assertAlmostEqual(result['mp_aperture_cal_mm'], 50)
        self.assertAlmostEqual(result['rs_aperture_mm'], 60)
        self.assertAlmostEqual(result['rs_minus_mp_mm'], 10)
        # Origins intentionally differ: MP hand origin vs RS camera origin.
        self.assertEqual(result['mp_points'][4, 2], 0)
        self.assertEqual(result['rs_points'][4, 2], .6)

    def test_webcam_keeps_mp_and_marks_rs_missing(self):
        result = measurement(False)
        self.assertTrue(result['mp_valid'])
        self.assertFalse(result['rs_valid'])
        self.assertEqual(result['rs_status'][4], 'no_depth')
        self.assertIsNone(result['rs_aperture_mm'])
        self.assertTrue(np.isnan(result['rs_points']).all())

    def test_missing_world_does_not_invent_metric_scale(self):
        _, pixels = hand_fixture()
        result = measure_hand(None, pixels, np.full((101, 101), .6), lambda p, z: [*p, z])
        self.assertFalse(result['mp_valid'])
        self.assertIsNone(result['mp_aperture_mm'])
        self.assertTrue(result['rs_valid'])

    def test_depth_holes_bounds_and_edges_are_not_filled(self):
        depth = np.full((7, 7), .6)
        self.assertEqual(sample_depth(depth, [-.1, 3])[1], 'outside_image')
        self.assertEqual(sample_depth(depth, [7, 3])[1], 'outside_image')
        depth[3, 3] = 0
        self.assertEqual(sample_depth(depth, [3, 3])[1], 'depth_hole')
        depth[3, 3] = 3
        self.assertEqual(sample_depth(depth, [3, 3])[1], 'depth_out_of_range')
        depth[3, 3] = .6
        depth[2:5, 4] = 1.2
        self.assertEqual(sample_depth(depth, [3, 3])[1], 'depth_edge')

    def test_zero_aperture_is_valid(self):
        world, pixels = hand_fixture()
        world[8], pixels[8] = world[4], pixels[4]
        result = measure_hand(world, pixels, np.full((101, 101), .6), lambda uv, z: [*uv, z], 80)
        self.assertEqual(result['mp_aperture_cal_mm'], 0)
        self.assertEqual(result['rs_aperture_mm'], 0)


class MotionTests(unittest.TestCase):
    def test_initial_partial_open_is_not_a_cycle(self):
        t = np.arange(30)/30
        self.assertEqual(LOGIC['count_cycles'](t, np.linspace(60, 180, 30))[0], 0)
        self.assertEqual(LOGIC['count_cycles'](t, np.r_[np.linspace(180, 60, 15),
                                                         np.linspace(60, 180, 15)])[0], 1)

    def test_no_negative_directional_speed(self):
        metrics = APP._trial_metrics(records(np.linspace(60, 180, 30)))
        self.assertEqual(metrics['flex_speed'], 0)
        self.assertGreater(metrics['ext_speed'], 0)

    def test_gap_does_not_create_cycle_or_velocity(self):
        recs = records(np.r_[np.linspace(180, 60, 30), np.linspace(60, 180, 30)],
                       np.r_[np.arange(30)/30, 10+np.arange(30)/30])
        metrics = APP._trial_metrics(recs)
        self.assertEqual(metrics['cycles'], 0)
        self.assertAlmostEqual(metrics['valid_duration'], 58/30)
        self.assertLess(metrics['ext_speed'], 125)

    def test_single_missing_frame_also_breaks_segment(self):
        recs = records(np.ones(30)*150)
        del recs[15]
        self.assertEqual(len(contiguous_segments(recs)), 2)

    def test_summary_compares_paired_distances(self):
        recs = records(np.linspace(60, 180, 30))
        recs[0]['measurement'] = measurement(False)
        metrics = APP._trial_metrics(recs)
        self.assertEqual(metrics['paired_samples'], 29)
        self.assertEqual(metrics['rs_valid_samples'], 29)
        self.assertAlmostEqual(metrics['rs_mp_mean_diff_mm'], 10)


class RecordingTests(unittest.TestCase):
    def test_lossless_round_trip_and_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = RawFrameWriter(Path(folder)/'raw')
            arrays = dict(color_bgr=np.arange(60, dtype=np.uint8).reshape(4, 5, 3),
                          depth_native_z16=np.array([[0, 123, 65535]], dtype=np.uint16),
                          depth_aligned_z16=np.arange(20, dtype=np.uint16).reshape(4, 5))
            writer.submit(dict(frame_id=17, capture_monotonic_s=12.25, depth_scale_m=.001), arrays)
            summary = writer.close()
            self.assertTrue(summary['complete'])
            self.assertEqual(summary['written_frames'], 1)
            with np.load(Path(folder)/'raw/frame_00000017.npz', allow_pickle=False) as data:
                for name, array in arrays.items():
                    np.testing.assert_array_equal(data[name], array)
                self.assertEqual(json.loads(data['metadata_json'].item())['depth_scale_m'], .001)
            with (Path(folder)/'raw/frames.csv').open(encoding='utf-8-sig', newline='') as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]['frame_id'], '17')

    def test_write_failure_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('mirror_capture.np.save', side_effect=OSError('disk full')):
                writer = RawFrameWriter(Path(folder)/'raw')
                writer.submit(dict(frame_id=1), dict(color_bgr=np.zeros((2, 2, 3))))
                summary = writer.close()
            self.assertFalse(summary['complete'])
            self.assertIn('disk full', summary['error'])
            self.assertEqual(summary['written_frames'], 0)

    def test_queue_overflow_is_not_silently_dropped(self):
        writer = RawFrameWriter.__new__(RawFrameWriter)
        writer.error = None
        writer._closing = __import__('threading').Event()
        writer.queue = queue.Queue(maxsize=1)
        writer.queue.put(({}, {}))
        with self.assertRaises(RuntimeError):
            writer.submit(dict(frame_id=2), {})
        self.assertIsNotNone(writer.error)

    def test_distance_csv_preserves_missing_values_and_frame_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            app = APP.__new__(APP)
            app.folder, app.records, app.frame_log = folder, records([180, 170]), []
            app.records[1]['measurement'] = measurement(False)
            app._export_comparison('test')
            with (Path(folder)/'test_distance_comparison.csv').open(encoding='utf-8-sig', newline='') as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(rows[0]['Frame_ID'], '1')
            self.assertEqual(rows[0]['RS_Aperture_raw_mm'], '60.0000')
            self.assertEqual(rows[1]['RS_Aperture_raw_mm'], '')
            self.assertEqual(rows[1]['RS_Thumb_Status'], 'no_depth')
            with (Path(folder)/'test_landmarks.csv').open(encoding='utf-8-sig', newline='') as fp:
                self.assertEqual(len(list(csv.DictReader(fp))), 42)


class WorkerTests(unittest.TestCase):
    def test_setting_changes_wait_for_frame_boundary(self):
        worker = LOGIC['VideoWorker']()
        worker.filters['existing'] = object()
        worker.set_smooth_3d(False)
        self.assertTrue(worker.smooth_3d)
        self.assertIn('existing', worker.filters)
        worker._apply_commands()
        self.assertFalse(worker.smooth_3d)
        self.assertEqual(worker.filters, {})

    def test_mock_camera_streams_mirror_and_view_keep_measurements_identical(self):
        world, pixels = hand_fixture()
        # A nondegenerate palm is needed by SVD/canonical view.
        world[[0, 5, 9, 13, 17]] = [[0, 0, 0], [-.035, .06, 0], [0, .08, 0],
                                    [.02, .07, 0], [.04, .05, 0]]
        result = NS(multi_hand_landmarks=[NS(landmark=[NS(x=u/101, y=v/101, z=0) for u,v in pixels])],
                    multi_hand_world_landmarks=[NS(landmark=[NS(x=x,y=y,z=z) for x,y,z in world])],
                    multi_handedness=[NS(classification=[NS(label='Left', score=.99)])])
        detector = NS(process=lambda rgb: result, close=lambda: None)
        mp = NS(solutions=NS(hands=NS(Hands=lambda **kw: detector, HAND_CONNECTIONS=[]),
                            drawing_utils=NS(draw_landmarks=lambda img, *a: img.__setitem__((slice(10,20), slice(10,20)), 255)),
                            drawing_styles=NS(get_default_hand_landmarks_style=lambda: None,
                                              get_default_hand_connections_style=lambda: None)))
        frame = np.zeros((101,101,3), dtype=np.uint8)
        cap = NS(isOpened=lambda: True, read=lambda: (True, frame.copy()),
                 set=lambda *a: None, release=lambda: None)
        cv = NS(VideoCapture=lambda *a: cap, CAP_DSHOW=0, CAP_PROP_FRAME_WIDTH=3,
                CAP_PROP_FRAME_HEIGHT=4, COLOR_BGR2RGB=0, FONT_HERSHEY_SIMPLEX=0, LINE_AA=0,
                cvtColor=lambda f, _: f.copy(), putText=lambda *a: None, flip=lambda f, _: f[:,::-1].copy(),
                hconcat=lambda frames: np.hstack(frames), INTER_AREA=0,
                resize=lambda frame, size, **kw: frame[::2, ::2][:size[1], :size[0]].copy())
        intr = NS(width=101, height=101, fx=100., fy=100., ppx=50., ppy=50., model='none', coeffs=[0.]*5)
        profile = NS(as_video_stream_profile=lambda: NS(get_intrinsics=lambda: intr))
        def sdk_frame(data, number, stamp):
            return NS(get_data=lambda: data, get_frame_number=lambda: number,
                      get_timestamp=lambda: stamp, get_frame_timestamp_domain=lambda: 'hardware_clock',
                      profile=profile)
        color_frame = sdk_frame(frame, 100, 1000.)
        native_frame = sdk_frame(np.full((7, 7), 600, dtype=np.uint16), 200, 1000.)
        aligned_frame = sdk_frame(np.full((101, 101), 600, dtype=np.uint16), 200, 1000.)
        original = NS(get_color_frame=lambda: color_frame, get_depth_frame=lambda: native_frame)
        aligned = NS(get_depth_frame=lambda: aligned_frame)
        pipe = NS(wait_for_frames=lambda **kw: original, stop=lambda: None)
        align = NS(process=lambda original: aligned)
        rs = NS(distortion=NS(modified_brown_conrady='modified'),
                rs2_deproject_pixel_to_point=lambda intr, uv, z: [(uv[0]-50)*z/100, (uv[1]-50)*z/100, z])
        outputs=[]
        cases = [(False, False, 'color'), (False, True, 'color'),
                 (True, False, 'color'), (True, True, 'color'),
                 (True, False, 'both'), (True, True, 'depth')]
        with patch.dict(LOGIC, cv2=cv, mp=mp, rs=rs):
            for use_depth, mirrored, view in cases:
                worker = LOGIC['VideoWorker']()
                worker.mirror_mode, worker.view_mode = mirrored, view
                worker.source_name = 'realsense' if use_depth else 'webcam'
                worker.depth_scale = .001
                worker._open_realsense = lambda: (pipe, align) if use_depth else None
                worker._colorize_depth = lambda depth: np.zeros((101, 101, 3), dtype=np.uint8)
                worker.failed = MagicMock()
                recorded = []
                worker.recorder = NS(submit=lambda info, arrays: recorded.append(arrays))
                def emit(*args):
                    outputs.append(args[-1]['measurements']['Right'])
                    worker.running = False
                worker.frame_processed = NS(emit=emit)
                worker.run()
                worker.failed.emit.assert_not_called()
                self.assertEqual(len(recorded), 1)
                self.assertFalse(recorded[0]['color_bgr'].any())
                self.assertTrue(recorded[0]['overlay_bgr'].any())
        self.assertEqual(len(outputs), len(cases))
        for output, (use_depth, _, _) in zip(outputs, cases):
            np.testing.assert_array_equal(outputs[0]['pixels'], output['pixels'])
            self.assertEqual(outputs[0]['mp_aperture_mm'], output['mp_aperture_mm'])
            self.assertEqual(output['rs_valid'], use_depth)
            if use_depth:
                self.assertAlmostEqual(output['rs_aperture_mm'], 60., places=4)


def app_fixture():
    app = APP.__new__(APP)
    app.session_on, app.session_id, app.t_session = True, 'test', 100.
    app.finishing = app.unsaved = app.close_pending = False
    app._stop_time, app._last_capture, app._trial_previous = None, None, None
    app._session_error = None
    app.trial_on, app.trial_idx, app.t_trial, app.auto_left = True, 1, 0., 1.
    app.trial_task, app.trial_hands = APP.TASKS[0], ('Right',)
    app.task_history = [(0., APP.TASKS[0])]
    app.records, app.trials, app.frame_log, app.capture_summary = [], [], [], {}
    app.t_app, app.paused = 100., False
    for name in ('btn_start', 'btn_stop', 'btn_trial', 'lbl_session', 'lbl_fps', 'lbl_video',
                 'chart', 'table', 'cb_task', 'chk_3d', 'chk_mirror', 'spin_auto',
                 'txt_name', 'spin_age', 'cb_gender', 'rb_healthy', 'rb_patient', 'spin_fma',
                 'cb_brs', 'cb_affected', 'spin_palm', 'chk_filter', 'chk_smooth', 'chk_hold',
                 'worker'):
        setattr(app, name, MagicMock())
    app.worker.source_name = 'webcam'
    app.txt_name.text.return_value = 'Test Subject'
    app.spin_age.value.return_value = 30
    app.spin_auto.value.return_value = 1
    app.spin_palm.value.return_value = 80
    app.spin_fma.value.return_value = 8
    app.cb_gender.currentText.return_value = '남성 (Male)'
    app.cb_task.currentText.return_value = APP.TASKS[0]
    app.rb_healthy.isChecked.return_value = True
    app.rb_patient.isChecked.return_value = False
    app.chk_3d.isChecked.return_value = False
    for name in ('chk_filter', 'chk_smooth', 'chk_hold', 'chk_mirror'):
        getattr(app, name).isChecked.return_value = False
    app._status, app.toast, app._update_gauge = MagicMock(), MagicMock(), MagicMock()
    app._trial_btn = MagicMock()
    return app


class SessionTests(unittest.TestCase):
    def frame(self, app, t, hand='Right', session='test'):
        data = records([160])[0]
        angles = {hand: dict(raw=data['raw'], filtered=data['filtered'])} if hand else {}
        capture = dict(source='webcam', capture_monotonic_s=100+t, capture_unix_s=1000+t,
                       session_id=session, frame_id=round(t*100)+1,
                       measurements={hand: measurement(False)} if hand else {})
        with patch.dict(LOGIC, time=NS(perf_counter=lambda: 100+t), QtGui=MagicMock(), Qt=MagicMock()):
            app.on_frame(np.zeros((2, 2, 3), dtype=np.uint8), angles, 30., int(bool(hand)), {}, {}, capture)

    def test_auto_time_uses_valid_frames_and_same_hand(self):
        app = app_fixture()
        self.frame(app, .1)
        self.frame(app, .2)
        self.assertAlmostEqual(app.auto_left, .9)
        self.frame(app, .3, None)
        self.frame(app, 1.0)
        self.assertAlmostEqual(app.auto_left, .9)
        self.frame(app, 1.1)
        self.assertAlmostEqual(app.auto_left, .8)
        self.frame(app, 1.2, 'Left')
        self.assertTrue(app.paused)
        self.assertAlmostEqual(app.auto_left, .8)

    def test_camera_silence_pauses_without_consuming_auto_time(self):
        app = app_fixture()
        app._last_capture = 100.
        with patch.dict(LOGIC, time=NS(perf_counter=lambda: 105.)):
            app._tick()
        self.assertTrue(app.paused)
        self.assertEqual(app.auto_left, 1.)

    def test_previous_session_frames_are_not_recorded(self):
        app = app_fixture()
        self.frame(app, .1, session='old-session')
        self.assertEqual(app.records, [])
        self.assertEqual(app.frame_log, [])

    def test_trial_keeps_start_task_even_if_control_changes(self):
        app = app_fixture()
        app.records = records(np.linspace(180, 60, 30))
        app.cb_task.currentText.return_value = APP.TASKS[1]
        app.table.rowCount.return_value = 0
        with patch.dict(LOGIC, QTableWidgetItem=lambda value: value):
            app._finish_trial(end_time=1.)
        self.assertEqual(len(app.trials), 1)
        self.assertEqual(app.trials[0]['task'], APP.TASKS[0])
        self.assertEqual(app.trials[0]['samples'], 30)

    def test_save_failure_keeps_data_and_allows_retry(self):
        app = app_fixture()
        app.records = records([180])
        app._stop_time = 1.
        app.save_session = MagicMock(side_effect=[OSError('disk full'), None])
        app._save_finished_session()
        self.assertTrue(app.unsaved)
        self.assertEqual(len(app.records), 1)
        app.btn_start.setEnabled.assert_called_with(False)
        app._save_finished_session()
        self.assertFalse(app.unsaved)

    def test_same_subject_gets_unique_session_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            app = app_fixture()
            app.base_dir, app.session_on = folder, False
            app.start_session()
            first = app.folder
            app.session_on = False
            app.start_session()
            self.assertNotEqual(app.folder, first)
            self.assertTrue(Path(first).is_dir())
            self.assertTrue(Path(app.folder).is_dir())

    def test_full_export_schema_and_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            app = app_fixture()
            app.folder, app.records = folder, records(np.linspace(180, 60, 30))
            app.export_plot, app.export_joint_plot = MagicMock(), MagicMock()
            app.table.rowCount.return_value = 0
            with patch.dict(LOGIC, QTableWidgetItem=lambda value: value,
                            cv2=NS(__version__='mock'), mp=NS(__version__='mock'),
                            QtCore=NS(PYQT_VERSION_STR='mock')):
                app._finish_trial(end_time=1.)
                # Simulate a frame captured before manual stop but delivered later.
                late = records([100], times=[.99])[0]
                late['frame_id'] = 31
                app.records.append(late)
                app.save_session(1.)
            self.assertEqual(app.trials[0]['samples'], 31)
            for path in Path(folder).glob('*.csv'):
                with path.open(encoding='utf-8-sig', newline='') as fp:
                    rows = list(csv.reader(fp))
                self.assertTrue(all(len(row) == len(rows[0]) for row in rows), path.name)
            meta = json.loads((Path(folder)/'subject_metadata.json').read_text(encoding='utf-8'))
            self.assertEqual(meta['schema_version'], 2)
            self.assertEqual(meta['session_id'], 'test')
            self.assertIn('RS', meta['measurement_methods'])


if __name__ == '__main__':
    unittest.main()
