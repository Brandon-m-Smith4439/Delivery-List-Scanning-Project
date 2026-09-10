# File: tests/test_sketch_recovery.py
"""Exact archived sketches and source-grounded reference geometry regressions."""
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
import json
import os
import time

from backend.config import load_config
from backend.production_files import ProductionFileService
from backend.sketch_geometry import read_reference_geometry


def service(tmp_path):
    cfg = replace(load_config(Path(__file__).resolve().parents[1]), root=tmp_path,
                  data_dir=tmp_path / 'data', sketches_dir=tmp_path / 'sketches',
                  programs_dir=tmp_path / 'programs', hardware_lists_dir=tmp_path / 'hardware',
                  completed_wj_dir=tmp_path / 'completed')
    cfg.data_dir.mkdir(exist_ok=True)
    cfg.sketches_dir.mkdir(exist_ok=True)
    cfg.programs_dir.mkdir(exist_ok=True)
    result = ProductionFileService(cfg)
    result._schedule_persist_index = mock.Mock()
    return result


def write_pdf(path, markers):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    for marker in markers:
        page = writer.add_blank_page(612, 792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject(); stream.set_data(f'BT /F1 14 Tf 20 700 Td ({marker}) Tj ET'.encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as output: writer.write(output)


def write_dxf(path, entities, units=1):
    path.write_text(f'0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n{units}\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n{entities}0\nENDSEC\n0\nEOF\n')


RECT = '0\nLWPOLYLINE\n70\n1\n10\n0\n20\n0\n10\n30\n20\n0\n10\n30\n20\n80\n10\n0\n20\n80\n'


def test_old_exact_pdf_survives_index_refresh_restart_and_share_failure(tmp_path):
    s = service(tmp_path)
    pdf = s.roots['sketch'] / '237763.pdf'
    write_pdf(pdf, ['Order overview', '237763.1 DENVER', '237763.2 WATERJET'])
    old = time.time() - 100 * 86400; os.utime(pdf, (old, old))
    assert s.assets('sketch') == []
    views = s.sketch_item_views('237763', '001')
    assert [(v['pageNumber'], v['itemMarker']) for v in views] == [(2, '237763.1')]
    assert s.sketch_item_views('237763', '002')[0]['pageNumber'] == 3
    assert not s.sketch_item_views('237763', '003')
    s._replace_kind_cache('sketch', [], True)
    assert s.resolve_asset(views[0]['id']) is not None
    s._persist_index()
    restarted = ProductionFileService(s.config)
    with mock.patch.object(Path, 'stat', side_effect=OSError('Share disconnected')):
        assert restarted.sketch_item_views('237763', '001')[0]['pageNumber'] == 2


def test_partial_pdf_recovers_and_newer_pdf_replaces_item_page(tmp_path):
    s = service(tmp_path); pdf = s.roots['sketch'] / '238001.pdf'
    pdf.write_bytes(b'')
    assert not s.sketch_item_views('238001', '001')
    write_pdf(pdf, ['238001.1 DENVER'])
    s._sketch_order_checked.clear()
    assert s.sketch_item_views('238001', '001')[0]['pageNumber'] == 1
    write_pdf(pdf, ['Cover', '238001.1 WATERJET'])
    os.utime(pdf, (time.time()+2, time.time()+2)); s._sketch_order_checked.clear()
    assert s.sketch_item_views('238001', '001')[0]['pageNumber'] == 2


def test_hot_fabrication_lookup_does_not_probe_exact_files(tmp_path):
    s = service(tmp_path)
    with mock.patch.object(s, '_exact_order_sketches', side_effect=AssertionError('Hot-path file probe')):
        s.machine_assignment('238001', '001', allow_content_read=False)


def test_reference_geometry_keeps_holes_and_uses_metric_units(tmp_path):
    p = tmp_path / 'metric.dxf'
    write_dxf(p, RECT + '0\nCIRCLE\n10\n10\n20\n20\n40\n2\n', units=4)
    geometry = read_reference_geometry(p)
    assert abs(geometry['width'] - 30 / 25.4) < 1e-9
    assert abs(geometry['height'] - 80 / 25.4) < 1e-9
    assert len(geometry['paths']) == 2
    assert geometry['paths'][0][0] == [0.0, round(80 / 25.4, 5)]


def test_curves_are_preserved_and_unknown_geometry_rejected(tmp_path):
    p = tmp_path / 'curves.dxf'
    write_dxf(p, '0\nLWPOLYLINE\n70\n1\n10\n0\n20\n0\n42\n1\n10\n20\n20\n0\n')
    assert len(read_reference_geometry(p)['paths'][0]) > 12
    write_dxf(p, RECT + '0\nSPLINE\n10\n5\n20\n5\n')
    assert read_reference_geometry(p) is None
    write_dxf(p, '0\nELLIPSE\n10\n0\n20\n0\n11\n20\n21\n0\n40\n0.5\n')
    result = read_reference_geometry(p)
    assert abs(result['width'] - 40) < .01 and abs(result['height'] - 20) < .01


def test_reference_lookup_requires_exact_item_and_fresh_unambiguous_source(tmp_path):
    s = service(tmp_path)
    wrong = s.roots['program'] / '23800110.dxf'; write_dxf(wrong, RECT)
    assert s.reference_geometry('238001','001') is None
    correct = s.roots['program'] / '23800101.dxf'; write_dxf(correct, RECT)
    s._reference_geometry_cache.clear()
    assert s.reference_geometry('238001','001')['source'] == correct.name
    future = datetime.fromtimestamp(time.time()+10, timezone.utc).isoformat()
    assert s.reference_geometry('238001','001',evidence_after=future) is None
    other = s.roots['program'] / '238001001.dxf'; write_dxf(other, RECT.replace('30\n','31\n'))
    s._reference_geometry_cache.clear()
    assert s.reference_geometry('238001','001') is None


def write_annotated_pdf(path, page_text, annotation_text):
    """Create one page whose operator markup lives in PDF annotation metadata."""
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        TextStringObject,
    )
    writer = PdfWriter()
    page = writer.add_blank_page(612, 792)
    font = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Helvetica'),
    })
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(f'BT /F1 14 Tf 20 700 Td ({page_text}) Tj ET'.encode())
    page[NameObject('/Contents')] = writer._add_object(stream)
    annotation = DictionaryObject({
        NameObject('/Type'): NameObject('/Annot'),
        NameObject('/Subtype'): NameObject('/Text'),
        NameObject('/Contents'): TextStringObject(annotation_text),
        NameObject('/Rect'): ArrayObject([FloatObject(20), FloatObject(620), FloatObject(60), FloatObject(660)]),
    })
    page[NameObject('/Annots')] = ArrayObject([writer._add_object(annotation)])
    with path.open('wb') as output:
        writer.write(output)


