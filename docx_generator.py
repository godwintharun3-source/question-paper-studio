import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_ORIENTATION
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=50, bottom=50, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def generate_docx(paper_data, output_path, img_dir):
    doc = docx.Document()
    
    pages = paper_data.get('pages', [])
    header_config = paper_data.get('header', {})
    footer_config = paper_data.get('footer', {})
    styling = paper_data.get('styling', {})
    
    page_size = styling.get('page_size', 'A4')
    orientation = styling.get('orientation', 'portrait').lower()
    
    PAGE_DIMENSIONS_DOCX = {
        'A4': (Inches(8.27), Inches(11.69)),
        'A3': (Inches(11.69), Inches(16.54)),
        'Letter': (Inches(8.5), Inches(11.0)),
        'Legal': (Inches(8.5), Inches(14.0)),
        'A5': (Inches(5.83), Inches(8.27))
    }
    base_w, base_h = PAGE_DIMENSIONS_DOCX.get(page_size, (Inches(8.27), Inches(11.69)))
    
    # Set page margins & orientation
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.4)
        section.bottom_margin = Inches(0.4)
        section.left_margin = Inches(0.4)
        section.right_margin = Inches(0.4)
        section.different_first_page_header_footer = True
        if orientation == 'landscape':
            section.orientation = WD_ORIENTATION.LANDSCAPE
            section.page_width = base_h
            section.page_height = base_w
        else:
            section.orientation = WD_ORIENTATION.PORTRAIT
            section.page_width = base_w
            section.page_height = base_h

        if styling.get('page_border', False):
            try:
                pgBorders = parse_xml(r'<w:pgBorders %s><w:top w:val="single" w:sz="12" w:space="24" w:color="auto"/><w:left w:val="single" w:sz="12" w:space="24" w:color="auto"/><w:bottom w:val="single" w:sz="12" w:space="24" w:color="auto"/><w:right w:val="single" w:sz="12" w:space="24" w:color="auto"/></w:pgBorders>' % nsdecls('w'))
                section._sectPr.append(pgBorders)
            except Exception:
                pass
    
    q_font_size = styling.get('q_font_size', 11)
    opt_font_size = styling.get('opt_font_size', 9.5)
    language_mode = styling.get('language_mode', 'bilingual')
    
    total_page_w = base_h if orientation == 'landscape' else base_w
    printable_w = total_page_w - Inches(0.8)
    img_cell_w = Inches(1.8)
    text_cell_w = printable_w - img_cell_w
    opt_cell_w = printable_w / 2

    for page_idx, page_questions in enumerate(pages):
        is_formal = styling.get('page_border', False) or header_config.get('include_instructions', False) or styling.get('show_marks_table', False)

        # Header (if enabled)
        if header_config.get('enabled', True):
            show_header = (page_idx == 0) if header_config.get('page1_only', True) else True
            inst_text = header_config.get('inst_name', 'FITTER, GITI.,VEERAKERLAMPUDUR.')
            title_text = header_config.get('test_title', 'MONTHLY TEST - FIRST YEAR')
            session_text = header_config.get('session_text', '')
            date_text = header_config.get('date_text', 'Date: ____________________')
            time_text = header_config.get('time_text', 'Time: ____________________')
            reg_no_text = header_config.get('reg_no_text', 'Register No.: ____________________')
            marks_text = header_config.get('marks_text', 'Maximum Marks: 50')

            if show_header and is_formal:
                # Institution
                p_inst = doc.add_paragraph()
                p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_inst.paragraph_format.space_before = Pt(0)
                p_inst.paragraph_format.space_after = Pt(1)
                r_inst = p_inst.add_run(inst_text)
                r_inst.bold = True
                r_inst.font.size = Pt(13)
                r_inst.font.name = 'Arial'

                # Test Title
                p_title = doc.add_paragraph()
                p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_title.paragraph_format.space_before = Pt(0)
                p_title.paragraph_format.space_after = Pt(1)
                r_title = p_title.add_run(title_text)
                r_title.bold = True
                r_title.font.size = Pt(11)
                r_title.font.name = 'Arial'

                if session_text:
                    p_sess = doc.add_paragraph()
                    p_sess.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_sess.paragraph_format.space_before = Pt(0)
                    p_sess.paragraph_format.space_after = Pt(2)
                    r_sess = p_sess.add_run(session_text)
                    r_sess.bold = True
                    r_sess.font.size = Pt(10)
                    r_sess.font.name = 'Arial'

                # 2x2 Metadata Table
                meta_tbl = doc.add_table(rows=2, cols=2)
                meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                meta_tbl.autofit = False
                half_w = printable_w / 2
                for row in meta_tbl.rows:
                    row.cells[0].width = half_w
                    row.cells[1].width = half_w

                p00 = meta_tbl.cell(0, 0).paragraphs[0]
                p00.paragraph_format.space_after = Pt(1)
                r00 = p00.add_run(date_text)
                r00.bold = True
                r00.font.size = Pt(9.5)
                r00.font.name = 'Arial'

                p01 = meta_tbl.cell(0, 1).paragraphs[0]
                p01.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p01.paragraph_format.space_after = Pt(1)
                r01 = p01.add_run(time_text)
                r01.bold = True
                r01.font.size = Pt(9.5)
                r01.font.name = 'Arial'

                p10 = meta_tbl.cell(1, 0).paragraphs[0]
                p10.paragraph_format.space_after = Pt(1)
                r10 = p10.add_run(reg_no_text)
                r10.bold = True
                r10.font.size = Pt(9.5)
                r10.font.name = 'Arial'

                p11 = meta_tbl.cell(1, 1).paragraphs[0]
                p11.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p11.paragraph_format.space_after = Pt(1)
                r11 = p11.add_run(marks_text)
                r11.bold = True
                r11.font.size = Pt(9.5)
                r11.font.name = 'Arial'

                # Solid divider line
                p_div = doc.add_paragraph()
                p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_div.paragraph_format.space_before = Pt(1)
                p_div.paragraph_format.space_after = Pt(4)
                r_div = p_div.add_run("—" * 58)
                r_div.font.size = Pt(8)
                r_div.font.color.rgb = RGBColor(60, 60, 60)

                # General Instructions
                if header_config.get('include_instructions', False):
                    p_ins_h = doc.add_paragraph()
                    p_ins_h.paragraph_format.space_before = Pt(2)
                    p_ins_h.paragraph_format.space_after = Pt(1)
                    r_ins_h = p_ins_h.add_run("GENERAL INSTRUCTIONS")
                    r_ins_h.bold = True
                    r_ins_h.font.size = Pt(9.5)
                    r_ins_h.font.name = 'Arial'

                    for ins in header_config.get('instructions', []):
                        p_ins = doc.add_paragraph()
                        p_ins.paragraph_format.space_before = Pt(0)
                        p_ins.paragraph_format.space_after = Pt(0.5)
                        r_ins = p_ins.add_run(ins)
                        r_ins.font.size = Pt(8.5)
                        r_ins.font.name = 'Arial'

                # Part A banner
                if header_config.get('part_a_title'):
                    p_pa_h = doc.add_paragraph()
                    p_pa_h.paragraph_format.space_before = Pt(3)
                    p_pa_h.paragraph_format.space_after = Pt(0.5)
                    r_pa_h = p_pa_h.add_run(header_config.get('part_a_title'))
                    r_pa_h.bold = True
                    r_pa_h.font.size = Pt(9.5)
                    r_pa_h.font.name = 'Arial'

                    p_pa_s = doc.add_paragraph()
                    p_pa_s.paragraph_format.space_before = Pt(0)
                    p_pa_s.paragraph_format.space_after = Pt(3)
                    r_pa_s = p_pa_s.add_run(header_config.get('part_a_subtitle', ''))
                    r_pa_s.font.size = Pt(8.5)
                    r_pa_s.font.name = 'Arial'

            elif show_header:
                # Institution
                p_inst = doc.add_paragraph()
                p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_inst.paragraph_format.space_before = Pt(0)
                p_inst.paragraph_format.space_after = Pt(2)
                r_inst = p_inst.add_run(inst_text)
                r_inst.bold = True
                r_inst.font.size = Pt(13)
                r_inst.font.name = 'Arial'

                # Test Title
                p_title = doc.add_paragraph()
                p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_title.paragraph_format.space_before = Pt(0)
                p_title.paragraph_format.space_after = Pt(4)
                r_title = p_title.add_run(title_text)
                r_title.bold = True
                r_title.font.size = Pt(11.5)
                r_title.font.name = 'Arial'

                # Meta row (Date, Trade, Marks)
                meta_table = doc.add_table(rows=1, cols=3)
                meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                meta_table.autofit = False
                for row in meta_table.rows:
                    row.cells[0].width = Inches(2.5)
                    row.cells[1].width = Inches(2.7)
                    row.cells[2].width = Inches(2.3)
                    
                    p0 = row.cells[0].paragraphs[0]
                    p0.paragraph_format.space_after = Pt(2)
                    r0 = p0.add_run(date_text)
                    r0.bold = True
                    r0.font.size = Pt(10)
                    r0.font.name = 'Arial'
                    
                    p1 = row.cells[1].paragraphs[0]
                    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p1.paragraph_format.space_after = Pt(2)
                    r1 = p1.add_run(header_config.get('trade_text', 'TRADE: FITTER (1st SEM)'))
                    r1.bold = True
                    r1.font.size = Pt(10)
                    r1.font.name = 'Arial'

                    p2 = row.cells[2].paragraphs[0]
                    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    p2.paragraph_format.space_after = Pt(2)
                    r2 = p2.add_run(marks_text)
                    r2.bold = True
                    r2.font.size = Pt(10)
                    r2.font.name = 'Arial'

                # Divider Line
                p_div = doc.add_paragraph()
                p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_div.paragraph_format.space_before = Pt(2)
                p_div.paragraph_format.space_after = Pt(6)
                r_div = p_div.add_run("=" * 80)
                r_div.bold = True
                r_div.font.size = Pt(8.5)
                r_div.font.name = 'Courier New'

            elif is_formal:
                # Condensed header for subsequent pages
                p_inst = doc.add_paragraph()
                p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_inst.paragraph_format.space_before = Pt(0)
                p_inst.paragraph_format.space_after = Pt(1)
                r_inst = p_inst.add_run(inst_text)
                r_inst.bold = True
                r_inst.font.size = Pt(11.5)
                r_inst.font.name = 'Arial'

                session_sub = f" | {session_text}" if session_text else ""
                p_sub = doc.add_paragraph()
                p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_sub.paragraph_format.space_before = Pt(0)
                p_sub.paragraph_format.space_after = Pt(1)
                r_sub = p_sub.add_run(f"{title_text}{session_sub}")
                r_sub.bold = True
                r_sub.font.size = Pt(10)
                r_sub.font.name = 'Arial'

                p_m = doc.add_paragraph()
                p_m.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_m.paragraph_format.space_before = Pt(0)
                p_m.paragraph_format.space_after = Pt(2)
                r_m = p_m.add_run(marks_text)
                r_m.bold = True
                r_m.font.size = Pt(9.5)
                r_m.font.name = 'Arial'

                p_div = doc.add_paragraph()
                p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_div.paragraph_format.space_before = Pt(1)
                p_div.paragraph_format.space_after = Pt(4)
                r_rule = p_div.add_run("—" * 58)
                r_rule.font.size = Pt(8)
                r_rule.font.color.rgb = RGBColor(60, 60, 60)

        # Special conditions / Instructions if page 1
        if page_idx == 0 and styling.get('conditions_text'):
            p_cond = doc.add_paragraph()
            p_cond.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p_cond.paragraph_format.space_before = Pt(2)
            p_cond.paragraph_format.space_after = Pt(4)
            r_cond = p_cond.add_run(f"Note: {styling['conditions_text']}")
            r_cond.italic = True
            r_cond.font.size = Pt(9.5)
            r_cond.font.name = 'Arial'

        # Questions for this page
        import re
        start_num = sum(len(p) for p in pages[:page_idx]) + 1
        current_subheading = None
        for q_idx, q in enumerate(page_questions):
            curr_q_num = start_num + q_idx
            q_en_raw = str(q.get('q_en', '')).strip()
            q_ta_raw = str(q.get('q_ta', '')).strip()

            if '|' in q_en_raw:
                parts = q_en_raw.split('|', 1)
                q_en_raw = parts[0].strip()
                if not q_ta_raw or q_ta_raw.strip().lower() == str(q.get('q_en', '')).strip().lower() or '|' in q_ta_raw:
                    q_ta_raw = parts[1].strip()
            elif '|' in q_ta_raw:
                parts = q_ta_raw.split('|', 1)
                if not q_en_raw:
                    q_en_raw = parts[0].strip()
                q_ta_raw = parts[1].strip()

            q_en_raw = q_en_raw.replace('|', ' ').strip()
            q_ta_raw = q_ta_raw.replace('|', ' ').strip()

            if not q_ta_raw:
                m_tam = re.search(r'[\u0B80-\u0BFF]', q_en_raw)
                if m_tam:
                    q_ta_raw = q_en_raw[m_tam.start():].strip()
                    q_en_raw = q_en_raw[:m_tam.start()].strip()

            def _clean_stem_docx(text):
                if not text:
                    return ""
                t = str(text).strip()
                while True:
                    p = t
                    t = re.sub(r'^\s*(?:Question|Ques|Qn|Q)\s*\.?\s*\d+\s*[\.\:\-\)\s]*', '', t, flags=re.I)
                    t = re.sub(r'^\s*\d+\s*[\.\)\:\-]+\s*', '', t)
                    t = re.sub(r'^[\|\:\-\.\s]+', '', t).strip()
                    if t == p:
                        break
                return t.strip()

            q_en_clean = _clean_stem_docx(q_en_raw)
            q_ta_clean = _clean_stem_docx(q_ta_raw)

            if q_ta_clean and q_en_clean and q_ta_clean.lower().startswith(q_en_clean.lower()):
                q_ta_clean = q_ta_clean[len(q_en_clean):].strip()
                q_ta_clean = _clean_stem_docx(q_ta_clean)

            if q_ta_clean.lower() == q_en_clean.lower():
                q_ta_clean = ''
            elif not re.search(r'[\u0B80-\u0BFF]', q_ta_clean) and not re.search(r'[\u0B80-\u0BFF]', q_en_clean):
                if q_ta_clean.lower() in q_en_clean.lower():
                    q_ta_clean = ''
                elif q_en_clean.lower() in q_ta_clean.lower():
                    q_en_clean = q_ta_clean
                    q_ta_clean = ''

            if not q_en_clean and q_ta_clean:
                q_en_clean = q_ta_clean
                q_ta_clean = ''

            if re.match(r'^(?:Question\s*\d+|\d+)$', q_en_clean, re.I) or len(q_en_clean) <= 3:
                if q_ta_clean and re.search(r'[\u0B80-\u0BFF]', q_ta_clean):
                    q_en_clean = q_ta_clean
                    q_ta_clean = ''
                else:
                    q_en_clean = ''

            # Subheading banner if subheading changes
            subheading = q.get('subheading')
            if subheading and subheading != current_subheading and str(subheading).lower() not in ["general", "none", ""]:
                current_subheading = subheading
                p_sub = doc.add_paragraph()
                p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_sub.paragraph_format.space_before = Pt(6)
                p_sub.paragraph_format.space_after = Pt(4)
                r_sub = p_sub.add_run(f"-- {subheading.upper()} --")
                r_sub.bold = True
                r_sub.font.size = Pt(q_font_size - 0.5)
                r_sub.font.name = 'Arial'
            
            # Question table: 2 columns if image exists, or 1 column if no image
            has_img = q.get('has_img') and q.get('img_file')
            img_path = os.path.join(img_dir, q.get('img_file', '')) if has_img else None
            if img_path and not os.path.exists(img_path):
                for alt_dir in [
                    '/Users/tharungodwin/Downloads/question_paper_app/question_banks/extracted_imgs',
                    '/Users/tharungodwin/Downloads/question/extracted_imgs'
                ]:
                    alt_p = os.path.join(alt_dir, q.get('img_file', ''))
                    if os.path.exists(alt_p):
                        img_path = alt_p
                        break
            
            if has_img and img_path and os.path.exists(img_path):
                q_table = doc.add_table(rows=1, cols=2)
                q_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                q_table.autofit = False
                row = q_table.rows[0]
                row.cells[0].width = text_cell_w
                row.cells[1].width = img_cell_w
                
                # Question text
                p_q = row.cells[0].paragraphs[0]
                p_q.paragraph_format.space_after = Pt(1)
                r_num = p_q.add_run(f"{curr_q_num}. ")
                r_num.bold = True
                r_num.font.size = Pt(q_font_size)
                r_num.font.name = 'Arial'
                
                r_en = p_q.add_run(q_en_clean)
                r_en.bold = True
                r_en.font.size = Pt(q_font_size)
                r_en.font.name = 'Arial'
                
                if language_mode != 'english_only' and q_ta_clean and q_ta_clean.lower() != q_en_clean.lower():
                    p_ta = row.cells[0].add_paragraph()
                    p_ta.paragraph_format.space_after = Pt(2)
                    p_ta.paragraph_format.left_indent = Inches(0.25)
                    r_ta = p_ta.add_run(q_ta_clean)
                    r_ta.font.size = Pt(q_font_size - 1)
                    r_ta.font.name = 'Arial'
                
                # Image in cell 1
                p_img = row.cells[1].paragraphs[0]
                p_img.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                p_img.paragraph_format.space_after = Pt(0)
                try:
                    p_img.add_run().add_picture(img_path, width=Inches(1.5))
                except Exception:
                    pass
            else:
                p_q = doc.add_paragraph()
                p_q.paragraph_format.space_before = Pt(3)
                p_q.paragraph_format.space_after = Pt(1)
                r_num = p_q.add_run(f"{curr_q_num}. ")
                r_num.bold = True
                r_num.font.size = Pt(q_font_size)
                r_num.font.name = 'Arial'
                
                r_en = p_q.add_run(q_en_clean)
                r_en.bold = True
                r_en.font.size = Pt(q_font_size)
                r_en.font.name = 'Arial'
                
                if language_mode != 'english_only' and q_ta_clean and q_ta_clean.lower() != q_en_clean.lower():
                    p_ta = doc.add_paragraph()
                    p_ta.paragraph_format.space_after = Pt(2)
                    p_ta.paragraph_format.left_indent = Inches(0.25)
                    r_ta = p_ta.add_run(q_ta_clean)
                    r_ta.font.size = Pt(q_font_size - 1)
                    r_ta.font.name = 'Arial'

            # Options table (2x2 grid)
            opts = q.get('options', [])
            valid_opts = [o for o in opts if o.get('en') or o.get('ta')]
            if valid_opts:
                opt_table = doc.add_table(rows=2, cols=2)
                opt_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                opt_table.autofit = False
                
                # Map A, B, C, D
                opt_dict = {o['opt']: o for o in valid_opts}
                col_pairs = [('A', 'B'), ('C', 'D')]
                for r_i, (opt1, opt2) in enumerate(col_pairs):
                    row = opt_table.rows[r_i]
                    row.cells[0].width = opt_cell_w
                    row.cells[1].width = opt_cell_w
                    set_cell_margins(row.cells[0], top=20, bottom=20, left=40, right=40)
                    set_cell_margins(row.cells[1], top=20, bottom=20, left=40, right=40)
                    
                    if opt1 in opt_dict:
                        o = opt_dict[opt1]
                        p = row.cells[0].paragraphs[0]
                        p.paragraph_format.space_after = Pt(1)
                        p.paragraph_format.left_indent = Inches(0.25)
                        r_lbl = p.add_run(f"({o['opt']}) ")
                        r_lbl.bold = True
                        r_lbl.font.size = Pt(opt_font_size)
                        o_en_raw = str(o.get('en', '')).strip()
                        o_ta_raw = str(o.get('ta', '')).strip()
                        if '|' in o_en_raw:
                            parts_o = o_en_raw.split('|', 1)
                            o_en_raw = parts_o[0].strip()
                            if not o_ta_raw or o_ta_raw == o.get('en', '').strip() or '|' in o_ta_raw:
                                o_ta_raw = parts_o[1].strip()
                        elif '|' in o_ta_raw:
                            parts_o = o_ta_raw.split('|', 1)
                            if not o_en_raw:
                                o_en_raw = parts_o[0].strip()
                            o_ta_raw = parts_o[1].strip()

                        def _clean_opt_docx(text):
                            if not text:
                                return ""
                            t = str(text).strip()
                            t = re.sub(r'^\s*(?:\([A-Da-d]\)|[A-Da-d]\s*[\.\)\:\-]+\s*|[A-Da-d]\s+)\s*', '', t)
                            t = re.sub(r'^[\|\:\-\.\s]+', '', t).strip()
                            return t.strip()

                        o_en = _clean_opt_docx(o_en_raw)
                        o_ta = _clean_opt_docx(o_ta_raw)

                        if not o_ta:
                            m_tam = re.search(r'[\u0B80-\u0BFF]', o_en)
                            if m_tam:
                                o_ta = o_en[m_tam.start():].strip()
                                o_en = o_en[:m_tam.start()].strip()

                        if o_ta and o_en and o_ta.lower().startswith(o_en.lower()):
                            o_ta = o_ta[len(o_en):].strip()
                            o_ta = _clean_opt_docx(o_ta)

                        if o_ta.lower() == o_en.lower():
                            o_ta = ''

                        if re.match(r'^Option\s*[A-D]$', o_en, re.I):
                            if q.get('has_img'):
                                o_en = f"Fig. ({o['opt']})"
                                o_ta = f"படம் ({o['opt']})"
                            else:
                                o_en = ''
                                o_ta = ''
                        disp = o_en
                        if language_mode != 'english_only' and o_ta and o_ta.lower() != o_en.lower():
                            disp += f" / {o_ta}"
                        r_txt = p.add_run(disp)
                        r_txt.font.size = Pt(opt_font_size)
                        r_txt.font.name = 'Arial'
                        
                    if opt2 in opt_dict:
                        o = opt_dict[opt2]
                        p = row.cells[1].paragraphs[0]
                        p.paragraph_format.space_after = Pt(1)
                        r_lbl = p.add_run(f"({o['opt']}) ")
                        r_lbl.bold = True
                        r_lbl.font.size = Pt(opt_font_size)
                        o_en_raw = str(o.get('en', '')).strip()
                        o_ta_raw = str(o.get('ta', '')).strip()
                        if '|' in o_en_raw:
                            parts_o = o_en_raw.split('|', 1)
                            o_en_raw = parts_o[0].strip()
                            if not o_ta_raw or o_ta_raw == o.get('en', '').strip() or '|' in o_ta_raw:
                                o_ta_raw = parts_o[1].strip()
                        elif '|' in o_ta_raw:
                            parts_o = o_ta_raw.split('|', 1)
                            if not o_en_raw:
                                o_en_raw = parts_o[0].strip()
                            o_ta_raw = parts_o[1].strip()

                        o_en_raw = o_en_raw.replace('|', ' ').strip()
                        o_ta_raw = o_ta_raw.replace('|', ' ').strip()

                        o_en = _clean_opt_docx(o_en_raw)
                        o_ta = _clean_opt_docx(o_ta_raw)

                        if not o_ta:
                            m_tam = re.search(r'[\u0B80-\u0BFF]', o_en)
                            if m_tam:
                                o_ta = o_en[m_tam.start():].strip()
                                o_en = o_en[:m_tam.start()].strip()

                        if o_ta and o_en and o_ta.lower().startswith(o_en.lower()):
                            o_ta = o_ta[len(o_en):].strip()
                            o_ta = _clean_opt_docx(o_ta)

                        if o_ta.lower() == o_en.lower():
                            o_ta = ''

                        if re.match(r'^Option\s*[A-D]$', o_en, re.I):
                            if q.get('has_img'):
                                o_en = f"Fig. ({o['opt']})"
                                o_ta = f"படம் ({o['opt']})"
                            else:
                                o_en = ''
                                o_ta = ''
                        disp = o_en
                        if language_mode != 'english_only' and o_ta and o_ta.lower() != o_en.lower():
                            disp += f" / {o_ta}"
                        r_txt = p.add_run(disp)
                        r_txt.font.size = Pt(opt_font_size)
                        r_txt.font.name = 'Arial'

            # Divider line between questions
            divider_style = styling.get('question_divider', 'dashed')
            if divider_style == 'dashed':
                p_div = doc.add_paragraph()
                p_div.paragraph_format.space_before = Pt(1)
                p_div.paragraph_format.space_after = Pt(2)
                r_dash = p_div.add_run("-" * 90)
                r_dash.font.size = Pt(6)
                r_dash.font.color.rgb = RGBColor(180, 180, 180)
            elif divider_style == 'solid':
                p_div = doc.add_paragraph()
                p_div.paragraph_format.space_before = Pt(1)
                p_div.paragraph_format.space_after = Pt(2)
                r_dash = p_div.add_run("—" * 60)
                r_dash.font.size = Pt(6)
                r_dash.font.color.rgb = RGBColor(160, 160, 160)

        # Part B and Part C on last page
        is_last_page = (page_idx == len(pages) - 1)
        part_b_enabled = header_config.get('part_b_enabled', False)
        part_c_enabled = header_config.get('part_c_enabled', False)

        if is_last_page and (part_b_enabled or part_c_enabled):
            written_num = start_num + len(page_questions)
            if part_b_enabled:
                p_b_h = doc.add_paragraph()
                p_b_h.paragraph_format.space_before = Pt(6)
                p_b_h.paragraph_format.space_after = Pt(1)
                r_b_h = p_b_h.add_run(header_config.get('part_b_title', 'PART - B : SHORT ANSWER QUESTIONS'))
                r_b_h.bold = True
                r_b_h.font.size = Pt(10)
                r_b_h.font.name = 'Arial'

                p_b_s = doc.add_paragraph()
                p_b_s.paragraph_format.space_before = Pt(0)
                p_b_s.paragraph_format.space_after = Pt(3)
                r_b_s = p_b_s.add_run(header_config.get('part_b_subtitle', '(5 x 2 = 10 Marks) - Answer all questions.'))
                r_b_s.font.size = Pt(8.5)
                r_b_s.font.name = 'Arial'

                for q_text in header_config.get('part_b_questions', []):
                    p_q = doc.add_paragraph()
                    p_q.paragraph_format.space_before = Pt(2)
                    p_q.paragraph_format.space_after = Pt(1)
                    r_q = p_q.add_run(f"{written_num}. {q_text}")
                    r_q.bold = True
                    r_q.font.size = Pt(9)
                    r_q.font.name = 'Arial'

                    p_l = doc.add_paragraph()
                    p_l.paragraph_format.space_before = Pt(0)
                    p_l.paragraph_format.space_after = Pt(2)
                    r_l = p_l.add_run("_________________________________________________________________________________")
                    r_l.font.size = Pt(8)
                    r_l.font.color.rgb = RGBColor(160, 160, 160)
                    written_num += 1

            if part_c_enabled:
                p_c_h = doc.add_paragraph()
                p_c_h.paragraph_format.space_before = Pt(6)
                p_c_h.paragraph_format.space_after = Pt(1)
                r_c_h = p_c_h.add_run(header_config.get('part_c_title', 'PART - C : DESCRIPTIVE ANSWER QUESTIONS'))
                r_c_h.bold = True
                r_c_h.font.size = Pt(10)
                r_c_h.font.name = 'Arial'

                p_c_s = doc.add_paragraph()
                p_c_s.paragraph_format.space_before = Pt(0)
                p_c_s.paragraph_format.space_after = Pt(3)
                r_c_s = p_c_s.add_run(header_config.get('part_c_subtitle', '(4 x 5 = 20 Marks) - Answer all questions.'))
                r_c_s.font.size = Pt(8.5)
                r_c_s.font.name = 'Arial'

                for q_text in header_config.get('part_c_questions', []):
                    p_q = doc.add_paragraph()
                    p_q.paragraph_format.space_before = Pt(2)
                    p_q.paragraph_format.space_after = Pt(1)
                    r_q = p_q.add_run(f"{written_num}. {q_text}")
                    r_q.bold = True
                    r_q.font.size = Pt(9)
                    r_q.font.name = 'Arial'

                    p_l = doc.add_paragraph()
                    p_l.paragraph_format.space_before = Pt(0)
                    p_l.paragraph_format.space_after = Pt(2)
                    r_l = p_l.add_run("_________________________________________________________________________________")
                    r_l.font.size = Pt(8)
                    r_l.font.color.rgb = RGBColor(160, 160, 160)
                    written_num += 1

        # Marks Distribution Table on last page
        if is_last_page and styling.get('show_marks_table', False):
            mcq_total = sum(len(p) for p in pages)
            part_b_count = len(header_config.get('part_b_questions', [])) if part_b_enabled else 0
            part_b_marks = part_b_count * 2
            part_c_count = len(header_config.get('part_c_questions', [])) if part_c_enabled else 0
            part_c_marks = part_c_count * 5
            total_all_q = mcq_total + part_b_count + part_c_count
            total_all_marks = mcq_total * 1 + part_b_marks + part_c_marks

            rows_count = 2 + (1 if part_b_enabled else 0) + (1 if part_c_enabled else 0)
            m_table = doc.add_table(rows=rows_count, cols=3)
            m_table.style = 'Table Grid'
            m_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            m_table.autofit = False

            w0 = printable_w * 0.48
            w1 = printable_w * 0.32
            w2 = printable_w * 0.2
            for r in m_table.rows:
                r.cells[0].width = w0
                r.cells[1].width = w1
                r.cells[2].width = w2

            headers = ["MARKS DISTRIBUTION", "NUMBER OF QUESTIONS", "MARKS"]
            for c_i, h_txt in enumerate(headers):
                p = m_table.cell(0, c_i).paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(h_txt)
                r.bold = True
                r.font.size = Pt(8.5)
                r.font.name = 'Arial'

            row_idx = 1
            # Part A row
            p = m_table.cell(row_idx, 0).paragraphs[0]
            p.add_run("Part A - Multiple Choice").font.size = Pt(8.5)
            p = m_table.cell(row_idx, 1).paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(f"{mcq_total} x 1").font.size = Pt(8.5)
            p = m_table.cell(row_idx, 2).paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(str(mcq_total)).font.size = Pt(8.5)
            row_idx += 1

            if part_b_enabled:
                p = m_table.cell(row_idx, 0).paragraphs[0]
                p.add_run("Part B - Short Answer").font.size = Pt(8.5)
                p = m_table.cell(row_idx, 1).paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run(f"{part_b_count} x 2").font.size = Pt(8.5)
                p = m_table.cell(row_idx, 2).paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run(str(part_b_marks)).font.size = Pt(8.5)
                row_idx += 1

            if part_c_enabled:
                p = m_table.cell(row_idx, 0).paragraphs[0]
                p.add_run("Part C - Descriptive").font.size = Pt(8.5)
                p = m_table.cell(row_idx, 1).paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run(f"{part_c_count} x 5").font.size = Pt(8.5)
                p = m_table.cell(row_idx, 2).paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run(str(part_c_marks)).font.size = Pt(8.5)
                row_idx += 1

            # TOTAL row
            p = m_table.cell(row_idx, 0).paragraphs[0]
            r = p.add_run("TOTAL")
            r.bold = True
            r.font.size = Pt(8.5)
            p = m_table.cell(row_idx, 1).paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(f"{total_all_q} QUESTIONS")
            r.bold = True
            r.font.size = Pt(8.5)
            p = m_table.cell(row_idx, 2).paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(str(total_all_marks))
            r.bold = True
            r.font.size = Pt(8.5)

        # End of Question Paper Marker
        if is_last_page and styling.get('end_marker', False):
            p_end = doc.add_paragraph()
            p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_end.paragraph_format.space_before = Pt(6)
            p_end.paragraph_format.space_after = Pt(2)
            r_end = p_end.add_run(styling.get('end_marker_text', '******************** END OF QUESTION PAPER ********************'))
            r_end.bold = True
            r_end.font.size = Pt(8)
            r_end.font.name = 'Arial'

        # Footer (if enabled)
        if styling.get('page_border', False) or footer_config.get('page_number', True):
            p_ftr = doc.add_paragraph()
            p_ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_ftr.paragraph_format.space_before = Pt(6)
            p_ftr.paragraph_format.space_after = Pt(0)
            ftr_text = f"Page {page_idx + 1}"
            if footer_config.get('enabled', False) and footer_config.get('text'):
                ftr_text = f"{footer_config.get('text')}   {ftr_text}"
            r_ftr = p_ftr.add_run(ftr_text)
            r_ftr.font.size = Pt(8.5)
            r_ftr.font.color.rgb = RGBColor(120, 120, 120)
        elif footer_config.get('enabled', False):
            p_ftr = doc.add_paragraph()
            p_ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_ftr.paragraph_format.space_before = Pt(8)
            p_ftr.paragraph_format.space_after = Pt(0)
            r_ftr = p_ftr.add_run(footer_config.get('text', ''))
            r_ftr.font.size = Pt(9)
            r_ftr.font.color.rgb = RGBColor(100, 100, 100)

        # Page break if not the last page
        if page_idx < len(pages) - 1:
            doc.add_page_break()

    doc.save(output_path)
    return output_path
