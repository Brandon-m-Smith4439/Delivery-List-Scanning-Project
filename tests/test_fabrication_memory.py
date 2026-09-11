# File: tests/test_fabrication_memory.py
"""Durable fabrication checks, event invalidation and bounded manual refresh."""
from datetime import datetime, timezone
from unittest import mock
import time

from backend.production_files import ProductionFileService
from test_sketch_recovery import service


def assigned(machine='denver'):
    return {'machine': machine, 'machineCode': machine, 'required': True, 'confidence': 'high'}


def test_completed_result_survives_restart_without_rereading_sources(tmp_path):
    s=service(tmp_path); (s.roots['program']/'23800101.egl').write_text('done')
    with mock.patch.object(s,'machine_assignment',return_value=assigned()):
        first=s.fabrication_status('238001','001')
    assert first['fabricated'] is True
    s._persist_index(); reopened=ProductionFileService(s.config)
    with mock.patch.object(reopened,'machine_assignment',side_effect=AssertionError('Unexpected reread')):
        second=reopened.fabrication_status('238001','001')
    assert second['fabricated'] is True and second['remembered'] is True
    assert second['checkedAt']==first['checkedAt']


def test_unrelated_file_refresh_keeps_result_but_matching_new_evidence_rechecks(tmp_path):
    s=service(tmp_path)
    with mock.patch.object(s,'machine_assignment',return_value=assigned()) as classify:
        assert s.fabrication_status('238001','001')['fabricated'] is False
        calls=classify.call_count
        (s.roots['program']/'23800201.egl').write_text('other')
        s.assets('program',refresh=True)
        assert s.fabrication_status('238001','001')['fabricated'] is False
        assert classify.call_count==calls
        (s.roots['program']/'23800101.egl').write_text('done')
        s.assets('program',refresh=True)
        assert s.fabrication_status('238001','001')['fabricated'] is True
        assert classify.call_count==calls+1


def test_only_reject_or_remake_lifecycle_bypasses_remembered_completion(tmp_path):
    s=service(tmp_path);(s.roots['program']/'23800101.egl').write_text('done')
    with mock.patch.object(s,'machine_assignment',return_value=assigned()) as classify:
        s.fabrication_status('238001','001',job='ordinary-job',label_hint={'pieceRevision':'one','lifecycleRevision':'original'})
        # Ordinary job, quantity, dimension, source and label edits cannot erase
        # an already observed physical completion.
        remembered=s.fabrication_status('238001','001',job='changed-job',label_hint={'pieceRevision':'two','lifecycleRevision':'original'})
        assert remembered['fabricated'] is True and remembered['remembered'] is True
        assert classify.call_count==1
        s.fabrication_status('238001','001',label_hint={'lifecycleRevision':'remake-1'})
        assert classify.call_count==2
        cutoff=datetime.fromtimestamp(time.time()+2,timezone.utc).isoformat()
        assert s.fabrication_status('238001','001',evidence_after=cutoff)['fabricated'] is False


def test_pending_fabrication_expires_and_finds_later_completion(tmp_path):
    s=service(tmp_path)
    with mock.patch.object(s,'machine_assignment',return_value=assigned()) as classify:
        first=s.fabrication_status('238001','001')
        assert first['fabricated'] is False and first['retryAfterSeconds']==s.cache_seconds
        assert s.fabrication_status('238001','001')['fabricated'] is False
        assert classify.call_count==1
        for key, (_checked, result) in list(s._fabrication_cache.items()):
            s._fabrication_cache[key]=(time.monotonic()-s.cache_seconds-1,result)
        for kind, (_checked, assets) in list(s._cache.items()):
            s._cache[kind]=(time.time()-s.cache_seconds-1,assets)
        (s.roots['program']/'23800101.egl').write_text('done')
        refreshed=s.fabrication_status('238001','001')
        assert refreshed['fabricated'] is True and refreshed['retryAfterSeconds']==0
        assert classify.call_count==2


def test_manual_check_discovers_new_file_without_full_share_walk(tmp_path):
    s=service(tmp_path)
    with mock.patch.object(s,'machine_assignment',return_value=assigned()):
        assert s.fabrication_status('238001','001')['fabricated'] is False
        (s.roots['program']/'23800101.egl').write_text('done')
        with mock.patch.object(s,'_walk_root',side_effect=AssertionError('Unbounded share walk')):
            result=s.fabrication_status('238001','001',force_check=True)
        assert result['fabricated'] is True


def test_waterjet_completion_is_remembered_after_archival(tmp_path):
    s=service(tmp_path);s.roots['completed_wj'].mkdir()
    path=s.roots['completed_wj']/'23800101.nce';path.write_text('done')
    with mock.patch.object(s,'machine_assignment',return_value=assigned('waterjet')):
        assert s.fabrication_status('238001','001')['fabricated'] is True
        path.unlink();s.assets('completed_wj',refresh=True)
        status=s.fabrication_status('238001','001')
        assert status['fabricated'] is True and status['evidence']['historical'] is True
        assert s.fabrication_status('238001','001',force_check=True)['fabricated'] is True


def test_cached_bulk_reads_do_not_touch_the_share(tmp_path):
    s=service(tmp_path);(s.roots['program']/'23800101.egl').write_text('done')
    with mock.patch.object(s,'machine_assignment',return_value=assigned()):
        s.fabrication_status('238001','001')
    with mock.patch.object(s,'machine_assignment',side_effect=AssertionError('Unexpected classification')):
        start=time.perf_counter()
        for _ in range(1000): assert s.fabrication_status('238001','001')['fabricated'] is True
        assert time.perf_counter()-start < 1.0


def test_no_fabrication_piece_is_terminal_for_current_lifecycle(tmp_path):
    s = service(tmp_path)
    no_fab = {'machine': '', 'machineCode': '', 'required': False, 'confidence': 'label'}
    with mock.patch.object(s, 'machine_assignment', return_value=no_fab) as classify:
        first = s.fabrication_status('238001', '001', label_hint={'lifecycleRevision': 'original'})
        assert first['required'] is False
        assert first['retryAfterSeconds'] == 0
        # Server cache still permits source-revision invalidation, while the browser
        # receives a terminal retry value and stops polling this unchanged pane.
        second = s.fabrication_status('238001', '001', label_hint={'lifecycleRevision': 'original'})
        assert second['remembered'] is True
        assert classify.call_count == 1
        s.fabrication_status('238001', '001', label_hint={'lifecycleRevision': 'remake-1'})
        assert classify.call_count == 2
