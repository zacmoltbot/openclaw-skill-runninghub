"""Offline regression for catalog sync and preserved international safeguards."""
import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runninghub/scripts'))
import runninghub as rh
import runninghub_app as app
import build_capabilities as builder


class SyncTests(unittest.TestCase):
    def test_catalog_and_menus(self):
        data = json.loads((ROOT/'runninghub/data/capabilities.json').read_text())
        ids = {e['endpoint'] for e in data['endpoints']}
        self.assertEqual(data['total'], len(ids))
        self.assertEqual(len(ids), 420)
        for name in ['image-models.md', 'video-models.md']:
            text = (ROOT/'runninghub/references'/name).read_text()
            candidates = re.findall(r'`([\w.-]+(?:/[\w.-]+)+)`', text)
            self.assertTrue(candidates)
            self.assertFalse(set(candidates) - ids)

    def test_global_hosts(self):
        for host in [rh.BASE_URL, rh.ACCOUNT_STATUS_URL, app.API_HOST]:
            self.assertIn('www.runninghub.ai', host)
            self.assertNotIn('.cn', host)

    def test_resource_pointers(self):
        text = (ROOT/'runninghub/SKILL.md').read_text()
        for rel in re.findall(r'\{baseDir\}/([\w./-]+)', text):
            self.assertTrue((ROOT/'runninghub'/rel).exists(), rel)

    def test_billing_decimal_and_unknown(self):
        self.assertEqual(rh._delta_str('1.10', '1.00'), '-0.1')
        self.assertEqual(rh._delta_str(None, '2'), 'unknown')
        self.assertEqual(rh.infer_billing_mode({'remainCoins': '2', 'remainMoney': '5'}), 'mixed')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rh.emit_billing_report({'balance': '5', 'coins':'20'}, {'balance':'4.5', 'coins':'10'}, 'mixed')
        for field in ['BALANCE_DELTA:-0.5','COINS_DELTA:-10','BILLING_MODE:mixed']:
            self.assertIn(field, out.getvalue())

    def test_preflight_before_standard_submit(self):
        args = SimpleNamespace(api_key='test', endpoint='test', task=None, output=None)
        out = io.StringIO()
        def submit(*unused):
            self.assertIn('PREFLIGHT_BILLING_MODE:', out.getvalue())
            return {'taskId':'test', 'status':'SUCCESS', 'results':[{'text':'ok'}]}
        with patch.object(rh, 'find_endpoint', return_value={'endpoint':'test','task':'test'}), patch.object(rh, 'fetch_account_status', return_value={}), patch.object(rh, 'build_payload', return_value={}), patch.object(rh, 'api_post', side_effect=submit), contextlib.redirect_stdout(out):
            rh.cmd_execute(args)
        self.assertIn('BALANCE_DELTA:unknown', out.getvalue())

    def test_preflight_before_app_submit(self):
        args = SimpleNamespace(api_key='test', run='123', node=None, file=None, instance_type='default')
        out = io.StringIO()
        def submit(*unused):
            self.assertIn('PREFLIGHT_BILLING_MODE:', out.getvalue())
            return {'taskId':'test'}
        with patch.object(app, 'fetch_account_status', return_value={}), patch.object(app, 'get_node_info', return_value=[]), patch.object(app, 'submit_task', side_effect=submit), patch.object(app, 'poll_task', return_value={'results':[{'text':'ok'}]}), contextlib.redirect_stdout(out):
            app.cmd_run(args)
        self.assertIn('COINS_DELTA:unknown', out.getvalue())

    def test_video_retries_recover(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d)/'result.mp4'
            def download(*unused):
                file.write_bytes(b'corrupt')
                return str(file)
            with patch.object(rh, 'download_file', side_effect=download) as dl, patch.object(rh,'fix_mov_to_mp4',return_value=False), patch.object(rh,'probe_video_file',side_effect=[(False,'bad',None),(True,'',{})]), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rh.download_file_with_validation('https://example.test/video',str(file),validate_video=True), str(file))
                self.assertEqual(dl.call_count, 2)

    def test_video_exhaustion_deletes_bad_file_and_keeps_url(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'bad.mp4'
            def download(*unused):
                file.write_bytes(b'bad'); return str(file)
            err=io.StringIO()
            with patch.object(rh,'download_file',side_effect=download) as dl, patch.object(rh,'fix_mov_to_mp4',return_value=False), patch.object(rh,'probe_video_file',return_value=(False,'bad',None)), contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                rh.download_file_with_validation('https://example.test/source',str(file),validate_video=True)
            self.assertEqual(dl.call_count,3)
            self.assertFalse(file.exists())
            failure=json.loads(err.getvalue().splitlines()[-1])
            self.assertEqual(failure['download_url'],'https://example.test/source')
            self.assertEqual(failure['error'],'VIDEO_DOWNLOAD_VALIDATION_FAILED')

    def test_real_ffprobe_rejects_corrupt_video(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'bad.mp4';file.write_bytes(b'not media')
            self.assertFalse(rh.probe_video_file(str(file))[0])

    def test_app_v2_and_legacy_response(self):
        self.assertEqual(app._normalize_submit_response({'taskId':'123'})[1],'123')
        self.assertEqual(app._normalize_submit_response({'code':0,'data':{'taskId':'456'}})[1],'456')
        with patch.object(app.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps({'taskId':'123'}),'')), patch.object(app,'curl_post_json') as legacy:
            self.assertEqual(app.submit_task('test','123',[])['taskId'],'123')
            legacy.assert_not_called()
        with patch.object(app.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps({'errorCode':'unsupported'}),'')), patch.object(app,'curl_post_json',return_value=subprocess.CompletedProcess([],0,json.dumps({'code':0,'data':{'taskId':'456'}}),'')) as legacy:
            self.assertEqual(app.submit_task('test','123',[])['taskId'],'456')
            self.assertEqual(legacy.call_args.args[1]['webappId'],123)

    def test_builder_filters_embedded_auth(self):
        param={'fieldKey':'imageUrl','type':'IMAGE','defaultValue':'https://example.test/?Rh-Comfy-Auth=secret'}
        self.assertNotIn('default',builder.simplify_param(param))
        self.assertEqual(builder.extract_task('minimax/hailuo-h3/text-to-video','video'),'text-to-video')
        for endpoint, kind, task in [('topazlabs/gigapixel', 'image', 'image-upscale'), ('model/layer-decomposition', 'image', 'image-layer-decomposition'), ('model/multimodal-video', 'video', 'multimodal-video'), ('model/text-to-world', '3d', 'text-to-world'), ('model/voice-design', 'audio', 'voice-design')]:
            self.assertEqual(builder.extract_task(endpoint,kind),task)

    def test_live_timeout_override(self):
        import os
        env=dict(os.environ,RUNNINGHUB_MAX_POLL_SECONDS='37')
        code='import sys;sys.path.insert(0,"runninghub/scripts");import runninghub;print(runninghub.MAX_POLL_SECONDS)'
        proc=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True,check=True)
        self.assertEqual(proc.stdout.strip(),'37')

if __name__ == '__main__':
    unittest.main()
