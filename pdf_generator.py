import os
import shutil
import base64
import subprocess
import pypdf

def find_chrome():
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def get_base64_image(img_path):
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return None

def generate_html(paper_data, img_dir):
    pages = paper_data.get('pages', [])
    header_config = paper_data.get('header', {})
    footer_config = paper_data.get('footer', {})
    styling = paper_data.get('styling', {})
    
    has_page_border = styling.get('page_border', False)
    is_formal = has_page_border or header_config.get('include_instructions', False) or styling.get('show_marks_table', False)

    # Auto-scaling calculation based on max questions per page
    max_q_per_page = max(len(p) for p in pages) if pages else 10
    
    if styling.get('auto_fit', True):
        if max_q_per_page <= 6:
            q_font = 12
            ta_font = 10.5
            opt_font = 10
            q_pad_btm = 1.6
            row_gap = 0.8
        elif max_q_per_page <= 10:
            q_font = 8.8
            ta_font = 7.8
            opt_font = 7.6
            q_pad_btm = 0.35
            row_gap = 0.2
        elif max_q_per_page <= 14:
            q_font = 8.2
            ta_font = 7.4
            opt_font = 7.2
            q_pad_btm = 0.25
            row_gap = 0.15
        else:
            q_font = 7.5
            ta_font = 6.8
            opt_font = 6.8
            q_pad_btm = 0.12
            row_gap = 0.12
    else:
        q_font = styling.get('q_font_size', 10.5)
        ta_font = q_font - 1
        opt_font = styling.get('opt_font_size', 9)
        q_pad_btm = styling.get('q_pad_btm', 0.8)
        row_gap = styling.get('row_gap', 0.4)

    language_mode = styling.get('language_mode', 'bilingual')
    img_max_h = 24 if max_q_per_page >= 8 else 34
    img_max_w = 75 if max_q_per_page >= 8 else 95
    page_box_pad = "2.5mm 5mm 2mm 5mm" if (has_page_border and max_q_per_page > 14) else "4mm 6mm 3mm 6mm"

    divider_style = styling.get('question_divider', 'dashed')
    border_css = "none"
    if divider_style == 'dashed':
        border_css = "0.5px dashed #ccc"
    elif divider_style == 'solid':
        border_css = "0.5px solid #aaa"
    elif divider_style == 'double':
        border_css = "1.5px double #888"

    options_layout = styling.get('options_layout', '2col')
    if options_layout == '4col':
        grid_template = "repeat(4, 1fr)"
    elif options_layout == '1col':
        grid_template = "1fr"
    else:
        grid_template = "1fr 1fr"

    page_size = styling.get('page_size', 'A4')
    orientation = styling.get('orientation', 'portrait').lower()
    
    PAGE_SIZES_MM = {
        'A4': (210, 297),
        'A3': (297, 420),
        'Letter': (215.9, 279.4),
        'Legal': (215.9, 355.6),
        'A5': (148, 210)
    }
    base_w, base_h = PAGE_SIZES_MM.get(page_size, (210, 297))
    if orientation == 'landscape':
        page_w_mm, page_h_mm = base_h, base_w
    else:
        page_w_mm, page_h_mm = base_w, base_h

    is_landscape = (orientation == 'landscape')
    landscape_cols = styling.get('landscape_columns', True) if is_landscape else False
    
    if has_page_border:
        print_margin = "5mm 6mm 5mm 6mm"
        screen_pad = "5mm 6mm 5mm 6mm"
    else:
        print_margin = "6mm 8mm 6mm 8mm" if is_landscape else "7mm 10mm 7mm 10mm"
        screen_pad = "6mm 8mm 6mm 8mm" if is_landscape else "7mm 10mm 7mm 10mm"

    divider_repeat = 115 if is_landscape else 72

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{header_config.get('test_title', 'Question Paper')}</title>
<style>
@page {{
  size: {page_w_mm}mm {page_h_mm}mm {orientation};
  margin: {print_margin};
}}
* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}
body {{
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Tamil Sangam MN", "Tamil MN", Arial, sans-serif;
  color: #000;
  line-height: 1.18;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}}

