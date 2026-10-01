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



def test_refresh_missing_finds_later_completion_before_cache_expiry_v542(tmp_path):
    s = service(tmp_path)
    with mock.patch.object(s, 'machine_assignment', return_value=assigned()):
        first = s.fabrication_status('238001', '001')
        assert first['fabricated'] is False
        # Add completion while the negative fabrication cache is still fresh.
        # refresh_missing is the bounded current-day status-batch path and must
        # discover it without waiting for cache expiry.
        (s.roots['program'] / '23800101.egl').write_text('done')
        refreshed = s.fabrication_status('238001', '001', refresh_missing=True)
        assert refreshed['fabricated'] is True
        assert refreshed['retryAfterSeconds'] == 0


def test_v560_completed_floor_machine_overrides_opposite_sketch_assignment_both_directions(tmp_path):
    """Completed production evidence is operational truth even when the sketch names the other machine."""
    s = service(tmp_path)
    s.roots['completed_wj'].mkdir(parents=True, exist_ok=True)

    # Sketch says Waterjet, but the exact item exists in completed Denver output.
    pdf_wj = s.roots['sketch'] / '239301.pdf'
    from test_sketch_recovery import write_pdf
    write_pdf(pdf_wj, ['239301.1 WATERJET'])
    (s.roots['program'] / '23930101.egl').write_text('Denver complete', encoding='utf-8')

    pdf_denver = s.roots['sketch'] / '239302.pdf'
    write_pdf(pdf_denver, ['239302.1 DENVER 2'])
    (s.roots['completed_wj'] / '23930201.nce').write_text('Waterjet complete', encoding='utf-8')

    wj_to_denver = s.fabrication_status('239301', '001', known_items=['001'])
    assert wj_to_denver['assignedMachine'] == 'Waterjet'
    assert wj_to_denver['actualMachine'] == 'Denver CNC'
    assert wj_to_denver['actualMachineCode'] == 'denver'
    assert wj_to_denver['machineOverride'] is True
    assert wj_to_denver['fabricated'] is True

    # Sketch says Denver, but the exact item appears in completed Waterjet output.
    denver_to_wj = s.fabrication_status('239302', '001', known_items=['001'])
    assert denver_to_wj['assignedMachine'] == 'Denver CNC'
    assert denver_to_wj['actualMachine'] == 'Waterjet'
    assert denver_to_wj['actualMachineCode'] == 'waterjet'
    assert denver_to_wj['machineOverride'] is True
    assert denver_to_wj['fabricated'] is True


def test_v560_when_both_machine_completions_exist_newest_exact_file_wins(tmp_path):
    """A rerun on the other fabrication machine must become the displayed floor truth."""
    s = service(tmp_path)
    s.roots['completed_wj'].mkdir(parents=True, exist_ok=True)
    from test_sketch_recovery import write_pdf
    write_pdf(s.roots['sketch'] / '239303.pdf', ['239303.1 WATERJET'])

    denver = s.roots['program'] / '23930301.egl'
    waterjet = s.roots['completed_wj'] / '23930301.nce'
    denver.write_text('Denver complete', encoding='utf-8')
    waterjet.write_text('Waterjet rerun complete', encoding='utf-8')
    now = time.time()
    import os
    os.utime(denver, (now - 20, now - 20))
    os.utime(waterjet, (now - 5, now - 5))

    status = s.fabrication_status('239303', '001', known_items=['001'])
    assert status['assignedMachine'] == 'Waterjet'
    assert status['actualMachine'] == 'Waterjet'
    assert status['evidence']['name'] == waterjet.name
    assert status['fabricated'] is True

    # A later Denver rerun supersedes the earlier Waterjet completion.
    os.utime(denver, (now + 5, now + 5))
    s.assets('program', refresh=True)
    status = s.fabrication_status('239303', '001', known_items=['001'], force_check=True)
    assert status['actualMachine'] == 'Denver CNC'
    assert status['machineOverride'] is True
    assert status['evidence']['name'] == denver.name


def test_v563_sole_scanner_item_accepts_denver_program_numbered_like_physical_sketch_page(tmp_path):
    """239197-style orders may have one scanner item but a Denver program suffix matching page 2."""
    s = service(tmp_path)
    from test_sketch_recovery import write_pdf

    write_pdf(s.roots['sketch'] / '239197.pdf', ['239197.1 Fabrication', '239197.2 DENVER 2'])
    denver = s.roots['program'] / '23919702.egl'
    denver.write_text('Denver completion for physical panel/page 2', encoding='utf-8')

    status = s.fabrication_status('239197', '001', known_items=['001'])
    assert status['assignedMachine'] == 'Denver CNC'
    assert status['actualMachine'] == 'Denver CNC'
    assert status['actualMachineCode'] == 'denver'
    assert status['fabricated'] is True
    assert status['evidence']['name'] == denver.name
    assert status['evidence']['soleItemInferred'] is True
    assert [row['name'] for row in status['programs']] == [denver.name]
    assert status['programs'][0]['soleItemInferred'] is True

    item_assets = s.item_assets('239197', '001', known_items=['001'])
    assert [row['name'] for row in item_assets['programs']] == [denver.name]
    assert item_assets['programs'][0]['soleItemInferred'] is True