def test_manual_variant_sketch_annotation_can_assign_waterjet(tmp_path):
    s = service(tmp_path)
    pdf = s.roots['sketch'] / '238445 Mirror markup.pdf'
    write_annotated_pdf(pdf, 'ORDER 238445 ITEM 1', 'WATERJET - manual internal cutout')
    old = time.time() - 100 * 86400
    os.utime(pdf, (old, old))

    # The rolling index excludes this old sketch. Deferred exact-order lookup
    # still finds the human-suffixed filename and reads the manual annotation.
    assert s.assets('sketch') == []
    views = s.sketch_item_views('238445', '001')
    assert len(views) == 1
    assert views[0]['pageNumber'] == 1
    assert views[0]['machineHint'] == 'Waterjet'
    assignment = s.machine_assignment('238445', '001', allow_content_read=True)
    assert assignment['required'] is True
    assert assignment['machine'] == 'Waterjet'
    assert assignment['sketchMatched'] is True


def test_cutting_label_infers_mirror_cutout_and_generic_fabrication(tmp_path):
    s = service(tmp_path)
    mirror = s.machine_assignment(
        '238445', '001', allow_content_read=True,
        label_hint={
            'productDescription': '1/4 Mirror',
            'processRows': [{'processProductDescription': 'Internal Cutout Macro'}],
        },
    )
    assert mirror['required'] is True
    assert mirror['machine'] == 'Waterjet'
    assert mirror['confidence'] == 'label-mirror-cutout'

    # Mirror labels may name the topology rather than literally saying CUTOUT.
    mirror_slot = s.machine_assignment(
        '238445', '002', allow_content_read=True,
        label_hint={
            'productDescription': '1/4 Mirror',
            'processRows': [{'processProductDescription': 'BCU4 Slot MACRO'}],
        },
    )
    assert mirror_slot['required'] is True
    assert mirror_slot['machine'] == 'Waterjet'

    generic = s.machine_assignment(
        '238446', '001', allow_content_read=True,
        label_hint={
            'productDescription': '3/8 Clear Tempered',
            'processRows': [{'workType': 'Fabrication'}],
        },
    )
    assert generic['required'] is True
    assert generic['machine'] == 'Fabrication'
    assert generic['confidence'] == 'label-required'