@media screen {{
  html, body {{
    background-color: transparent !important;
    margin: 0 !important;
    padding: 16px 0 !important;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    overflow-x: hidden;
    width: 100%;
    min-height: 0 !important;
    height: auto !important;
  }}
  .page {{
    width: {page_w_mm}mm;
    min-height: {page_h_mm}mm;
    max-height: {page_h_mm}mm;
    height: {page_h_mm}mm;
    box-sizing: border-box;
    background: #ffffff;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.28), 0 2px 8px rgba(0, 0, 0, 0.16);
    border-radius: 3px;
    overflow: hidden;
    margin: 0 auto;
    padding: {screen_pad};
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    page-break-after: always;
  }}
  .page.page-hidden {{
    display: none !important;
  }}
}}

@media print {{
  html, body {{
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    height: 100% !important;
  }}
  .page {{
    width: 100% !important;
    height: 100% !important;
    max-height: 100% !important;
    box-shadow: none !important;
    border: none !important;
    border-radius: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    page-break-inside: avoid !important;
    page-break-after: always !important;
    break-after: page !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
  }}
  .page:last-child {{
    page-break-after: avoid !important;
    break-after: avoid !important;
  }}
}}

/* Header styling */
.exam-header {{
  text-align: center;
  font-weight: bold;
  font-size: 14pt;
  line-height: 1.25;
  margin-bottom: 1.5mm;
  text-transform: uppercase;
}}
.inst-name {{
  font-size: 14pt;
  letter-spacing: 0.5px;
}}
.test-meta {{
  display: flex;
  justify-content: space-between;
  font-size: 13.5pt;
  margin-top: 1mm;
  padding: 0 3mm;
}}
.divider-line {{
  font-family: monospace;
  font-size: 13pt;
  font-weight: bold;
  letter-spacing: -1px;
  overflow: hidden;
  white-space: nowrap;
  margin: 0.8mm 0 1.5mm 0;
  width: 100%;
}}

/* Question Container */
.questions-container {{
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}}

.questions-container.two-columns {{
  display: block;
  column-count: 2;
  column-gap: 8mm;
  column-rule: 0.5px solid #e0e0e0;
}}

.questions-container.two-columns .question-item {{
  break-inside: avoid;
  page-break-inside: avoid;
  margin-bottom: 2mm;
}}

.question-item {{
  border-bottom: {border_css};
  padding-bottom: {q_pad_btm}mm;
  padding-top: 0.5mm;
}}
.question-item:last-child {{
  border-bottom: none;
}}

.question-text {{
  font-size: {q_font}pt;
  font-weight: bold;
  margin-bottom: 0.8mm;
  display: flex;
  align-items: flex-start;
}}
.q-num {{
  min-width: 22px;
  color: #000;
}}
.q-body {{
  flex-grow: 1;
}}
.q-ta {{
  font-size: {ta_font}pt;
  font-weight: 500;
  color: #222;
  margin-top: 0.3mm;
}}

/* Image row */
.q-content-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.q-symbol-img {{
  max-height: {img_max_h}px;
  max-width: {img_max_w}px;
  object-fit: contain;
  border: 1px solid #777;
  padding: 1px;
  background: #fafafa;
  border-radius: 2px;
  margin-left: 6px;
}}

/* Options */
.options-grid {{
  font-size: {opt_font}pt;
  display: grid;
  grid-template-columns: {grid_template};
  grid-column-gap: 5mm;
  grid-row-gap: {row_gap}mm;
  margin-left: 22px;
}}
.option-item {{
  display: flex;
  align-items: baseline;
}}
.opt-label {{
  font-weight: bold;
  min-width: 17px;
}}
.opt-text {{
  color: #222;
}}
.opt-ta {{
  color: #444;
  font-size: {opt_font - 0.5}pt;
}}

/* Footer */
.exam-footer {{
  text-align: center;
  font-size: 9pt;
  color: #555;
  border-top: 0.5px solid #ccc;
  padding-top: 1.5mm;
  margin-top: 1.5mm;
}}

/* Formal Examination Styles */
.page-box {{
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
  position: relative;
}}
.page-box.has-border {{
  border: 1.5px solid #000;
  padding: {page_box_pad};
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
}}
.page-number-footer {{
  text-align: center;
  font-size: 8pt;
  color: #333;
  padding-top: 1mm;
  font-family: Arial, sans-serif;
}}