def test_v563_physical_page_program_fallback_never_crosses_multi_item_order(tmp_path):
    """A page-2 Denver file cannot satisfy Item 001 when Item 002 is a real scanner item."""
    s = service(tmp_path)
    denver = s.roots['program'] / '23919702.egl'
    denver.write_text('Denver completion for item 2', encoding='utf-8')

    with mock.patch.object(s, 'machine_assignment', return_value=assigned('denver')):
        status = s.fabrication_status('239197', '001', known_items=['001', '002'])
    assert status['fabricated'] is False
    assert status['actualMachine'] == ''
    assert status['programs'] == []


def test_v563_newest_sole_item_floor_completion_beats_older_exact_opposite_machine(tmp_path):
    """Physical-page Denver reruns remain floor truth even when Waterjet used the scanner item suffix."""
    s = service(tmp_path)
    s.roots['completed_wj'].mkdir(parents=True, exist_ok=True)
    from test_sketch_recovery import write_pdf

    write_pdf(s.roots['sketch'] / '239197.pdf', ['239197.1 Fabrication', '239197.2 DENVER 2'])
    waterjet = s.roots['completed_wj'] / '23919701.nce'
    denver = s.roots['program'] / '23919702.egl'
    waterjet.write_text('older Waterjet completion', encoding='utf-8')
    denver.write_text('newer Denver rerun', encoding='utf-8')
    now = time.time()
    import os
    os.utime(waterjet, (now - 30, now - 30))
    os.utime(denver, (now - 5, now - 5))

    status = s.fabrication_status('239197', '001', known_items=['001'])
    assert status['actualMachine'] == 'Denver CNC'
    assert status['actualMachineCode'] == 'denver'
    assert status['fabricated'] is True
    assert status['evidence']['name'] == denver.name
    assert status['evidence']['soleItemInferred'] is True


def test_v564_order_details_auto_probe_finds_denver_file_created_after_stale_index(tmp_path):
    """Order Details must not wait for the rolling Programs index to notice a new Denver file."""
    s = service(tmp_path)
    from test_sketch_recovery import write_pdf

    write_pdf(s.roots['sketch'] / '239197.pdf', ['239197.1 Fabrication', '239197.2 DENVER 2'])
    # Prime an empty Programs cache first; this reproduces the live case where
    # the .egl exists after the rolling production index snapshot was built.
    assert s.assets('program', refresh=True) == []
    assert s.assets('sketch', refresh=True)
    denver = s.roots['program'] / '23919702.egl'
    denver.write_text('Denver completion for physical panel/page 2', encoding='utf-8')

    with mock.patch.object(s, '_walk_root', side_effect=AssertionError('Order Details must use bounded targeted probing')):
        assets = s.item_assets('239197', '001', known_items=['001'])

    status = assets['fabrication']
    assert status['assignedMachine'] == 'Denver CNC'
    assert status['actualMachine'] == 'Denver CNC'
    assert status['fabricated'] is True
    assert status['evidence']['name'] == denver.name
    assert [row['name'] for row in assets['programs']] == [denver.name]


def test_v564_targeted_probe_supports_order_folder_with_physical_page_filename(tmp_path):
    """Programs/239197/02.egl is valid sole-item page-2 Denver evidence without a full share walk."""
    s = service(tmp_path)
    from test_sketch_recovery import write_pdf

    write_pdf(s.roots['sketch'] / '239197.pdf', ['239197.1 Fabrication', '239197.2 DENVER 2'])
    assert s.assets('program', refresh=True) == []
    assert s.assets('sketch', refresh=True)
    order_folder = s.roots['program'] / '239197'
    order_folder.mkdir(parents=True)
    denver = order_folder / '02.egl'
    denver.write_text('Denver completion in order folder', encoding='utf-8')

    with mock.patch.object(s, '_walk_root', side_effect=AssertionError('Targeted probe must stay bounded')):
        assets = s.item_assets('239197', '001', known_items=['001'])

    status = assets['fabrication']
    assert status['actualMachineCode'] == 'denver'
    assert status['fabricated'] is True
    assert status['evidence']['name'] == denver.name
    assert status['evidence']['relativePath'] == '239197/02.egl'
    assert status['evidence']['soleItemInferred'] is True


def test_v564_targeted_order_folder_probe_remains_strict_for_multi_item_orders(tmp_path):
    """A page-2 file under the order folder cannot complete Item 001 when Item 002 really exists."""
    s = service(tmp_path)
    order_folder = s.roots['program'] / '239197'
    order_folder.mkdir(parents=True)
    (order_folder / '02.egl').write_text('Denver completion for physical item 2', encoding='utf-8')

    with mock.patch.object(s, 'machine_assignment', return_value=assigned('denver')):
        result = s.fabrication_status('239197', '001', known_items=['001', '002'], force_check=True)
    assert result['fabricated'] is False
    assert result['evidence'] is None
    assert result['programs'] == []