def test_job_number_identity_finds_archived_sketch_and_machine_files(tmp_path):
    """Job Nr. is a bounded secondary production-file identity, not an Order-only fallback."""
    s = service(tmp_path)
    s.roots['completed_wj'].mkdir(parents=True, exist_ok=True)
    job = '89883882 RCM75'

    # The archived sketch is older than the rolling seven-day index and named by
    # Job Nr., while the page itself still carries the authoritative Order.Item.
    pdf = s.roots['sketch'] / '89883882 manually marked.pdf'
    write_pdf(pdf, ['Order overview', '238900.1 WATERJET'])
    old = time.time() - 100 * 86400
    os.utime(pdf, (old, old))
    assert s.assets('sketch') == []
    views = s.sketch_item_views('238900', '001', job)
    assert len(views) == 1
    assert views[0]['pageNumber'] == 2
    assert views[0]['name'] == pdf.name

    # Recent machine outputs sometimes use only the Job Nr. filename. These are
    # accepted for machine evidence while sketches still require page identity.
    program = s.roots['program'] / '89883882.egl'
    program.write_text('DENVER PROGRAM', encoding='utf-8')
    waterjet = s.roots['completed_wj'] / '89883882.nce'
    waterjet.write_text('WATERJET COMPLETE', encoding='utf-8')
    assert [asset.name for asset in s.matches('program', '238900', '001', job, require_item=True)] == [program.name]
    assert [asset.name for asset in s.matches('completed_wj', '238900', '001', job, require_item=True)] == [waterjet.name]
    assert not s.matches('program', '238900', '001', '89883883', require_item=True)
    assert not s.matches('completed_wj', '238900', '001', '89883883', require_item=True)



def test_v521_configurable_machine_definition_controls_detection_color_and_rank(tmp_path):
    s = service(tmp_path)
    s.configure({
        'machines': [
            {'code': 'denver', 'name': 'Denver CNC', 'terms': ['DENVER'], 'color': '#2563eb', 'progressRank': 0, 'active': True, 'completionKind': 'denver'},
            {'code': 'waterjet', 'name': 'WaterJet', 'terms': ['WATERJET'], 'color': '#7c3aed', 'progressRank': 0, 'active': True, 'completionKind': 'waterjet'},
            {'code': 'edge-polisher', 'name': 'Edge Polisher', 'terms': ['KODIAK POLISHER', 'EDGE POLISH'], 'color': '#118855', 'progressRank': -15, 'active': True, 'completionKind': 'custom'},
        ]
    })
    machines = {row['code']: row for row in s.settings_snapshot()['machines']}
    assert machines['edge-polisher']['name'] == 'Edge Polisher'
    assert machines['edge-polisher']['color'] == '#118855'
    assert machines['edge-polisher']['progressRank'] == -15
    assert s._detect_machine('Route note: KODIAK POLISHER required') == 'Edge Polisher'