.exam-header-formal {{
  text-align: center;
  margin-bottom: 1.5mm;
}}
.inst-name-formal {{
  font-size: 13pt;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5mm;
}}
.test-title-formal {{
  font-size: 11pt;
  font-weight: bold;
  text-transform: uppercase;
  margin-bottom: 0.5mm;
}}
.session-formal {{
  font-size: 10pt;
  font-weight: bold;
  text-transform: uppercase;
  margin-bottom: 1.5mm;
}}
.meta-grid-formal {{
  display: flex;
  flex-direction: column;
  font-size: 9pt;
  font-weight: bold;
  margin-bottom: 1mm;
  gap: 1mm;
}}
.meta-row-formal {{
  display: flex;
  justify-content: space-between;
  width: 100%;
}}
.header-rule-formal {{
  border: none;
  border-top: 1px solid #000;
  margin: 1mm 0 1.5mm 0;
}}

.instructions-box {{
  margin-bottom: 1.5mm;
  font-size: 8pt;
  line-height: 1.35;
  text-align: left;
}}
.instructions-heading {{
  font-weight: bold;
  text-transform: uppercase;
  font-size: 8.5pt;
  margin-bottom: 0.5mm;
}}
.instructions-list {{
  margin: 0;
  padding-left: 0;
}}
.instructions-list div {{
  margin-bottom: 0.2mm;
}}

.part-header-box {{
  margin: 1.5mm 0 1mm 0;
  text-align: left;
}}
.part-title {{
  font-size: 9pt;
  font-weight: bold;
  text-transform: uppercase;
}}
.part-subtitle {{
  font-size: 8pt;
  font-weight: normal;
  color: #222;
}}

.condensed-header {{
  text-align: center;
  margin-bottom: 1.5mm;
}}
.condensed-header .inst-name-condensed {{
  font-size: 11.5pt;
  font-weight: bold;
  text-transform: uppercase;
}}
.condensed-header .title-session-condensed {{
  font-size: 9.5pt;
  font-weight: bold;
  margin-top: 0.3mm;
}}
.condensed-header .marks-condensed {{
  font-size: 9pt;
  font-weight: bold;
  text-align: center;
  margin-top: 0.5mm;
}}

.written-q-item {{
  font-size: 8.5pt;
  padding: 1.5mm 0 1mm 0;
  border-bottom: 0.5px solid #bbb;
}}
.written-q-item:last-child {{
  border-bottom: none;
}}
.written-q-title {{
  font-weight: bold;
  margin-bottom: 0.5mm;
}}

.marks-dist-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 7.5pt;
  margin-top: 2mm;
  margin-bottom: 1.5mm;
}}
.marks-dist-table th, .marks-dist-table td {{
  border: 1px solid #000;
  padding: 1.2mm 2mm;
  text-align: left;
}}
.marks-dist-table th {{
  background: #f4f4f4;
  font-weight: bold;
}}
.marks-dist-table tr.total-row td {{
  font-weight: bold;
  background: #fafafa;
}}
.end-marker-text {{
  text-align: center;
  font-size: 7.5pt;
  font-weight: bold;
  letter-spacing: 0.5px;
  margin-top: 1.5mm;
  margin-bottom: 0.5mm;
}}

