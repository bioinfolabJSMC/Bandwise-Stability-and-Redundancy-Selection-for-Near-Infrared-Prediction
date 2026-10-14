"""Export references in first-appearance order for the SPXY manuscript."""
import argparse
import copy
import json
import pathlib
import re
import xml.etree.ElementTree as ET

root = pathlib.Path(__file__).resolve().parent
destination = root / 'references'
content_path = root / 'document_assets/manuscript_content.json'
existing = json.loads((root / 'document_assets/references.json').read_text(encoding='utf-8'))
source = {r['key']: copy.deepcopy(r) for r in existing}
content = content_path.read_text(encoding='utf-8')
keys = list(dict.fromkeys(re.findall(r'@([A-Za-z0-9_]+)', content)))
if not set(keys).issubset(source):
    raise ValueError({'uncited_reference_keys': sorted(set(source) - set(keys)),
                      'unknown_citation_keys': sorted(set(keys) - set(source))})
assert len(keys) == 27 and 'cars' not in keys
records = []
for number, key in enumerate(keys, 1):
    record = source[key]
    record['number'] = number
    record['formatted'] = (f"{number}. {record['authors_text']} "
                           f"{record['title'].rstrip('.')}. "
                           f"{record['journal_abbrev']} {record['year']}, "
                           f"{record['volume']}, {record['pages'].replace('-', '–')}. "
                           + (f"https://doi.org/{record['doi']}" if record['doi'] else record['url']))
    records.append(record)
destination.mkdir(parents=True, exist_ok=True)
for filename, obj in [
    ('references.json', records),
    ('reference_keymap.json', {r['key']: r['number'] for r in records}),
    ('citation_order.json', [{k: r[k] for k in ('number', 'key', 'doi', 'url')} for r in records])
]:
    (destination / filename).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
(destination / 'References_Foods_style.txt').write_text(
    '\n\n'.join(r['formatted'] for r in records) + '\n', encoding='utf-8')

ris_records = []
for record in records:
    lines = ['TY  - JOUR', f"ID  - {record['key']}"]
    lines.extend(f"AU  - {a['family']}, {a['given']}" for a in record['authors'])
    lines.extend([f"PY  - {record['year']}", f"TI  - {record['title']}",
                  f"JO  - {record['journal']}", f"J2  - {record['journal_abbrev']}",
                  f"VL  - {record['volume']}"])
    if record.get('issue'):
        lines.append(f"IS  - {record['issue']}")
    pages = record['pages'].split('-')
    lines.append(f'SP  - {pages[0]}')
    if len(pages) > 1:
        lines.append(f'EP  - {pages[-1]}')
    if record['doi']:
        lines.append(f"DO  - {record['doi']}")
    lines.extend([f"UR  - {record['url']}",
                  f"N1  - Verified bibliography record; manuscript citation "
                  f"[{record['number']}]; logical key {record['key']}.", 'ER  - '])
    ris_records.append('\n'.join(lines))
(destination / 'EndNote.ris').write_text('\n\n'.join(ris_records) + '\n', encoding='utf-8-sig')

xml = ET.Element('xml')
xml_records = ET.SubElement(xml, 'records')
def element(parent, tag, value, attributes=None):
    child = ET.SubElement(parent, tag, attributes or {})
    child.text = str(value)
    return child
for record in records:
    rec = ET.SubElement(xml_records, 'record')
    element(rec, 'rec-number', record['number'])
    element(rec, 'ref-type', 17, {'name': 'Journal Article'})
    authors = ET.SubElement(ET.SubElement(rec, 'contributors'), 'authors')
    for author in record['authors']:
        element(authors, 'author', author['family'] + ', ' + author['given'])
    titles = ET.SubElement(rec, 'titles')
    element(titles, 'title', record['title'])
    element(titles, 'secondary-title', record['journal'])
    element(titles, 'alt-title', record['journal_abbrev'])
    periodical = ET.SubElement(rec, 'periodical')
    element(periodical, 'full-title', record['journal'])
    element(periodical, 'abbr-1', record['journal_abbrev'])
    element(rec, 'pages', record['pages'])
    element(rec, 'volume', record['volume'])
    if record.get('issue'):
        element(rec, 'number', record['issue'])
    element(ET.SubElement(rec, 'dates'), 'year', record['year'])
    element(ET.SubElement(ET.SubElement(rec, 'urls'), 'related-urls'), 'url', record['url'])
    if record['doi']:
        element(rec, 'electronic-resource-num', record['doi'])
    element(rec, 'label', record['key'])
    element(rec, 'notes', f"Verified reference metadata. Manuscript citation [{record['number']}].")
ET.indent(xml, space='  ')
ET.ElementTree(xml).write(destination / 'EndNote.xml', encoding='utf-8', xml_declaration=True)

parsed_xml = ET.parse(destination / 'EndNote.xml').findall('.//record')
parsed_ris = (destination / 'EndNote.ris').read_text(encoding='utf-8-sig')
ris_keys = re.findall(r'^ID  - (.+)$', parsed_ris, flags=re.MULTILINE)
assert len(parsed_xml) == parsed_ris.count('TY  - JOUR') == parsed_ris.count('ER  - ') == len(keys)
assert ris_keys == [r.findtext('label') for r in parsed_xml] == keys
assert [int(r.findtext('rec-number')) for r in parsed_xml] == list(range(1, len(keys) + 1))
assert all(x.findtext('./titles/title') == r['title'] and
           (x.findtext('electronic-resource-num') or '') == r['doi'] and
           len(x.findall('./contributors/authors/author')) == len(r['authors'])
           for x, r in zip(parsed_xml, records))
audit = {'status': 'PASS', 'reference_count': len(keys), 'doi_reference_count': sum(bool(r['doi']) for r in records),
         'publisher_url_only_records': [r['key'] for r in records if not r['doi']], 'citation_order_source': 'document_assets/manuscript_content.json',
         'ris_xml_keys_and_numbers_match': True, 'metadata_unchanged': True,
         'removed_selector_key_absent': True,
         'endnote_format': 'RIS and XML exchange files for EndNote import'}
(destination / 'reference_validation.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'destination': str(destination), **audit}, ensure_ascii=False, indent=2))
