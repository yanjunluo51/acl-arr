"""Local PDF checks; PyMuPDF is needed only for this submission QA script."""
from pathlib import Path
import json
import re
import fitz

ROOT = Path(__file__).resolve().parents[1]

def main():
    doc = fitz.open(ROOT / 'paper/main.pdf')
    contents = [p.get_text() for p in doc]
    text = '\n'.join(contents)
    limitations = next(i + 1 for i, t in enumerate(contents) if '\nLimitations\n' in t)
    references = next(i + 1 for i, t in enumerate(contents) if '\nReferences\n' in t)
    lp=doc[limitations-1]
    spans=[s for b in lp.get_text('dict')['blocks'] for line in b.get('lines',[]) for s in line['spans']]
    heading=next(s for s in spans if s['text'].strip()=='Limitations')
    before=[s for s in spans if s['color']==0 and s['bbox'][3]<=heading['bbox'][1] and s['text'].strip() and not s['text'].strip().isdigit()]
    main_end=limitations if before else limitations-1
    assert main_end <= 8, 'Main content exceeds eight pages'
    assert 'Anonymous ACL submission' in contents[0]
    assert doc.metadata.get('author', '') == ''
    assert '??' not in text
    assert re.search(r'/(?:Users|home)/[^/\s]+', text) is None
    log = (ROOT / 'paper/main.log').read_text(errors='replace')
    assert 'Overfull' not in log
    assert 'undefined' not in log
    fonts = []
    for pg in doc:
        for f in pg.get_fonts():
            assert f[2] != 'Type3', f
            assert len(doc.extract_font(f[0])[3]) > 0, f
            fonts.append({'name':f[3], 'type':f[2]})
    collisions = []
    outside_body = []
    for page_i, pg in enumerate(doc):
        black = []
        numbers = []
        for block in pg.get_text('rawdict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    chars = span['chars']
                    if span['color'] == 0:
                        for c in chars:
                            if c['c'].strip():
                                rect = fitz.Rect(c['bbox'])
                                black.append(rect)
                                # Three points permit ordinary optical hanging.
                                if rect.x0 < 70.866-3 or rect.x1 > pg.rect.width-70.866+3:
                                    outside_body.append([page_i+1, c['c'], list(rect)])
                    elif ''.join(c['c'] for c in chars).isdigit():
                        numbers.extend(fitz.Rect(c['bbox']) for c in chars)
        for n in numbers:
            if any(n.intersects(c) for c in black):
                collisions.append([page_i+1, list(n)])
    assert not collisions, collisions[:3]
    assert not outside_body, outside_body[:3]
    out = {'status':'PASS_SCOPED_PDF_CHECKS', 'total_pages':len(doc),
           'main_content_ends_on_page':main_end,
           'limitations_start_page':limitations, 'references_start_page':references,
           'fonts_embedded':True, 'type3_fonts':False,
           'line_number_character_collisions':len(collisions),
           'body_characters_outside_horizontal_margins_with_3pt_tolerance':len(outside_body),
           'no_overfull_or_undefined_references':True,
           'author_metadata_empty':True,
           'scope':'Build, text, fonts, anonymous identifiers and horizontal bounds; visual review also required.'}
    (ROOT / 'submission').mkdir(exist_ok=True)
    (ROOT / 'submission/pdf-check.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