.subheading-banner {{
  font-size: 9.5pt;
  font-weight: bold;
  text-align: center;
  border-top: 0.8px solid #999;
  border-bottom: 0.8px solid #999;
  padding: 0.8mm 0;
  margin: 1.2mm 0;
  background: #fbfbfb;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}}
</style>
</head>
<body>
"""

    current_q_num = 1
    current_subheading = None
    has_page_border = styling.get('page_border', False)
    is_formal = has_page_border or header_config.get('include_instructions', False) or styling.get('show_marks_table', False)

    for page_idx, page_questions in enumerate(pages):
        html += f'<div class="page" id="page{page_idx + 1}">'
        border_class = "has-border" if has_page_border else ""
        html += f'  <div class="page-box {border_class}">'
        
        # Header
        if header_config.get('enabled', True):
            show_header = (page_idx == 0) if header_config.get('page1_only', True) else True
            inst_text = header_config.get('inst_name', 'FITTER, GITI.,VEERAKERLAMPUDUR.')
            title_text = header_config.get('test_title', 'MONTHLY TEST - FIRST YEAR')
            session_text = header_config.get('session_text', '')
            date_text = header_config.get('date_text', 'DATE: ______________')
            time_text = header_config.get('time_text', 'TIME: ______________')
            reg_no_text = header_config.get('reg_no_text', 'Register No.: ____________________')
            marks_text = header_config.get('marks_text', 'Maximum Marks: 50')
            div_char = header_config.get('divider_char', '=')

            if show_header and is_formal:
                # Full formal exam header on page 1
                session_html = f'<div class="session-formal">{session_text}</div>' if session_text else ''
                html += f"""
    <div class="exam-header-formal">
      <div class="inst-name-formal">{inst_text}</div>
      <div class="test-title-formal">{title_text}</div>
      {session_html}
      <div class="meta-grid-formal">
        <div class="meta-row-formal">
          <span>{date_text}</span>
          <span>{time_text}</span>
        </div>
        <div class="meta-row-formal">
          <span>{reg_no_text}</span>
          <span>{marks_text}</span>
        </div>
      </div>
      <hr class="header-rule-formal" />
    </div>
"""
                # General Instructions
                if header_config.get('include_instructions', False):
                    ins_lines = header_config.get('instructions', [])
                    ins_html = "".join(f"<div>{ins}</div>" for ins in ins_lines)
                    html += f"""
    <div class="instructions-box">
      <div class="instructions-heading">GENERAL INSTRUCTIONS</div>
      <div class="instructions-list">
        {ins_html}
      </div>
    </div>
"""
                # Part A header
                if header_config.get('part_a_title'):
                    html += f"""
    <div class="part-header-box">
      <div class="part-title">{header_config.get('part_a_title')}</div>
      <div class="part-subtitle">{header_config.get('part_a_subtitle', '')}</div>
    </div>
"""
            elif show_header:
                # Standard clean header
                html += f"""
    <div class="exam-header">
      <div class="inst-name">{inst_text}</div>
      <div>{title_text}</div>
      <div class="test-meta">
        <span>{date_text}</span>
        <span>{marks_text}</span>
      </div>
      <div class="divider-line">{div_char * divider_repeat}</div>
    </div>
"""
            elif is_formal:
                # Condensed header on subsequent pages
                session_sub = f" | {session_text}" if session_text else ""
                html += f"""
    <div class="condensed-header">
      <div class="inst-name-condensed">{inst_text}</div>
      <div class="title-session-condensed">{title_text}{session_sub}</div>
      <div class="marks-condensed">{marks_text}</div>
      <hr class="header-rule-formal" />
    </div>
"""

        # Questions Container
        pad_top = "padding-top: 1mm;" if page_idx > 0 else ""
        container_class = "questions-container two-columns" if landscape_cols else "questions-container"
        html += f'    <div class="{container_class}" style="{pad_top}">\n'
        
        for q in page_questions:
            img_html = ""
            if q.get('has_img') and q.get('img_file'):
                img_path = os.path.join(img_dir, q['img_file'])
                if not os.path.exists(img_path):
                    for alt_dir in [
                        '/Users/tharungodwin/Downloads/question_paper_app/question_banks/extracted_imgs',
                        '/Users/tharungodwin/Downloads/question/extracted_imgs'
                    ]:
                        alt_p = os.path.join(alt_dir, q['img_file'])
                        if os.path.exists(alt_p):
                            img_path = alt_p
                            break
                b64 = get_base64_image(img_path)
                if b64:
                    img_html = f'<img class="q-symbol-img" src="data:image/png;base64,{b64}" alt="Diagram" />'

            import re
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

            # Helper for stripping question numbering prefixes
            def _clean_stem(text):
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

            q_en_clean = _clean_stem(q_en_raw)
            q_ta_clean = _clean_stem(q_ta_raw)

            if q_ta_clean and q_en_clean and q_ta_clean.lower().startswith(q_en_clean.lower()):
                q_ta_clean = q_ta_clean[len(q_en_clean):].strip()
                q_ta_clean = _clean_stem(q_ta_clean)

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

            # Never display bare 'Question 22' or numbers as question text
            if re.match(r'^(?:Question\s*\d+|\d+)$', q_en_clean, re.I) or len(q_en_clean) <= 3:
                if q_ta_clean and re.search(r'[\u0B80-\u0BFF]', q_ta_clean):
                    q_en_clean = q_ta_clean
                    q_ta_clean = ''
                else:
                    q_en_clean = ''

            opts_html = ""
            for o in q.get('options', []):
                o_en_raw = str(o.get('en', '')).strip()
                o_ta_raw = str(o.get('ta', '')).strip()
                opt_lbl = str(o.get('opt', '')).strip()

                if '|' in o_en_raw:
                    parts_o = o_en_raw.split('|', 1)
                    o_en_raw = parts_o[0].strip()
                    if not o_ta_raw or o_ta_raw.strip().lower() == str(o.get('en', '')).strip().lower() or '|' in o_ta_raw:
                        o_ta_raw = parts_o[1].strip()
                elif '|' in o_ta_raw:
                    parts_o = o_ta_raw.split('|', 1)
                    if not o_en_raw:
                        o_en_raw = parts_o[0].strip()
                    o_ta_raw = parts_o[1].strip()

                o_en_raw = o_en_raw.replace('|', ' ').strip()
                o_ta_raw = o_ta_raw.replace('|', ' ').strip()

                def _clean_opt(text):
                    if not text:
                        return ""
                    t = str(text).strip()
                    t = re.sub(r'^\s*(?:\([A-Da-d]\)|[A-Da-d]\s*[\.\)\:\-]+\s*|[A-Da-d]\s+)\s*', '', t)
                    t = re.sub(r'^[\|\:\-\.\s]+', '', t).strip()
                    return t.strip()

                o_en = _clean_opt(o_en_raw)
                o_ta = _clean_opt(o_ta_raw)

                if not o_ta:
                    m_tam = re.search(r'[\u0B80-\u0BFF]', o_en)
                    if m_tam:
                        o_ta = o_en[m_tam.start():].strip()
                        o_en = o_en[:m_tam.start()].strip()

                if o_ta and o_en and o_ta.lower().startswith(o_en.lower()):
                    o_ta = o_ta[len(o_en):].strip()
                    o_ta = _clean_opt(o_ta)

                if o_ta.lower() == o_en.lower():
                    o_ta = ''

                # Filter out or adapt dummy placeholder 'Option A'
                if re.match(r'^Option\s*[A-D]$', o_en, re.I):
                    if q.get('has_img'):
                        o_en = f"Fig. ({opt_lbl})"
                        o_ta = f"படம் ({opt_lbl})"
                    else:
                        continue

                if not o_en and not o_ta:
                    continue

                ta_part = f' <span class="opt-ta">/ {o_ta}</span>' if (language_mode != 'english_only' and o_ta) else ""
                opt_lbl_disp = f"{opt_lbl.lower()})" if is_formal else f"({opt_lbl})"
                opts_html += f"""
        <div class="option-item">
          <span class="opt-label">{opt_lbl_disp}</span>
          <span class="opt-text">{o_en}{ta_part}</span>
        </div>"""

            ta_html = f'<div class="q-ta">{q_ta_clean}</div>' if (language_mode != 'english_only' and q_ta_clean and q_ta_clean.strip().lower() != q_en_clean.strip().lower()) else ""

            # Subheading banner if subheading changes
            subheading = q.get('subheading')
            subheading_html = ""
            if subheading and subheading != current_subheading and str(subheading).lower() not in ["general", "none", ""]:
                current_subheading = subheading
                subheading_html = f'<div class="subheading-banner">-- {subheading} --</div>\n'

            options_block = f'<div class="options-grid">\n{opts_html}\n        </div>' if opts_html.strip() else ''

            html += f"""
      {subheading_html}<div class="question-item">
        <div class="q-content-row">
          <div class="question-text">
            <span class="q-num">{current_q_num}.</span>
            <div class="q-body">
              <div>{q_en_clean}</div>
              {ta_html}
            </div>
          </div>
          {img_html}
        </div>
        {options_block}
      </div>
"""
            current_q_num += 1

        # Additional Part B & Part C sections on the last page
        is_last_page = (page_idx == len(pages) - 1)
        part_b_enabled = header_config.get('part_b_enabled', False)
        part_c_enabled = header_config.get('part_c_enabled', False)

        if is_last_page and (part_b_enabled or part_c_enabled):
            written_num = current_q_num
            if part_b_enabled:
                b_title = header_config.get('part_b_title', 'PART - B : SHORT ANSWER QUESTIONS')
                b_sub = header_config.get('part_b_subtitle', '(5 x 2 = 10 Marks) - Answer all questions.')
                b_qs = header_config.get('part_b_questions', [])
                b_items_html = ""
                for q_text in b_qs:
                    b_items_html += f"""
        <div class="written-q-item">
          <div class="written-q-title">{written_num}. {q_text}</div>
          <div class="written-q-line">{'__________________________________________________________________________________________'}</div>
        </div>
"""
                    written_num += 1
                html += f"""
      <div class="part-header-box" style="margin-top: 2.5mm;">
        <div class="part-title">{b_title}</div>
        <div class="part-subtitle">{b_sub}</div>
      </div>
      {b_items_html}
"""
            if part_c_enabled:
                c_title = header_config.get('part_c_title', 'PART - C : DESCRIPTIVE ANSWER QUESTIONS')
                c_sub = header_config.get('part_c_subtitle', '(4 x 5 = 20 Marks) - Answer all questions.')
                c_qs = header_config.get('part_c_questions', [])
                c_items_html = ""
                for q_text in c_qs:
                    c_items_html += f"""
        <div class="written-q-item">
          <div class="written-q-title">{written_num}. {q_text}</div>
          <div class="written-q-line">{'__________________________________________________________________________________________'}</div>
        </div>
"""
                    written_num += 1
                html += f"""
      <div class="part-header-box" style="margin-top: 2.5mm;">
        <div class="part-title">{c_title}</div>
        <div class="part-subtitle">{c_sub}</div>
      </div>
      {c_items_html}
"""

        # Marks Distribution Table on last page
        if is_last_page and styling.get('show_marks_table', False):
            mcq_total = current_q_num - 1
            part_b_count = len(header_config.get('part_b_questions', [])) if part_b_enabled else 0
            part_b_marks = part_b_count * 2
            part_c_count = len(header_config.get('part_c_questions', [])) if part_c_enabled else 0
            part_c_marks = part_c_count * 5
            total_all_q = mcq_total + part_b_count + part_c_count
            total_all_marks = mcq_total * 1 + part_b_marks + part_c_marks

            b_row = f'<tr><td>Part B - Short Answer</td><td>{part_b_count} x 2</td><td>{part_b_marks}</td></tr>' if part_b_enabled else ''
            c_row = f'<tr><td>Part C - Descriptive</td><td>{part_c_count} x 5</td><td>{part_c_marks}</td></tr>' if part_c_enabled else ''

            html += f"""
      <table class="marks-dist-table">
        <thead>
          <tr>
            <th style="width: 48%;">MARKS DISTRIBUTION</th>
            <th style="width: 32%;">NUMBER OF QUESTIONS</th>
            <th style="width: 20%;">MARKS</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Part A - Multiple Choice</td>
            <td>{mcq_total} x 1</td>
            <td>{mcq_total}</td>
          </tr>
          {b_row}
          {c_row}
          <tr class="total-row">
            <td>TOTAL</td>
            <td>{total_all_q} QUESTIONS</td>
            <td>{total_all_marks}</td>
          </tr>
        </tbody>
      </table>
"""

        # End of Question Paper Marker
        if is_last_page and styling.get('end_marker', False):
            end_txt = styling.get('end_marker_text', '******************** END OF QUESTION PAPER ********************')
            html += f'<div class="end-marker-text">{end_txt}</div>\n'

        html += "    </div>\n" # end questions-container
        html += "  </div>\n"   # end page-box

        # Page numbering footer
        if has_page_border or footer_config.get('page_number', True):
            html += f'  <div class="page-number-footer">Page {page_idx + 1}</div>\n'
        elif footer_config.get('enabled', False):
            ftr_text = footer_config.get('text', '')
            html += f'  <div class="exam-footer">{ftr_text}</div>\n'

        html += "</div>\n" # end page

    html += """
</body>
</html>"""
    return html

def compile_pdf(html_content, output_pdf_path, temp_html_path):
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    chrome_path = find_chrome()
    cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_pdf_path}",
        temp_html_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    # Verify page count
    r = pypdf.PdfReader(output_pdf_path)
    return len(r.pages)
