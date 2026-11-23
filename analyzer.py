import os
import re
try:
    import cv2
except ImportError:
    cv2 = None
import json
import uuid
import glob
import subprocess
try:
    import numpy as np
except ImportError:
    np = None
import pdfplumber
import pypdf
from PIL import Image

CID_MAP = {
    '(cid:10)': 'பா',
    '(cid:18)': 'லை',
    '(cid:34)': 'ச',
    '(cid:37)': 'ன',
    '(cid:4)': 'ன்',
    '(cid:44)': 'ன',
    '(cid:49)': 'ட',
    '(cid:52)': 'சா',
    '(cid:75)': 'ஜ',
    '(cid:25)': 'ழ',
}

def clean_text(text):
    if not text:
        return ""
    for k, v in CID_MAP.items():
        text = text.replace(k, v)
    text = re.sub(r'\(cid:\d+\)', '', text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " ".join(" ".join(lines).split())

def split_en_ta(raw_text):
    """
    Splits bilingual text into English and Tamil parts.
    Strips leading question or option numbers.
    """
    raw_text = clean_text(raw_text)
    if '|' in raw_text:
        parts = raw_text.split('|', 1)
        en = parts[0].strip()
        ta = parts[1].strip()
    else:
        # Check first Tamil unicode character in range 0x0B80 - 0x0BFF
        m = re.search(r'[\u0B80-\u0BFF]', raw_text)
        if m:
            en = raw_text[:m.start()].strip()
            ta = raw_text[m.start():].strip()
        else:
            en = raw_text.strip()
            ta = ""

    en = en.replace('|', ' ').strip()
    ta = ta.replace('|', ' ').strip()
            
    # Strip leading question or option numbering (e.g., '19.', '5)', '1. ', 'A.', '(A)', 'Question 22')
    while True:
        prev_en = en
        en = re.sub(r'^\s*(?:Question|Ques|Qn|Q)\s*\.?\s*\d+\s*[\.\:\-\)\s]*', '', en, flags=re.I)
        en = re.sub(r'^\s*\d+\s*[\.\)\:\-]+\s*', '', en)
        en = re.sub(r'^\s*(?:\([A-Da-d]\)|[A-Da-d]\s*[\.\)\:\-]+\s*|[A-Da-d]\s+)\s*', '', en)
        en = re.sub(r'^[\|\:\-\.\s]+', '', en).strip()
        if en == prev_en:
            break

    while True:
        prev_ta = ta
        ta = re.sub(r'^\s*(?:Question|Ques|Qn|Q)\s*\.?\s*\d+\s*[\.\:\-\)\s]*', '', ta, flags=re.I)
        ta = re.sub(r'^\s*\d+\s*[\.\)\:\-]+\s*', '', ta)
        ta = re.sub(r'^\s*(?:\([A-Da-d]\)|[A-Da-d]\s*[\.\)\:\-]+\s*|[A-Da-d]\s+)\s*', '', ta)
        ta = re.sub(r'^[\|\:\-\.\s]+', '', ta).strip()
        if ta == prev_ta:
            break

    # If ta starts with en duplicate, strip it
    if ta and en and ta.lower().startswith(en.lower()):
        ta = ta[len(en):].strip()
        ta = re.sub(r'^[\|\:\-\.\s]+', '', ta).strip()
    
    # If ta is identical to en, clear ta to avoid duplication
    if ta.lower() == en.lower():
        ta = ""
    elif not re.search(r'[\u0B80-\u0BFF]', ta) and not re.search(r'[\u0B80-\u0BFF]', en):
        if ta.lower() in en.lower():
            ta = ""
        elif en.lower() in ta.lower():
            en = ta
            ta = ""
        
    return en, ta

def is_header_or_noise(text):
    t = text.strip()
    if not t:
        return True
    if re.match(r'^\s*Question\s*\d+\s*$', t, re.I):
        return True
    if re.search(r'^(?:FITTER|FIRST\s*YEAR|I\.CHANDRA|====+|\d+\s*[\-\.]\s*QUESTIONS)', t, re.I):
        return True
    if t.isdigit() and len(t) <= 3: # lone page numbers
        return True
    return False

def read_page_image(img_path):
    if not img_path or not os.path.exists(img_path):
        return None
    if cv2 is not None:
        return cv2.imread(img_path)
    try:
        pil_im = Image.open(img_path).convert('RGB')
        if np is not None:
            arr = np.array(pil_im)
            return arr[:, :, ::-1]
        return pil_im
    except Exception:
        return None

def save_crop_image(save_path, img_obj):
    if img_obj is None:
        return
    if cv2 is not None and hasattr(img_obj, 'shape'):
        cv2.imwrite(save_path, img_obj)
    elif isinstance(img_obj, Image.Image):
        img_obj.save(save_path)
    elif hasattr(img_obj, 'shape'):
        try:
            if len(img_obj.shape) == 3 and img_obj.shape[2] == 3:
                Image.fromarray(img_obj[:, :, ::-1]).save(save_path)
            else:
                Image.fromarray(img_obj).save(save_path)
        except Exception:
            pass

def crop_box(img_obj, x0, y0, x1, y1):
    if img_obj is None:
        return None
    if hasattr(img_obj, 'shape'):
        return img_obj[y0:y1, x0:x1]
    elif isinstance(img_obj, Image.Image):
        return img_obj.crop((x0, y0, x1, y1))
    return None

def tight_crop_image(img):
    if img is None:
        return img
    if isinstance(img, Image.Image):
        gray = img.convert('L')
        lut = [255 if p < 235 else 0 for p in range(256)]
        mask = gray.point(lut, mode='1')
        bbox = mask.getbbox()
        if bbox:
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if w > 15 and h > 15:
                pad = 4
                box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                       min(img.width, bbox[2] + pad), min(img.height, bbox[3] + pad))
                return img.crop(box)
        return img
    elif hasattr(img, 'size') and img.size > 0:
        if cv2 is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        elif np is not None:
            gray = np.mean(img, axis=2).astype(np.uint8) if len(img.shape) == 3 else img
        else:
            return img
        if np is not None:
            y_idx, x_idx = np.where(gray < 235)
            if len(y_idx) > 0 and len(x_idx) > 0:
                ymin, ymax = y_idx.min(), y_idx.max()
                xmin, xmax = x_idx.min(), x_idx.max()
                if (ymax - ymin > 15) and (xmax - xmin > 15):
                    return img[max(0, ymin - 4):min(img.shape[0], ymax + 5), max(0, xmin - 4):min(img.shape[1], xmax + 5)]
    return img

def find_rendered_page(render_dir, p_num):
    for pat in [f"*p_{p_num}-*.png", f"*p_{p_num}*.png", f"*-{p_num:03d}*.png", f"*-{p_num:02d}*.png", f"*-{p_num}.png"]:
        matches = glob.glob(os.path.join(render_dir, pat))
        if matches:
            return matches[0]
    return None

def analyze_sequential_pdf(pdf_path, img_dir, bank_id, trade_name="General Trade"):
    """
    Parses flowing/sequential document PDFs where questions and options are listed line by line.
    Extracts text, options, answer highlights, and crops diagrams.
    """
    temp_dir = os.path.join(os.path.dirname(pdf_path), f"temp_render_{bank_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    extracted_questions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        # 1. Identify which pages have diagrams (pattern rects, height > 20, or embedded images)
        pages_with_diagrams = set()
        for pno, page in enumerate(pdf.pages):
            pat_rects = [r for r in page.rects if str(r.get('non_stroking_color', '')).startswith('P') or r['height'] > 20]
            if pat_rects or len(page.images) > 0:
                pages_with_diagrams.add(pno + 1)
                
        # 2. Render only pages with diagrams at 150 DPI
        for p_num in pages_with_diagrams:
            prefix = os.path.join(temp_dir, f"p_{p_num}")
            try:
                subprocess.run(
                    ['pdftoppm', '-png', '-r', '150', '-f', str(p_num), '-l', str(p_num), pdf_path, prefix],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception as e:
                print(f"pdftoppm render error page {p_num}: {e}")

        # 3. Parse pages sequentially
        current_q = None
        current_module = "General"
        current_subheading = ""
        global_id_counter = 1
        
        for pno in range(total_pages):
            page = pdf.pages[pno]
            p_num = pno + 1
            words = page.extract_words(x_tolerance=1.5)
            rects = page.rects
            
            # Answer highlights (gray background)
            gray_rects = [r for r in rects if str(r.get('non_stroking_color')) == '(0.82745, 0.82745, 0.82745)']
            # Diagram rects (pattern drawings or boxes)
            pat_rects = [r for r in rects if str(r.get('non_stroking_color', '')).startswith('P') or r['height'] > 20]
            
            # Rendered image if available
            page_img_path = find_rendered_page(temp_dir, p_num)
            page_cv = read_page_image(page_img_path)
            img_w = page_cv.shape[1] if hasattr(page_cv, 'shape') else (page_cv.width if page_cv else 1)
            img_h = page_cv.shape[0] if hasattr(page_cv, 'shape') else (page_cv.height if page_cv else 1)
            scale_x = img_w / page.width if page_cv is not None else 2.083
            scale_y = img_h / page.height if page_cv is not None else 2.083

            # Group words into lines
            lines = []
            for w in words:
                matched = False
                for l in lines:
                    if abs(l['top'] - w['top']) < 3.5:
                        l['words'].append(w)
                        l['bottom'] = max(l['bottom'], w['bottom'])
                        matched = True
                        break
                if not matched:
                    lines.append({'top': w['top'], 'bottom': w['bottom'], 'words': [w]})
            lines.sort(key=lambda x: x['top'])
            for l in lines:
                l['text'] = ' '.join(w['text'] for w in l['words'])

            for l in lines:
                txt = l['text'].strip()
                if not txt:
                    continue
                    
                # Detect module/section headers
                mod_m = re.search(r'MODULE\s*(\d+[^|\n]*)', txt, re.I)
                if mod_m:
                    current_module = mod_m.group(0).strip()
                    current_subheading = ""
                    continue
                if re.search(r'^சதாகுதி\s*\d+', txt, re.I):
                    current_module = txt
                    current_subheading = ""
                    continue
                    
                # Detect sub-headings and topic titles (e.g. Questions: Level 1, Section A, Part 1, Topic)
                sub_m = re.search(r'^(?:QUESTIONS\s*[:\-]?\s*)?(LEVEL\s*\d+|SECTION\s*[-:]?\s*[A-Z0-9]+|PART\s*[-:]?\s*[A-Z0-9]+|TOPIC\s*[-:]?\s*[^|\n]+)', txt, re.I)
                if sub_m and not re.match(r'^\s*\d+[\.\)]\s*', txt):
                    current_subheading = sub_m.group(0).strip()
                    continue

                # Section numbers like '12.2. TOPIC' or '8.2. TOPIC'
                multi_num_m = re.match(r'^\s*\d+(?:\.\d+)+[\.\)]\s*(.*)', txt)
                if multi_num_m:
                    current_subheading = multi_num_m.group(1).strip().rstrip('-: ')
                    continue

                # Numbered topic heading ending with '-' or ':' without question mark (e.g. '8. BUILDING YOUR RESUME -')
                m_topic = re.match(r'^\s*\d+[\.\)]\s*([A-Z0-9\s/&]+(?:\s*-\s*|\s*:\s*))(.*)', txt)
                if m_topic and '?' not in txt:
                    current_subheading = m_topic.group(1).strip().rstrip('-: ')
                    continue
                    
                if is_header_or_noise(txt):
                    continue
                    
                # Check Question Start: number followed by dot/paren and letter
                qm = re.match(r'^\s*(\d+)[\.\)]\s*(.*)', txt)
                if qm and not re.search(r'^\d+\.\d+\s*mm', txt, re.I) and not txt.endswith('mm'):
                    if current_q:
                        # Finalize previous question
                        extracted_questions.append(current_q)
                        
                    orig_num = int(qm.group(1))
                    en, ta = split_en_ta(qm.group(2))
                    
                    # Find if Option A exists later on this page to bound diagram search
                    opt_a_top = None
                    curr_idx = lines.index(l)
                    for nxt_l in lines[curr_idx + 1:min(curr_idx + 10, len(lines))]:
                        if re.match(r'^\s*A[\.\)]\s*', nxt_l['text']):
                            opt_a_top = nxt_l['top']
                            break
                        if re.match(r'^\s*\d+[\.\)]\s*', nxt_l['text']):
                            break
                            
                    limit_top = opt_a_top + 15 if opt_a_top else page.height
                    
                    # Check matching diagram rect
                    has_img = False
                    img_file = None
                    for pr in list(pat_rects):
                        if (l['bottom'] - 12 <= pr['top']) and (pr['bottom'] <= limit_top + 15):
                            has_img = True
                            if page_cv is not None:
                                py0 = max(0, int(pr['top'] * scale_y) - 4)
                                py1 = min(page_cv.shape[0], int(pr['bottom'] * scale_y) + 4)
                                px0 = max(0, int(pr['x0'] * scale_x) - 4)
                                px1 = min(page_cv.shape[1], int(pr['x1'] * scale_x) + 4)
                                crop = crop_box(page_cv, px0, py0, px1, py1)
                                crop = tight_crop_image(crop)
                                img_file = f"{bank_id}_p{p_num}_q{orig_num}.png"
                                save_crop_image(os.path.join(img_dir, img_file), crop)
                            pat_rects.remove(pr) # consumed
                            break
                            
                    # Check raster page.images
                    if not has_img and page.images:
                        for im in page.images:
                            if (l['bottom'] - 12 <= im['top']) and (im['bottom'] <= limit_top + 15):
                                has_img = True
                                if page_cv is not None:
                                    py0 = max(0, int(im['top'] * scale_y) - 4)
                                    py1 = min(img_h, int(im['bottom'] * scale_y) + 4)
                                    px0 = max(0, int(im['x0'] * scale_x) - 4)
                                    px1 = min(img_w, int(im['x1'] * scale_x) + 4)
                                    crop = crop_box(page_cv, px0, py0, px1, py1)
                                    crop = tight_crop_image(crop)
                                    img_file = f"{bank_id}_p{p_num}_q{orig_num}.png"
                                    save_crop_image(os.path.join(img_dir, img_file), crop)
                                break

                    current_q = {
                        "orig_id": orig_num,
                        "global_id": global_id_counter,
                        "module": current_module,
                        "subheading": current_subheading,
                        "q_en": en,
                        "q_ta": ta if ta else en,
                        "options": [],
                        "ans": "A",
                        "has_img": has_img,
                        "img_file": img_file,
                        "page": p_num
                    }
                    global_id_counter += 1
                elif current_q is not None:
                    # Check if line contains one or more options (e.g. 'A. Tang', '(A) Tang', 'A. Tang B. Heel')
                    opt_matches = re.findall(r'(?:^|\s+)(?:\(?([A-Da-d])[\.\)]\s*)(.*?)(?=(?:\s+\(?[A-Da-d][\.\)]\s*)|$)', txt)
                    if opt_matches:
                        for opt_char, opt_body in opt_matches:
                            opt_letter = opt_char.upper()
                            o_en, o_ta = split_en_ta(opt_body)
                            
                            # Check answer highlight
                            for gr in gray_rects:
                                if abs(gr['top'] - l['top']) < 7:
                                    current_q['ans'] = opt_letter
                                    break
                                    
                            current_q['options'].append({
                                "opt": opt_letter,
                                "en": o_en,
                                "ta": o_ta if o_ta else o_en
                            })
                    else:
                        # Continuation text
                        if not current_q['options']:
                            c_en, c_ta = split_en_ta(txt)
                            if c_en: current_q['q_en'] += " " + c_en
                            if c_ta and current_q['q_ta'] != current_q['q_en']:
                                current_q['q_ta'] += " " + c_ta
                        else:
                            last_opt = current_q['options'][-1]
                            c_en, c_ta = split_en_ta(txt)
                            if c_en: last_opt['en'] += " " + c_en
                            if c_ta and last_opt['ta'] != last_opt['en']:
                                last_opt['ta'] += " " + c_ta

        if current_q:
            extracted_questions.append(current_q)

    # Clean up temp render dir
    try:
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)
    except:
        pass
        
    # Filter out any non-question items (e.g. topic headings that slipped through)
    valid_questions = []
    for q in extracted_questions:
        q_en = q.get('q_en', '').strip()
        opts = q.get('options', [])
        
        # If it ends with '-' or ':' and has no options, it's a topic header
        if (q_en.endswith('-') or q_en.endswith(':')) and not opts:
            continue
            
        # If it has 0 options and no question mark/question stem and no image, discard
        if not opts and not q.get('has_img'):
            has_q_word = bool(re.search(r'\b(what|which|how|why|name|state|describe|explain|calculate|find|identify|choose|select)\b', q_en, re.I))
            if '?' not in q_en and not has_q_word:
                continue
                
        # Deduplicate option letters and keep only real options (NEVER fill fake Option A/B/C/D)
        seen_letters = set()
        clean_opts = []
        for o in opts:
            if o['opt'] not in seen_letters:
                seen_letters.add(o['opt'])
                clean_opts.append(o)
        q['options'] = clean_opts
        valid_questions.append(q)

    extracted_questions = valid_questions

    # Extract clean module list
    modules = []
    seen_mods = set()
    for q in extracted_questions:
        mod = q.get('module', 'General')
        if mod not in seen_mods:
            seen_mods.add(mod)
            modules.append(mod)

    # Base name title
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    base_name = re.sub(r'^(bank_|custom_)[a-f0-9]+_', '', base_name)
    clean_title = base_name.replace('_', ' ').replace('-', ' ').title()

    return {
        "module_id": bank_id,
        "module_name": clean_title,
        "trade": trade_name,
        "modules": modules,
        "questions": extracted_questions
    }

def analyze_table_pdf(pdf_path, img_dir, bank_id, trade_name="General Trade"):
    """
    Parses table-grid PDFs (where each question is in a bordered table row).
    """
    temp_dir = os.path.join(os.path.dirname(pdf_path), f"temp_render_{bank_id}")
    os.makedirs(temp_dir, exist_ok=True)
    
    render_prefix = os.path.join(temp_dir, "page")
    try:
        subprocess.run(["pdftoppm", "-png", "-r", "150", pdf_path, render_prefix], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"pdftoppm error: {e}")

    extracted_questions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        global_q_counter = 1
        
        for p_idx, page in enumerate(pdf.pages):
            page_img_path = find_rendered_page(temp_dir, p_idx + 1)
            page_cv_img = read_page_image(page_img_path)
            img_w = page_cv_img.shape[1] if hasattr(page_cv_img, 'shape') else (page_cv_img.width if page_cv_img else 1)
            img_h = page_cv_img.shape[0] if hasattr(page_cv_img, 'shape') else (page_cv_img.height if page_cv_img else 1)
            scale_x = img_w / page.width if page_cv_img is not None else 2.083
            scale_y = img_h / page.height if page_cv_img is not None else 2.083
            
            tables = page.find_tables()
            if tables:
                t = tables[0]
                extracted_data = page.extract_tables()[0] if page.extract_tables() else []
                
                for r_idx, row_obj in enumerate(t.rows):
                    if r_idx >= len(extracted_data):
                        break
                    row = extracted_data[r_idx]
                    if not row or len(row) < 5:
                        continue
                        
                    first_cell = str(row[0]).strip() if row[0] else ""
                    if first_cell.lower() in ['#', 'sl', 'sl.no', 'q.no', 'no']:
                        continue
                        
                    q_num_match = re.search(r'\d+', first_cell)
                    if not q_num_match and not (len(row) > 1 and row[1] and len(str(row[1]).strip()) > 10):
                        continue
                        
                    q_id = int(q_num_match.group(0)) if q_num_match else global_q_counter
                    
                    q_en_raw = clean_text(str(row[1])) if len(row) > 1 and row[1] else ""
                    opt_a_raw = clean_text(str(row[2])) if len(row) > 2 and row[2] else ""
                    opt_b_raw = clean_text(str(row[3])) if len(row) > 3 and row[3] else ""
                    opt_c_raw = clean_text(str(row[4])) if len(row) > 4 and row[4] else ""
                    opt_d_raw = clean_text(str(row[5])) if len(row) > 5 and row[5] else ""
                    
                    q_ta_raw = clean_text(str(row[6])) if len(row) > 6 and row[6] else ""
                    opt_a_ta_raw = clean_text(str(row[7])) if len(row) > 7 and row[7] else ""
                    opt_b_ta_raw = clean_text(str(row[8])) if len(row) > 8 and row[8] else ""
                    opt_c_ta_raw = clean_text(str(row[9])) if len(row) > 9 and row[9] else ""
                    opt_d_ta_raw = clean_text(str(row[10])) if len(row) > 10 and row[10] else ""

                    # Never invent 'Question {q_id}' as stem
                    if not q_en_raw and q_ta_raw:
                        q_en_raw = q_ta_raw
                    elif not q_en_raw and not q_ta_raw and not (row_obj and row_obj.bbox):
                        continue
                    
                    q_en = re.sub(r'^\s*\d+[\.\)\:\-\s]+', '', q_en_raw).strip()
                    q_ta = re.sub(r'^\s*\d+[\.\)\:\-\s]+', '', q_ta_raw).strip()
                    opt_a = re.sub(r'^\s*[A-D][\.\)\:\-\s]+', '', opt_a_raw).strip()
                    opt_b = re.sub(r'^\s*[A-D][\.\)\:\-\s]+', '', opt_b_raw).strip()
                    opt_c = re.sub(r'^\s*[A-D][\.\)\:\-\s]+', '', opt_c_raw).strip()
                    opt_d = re.sub(r'^\s*[A-D][\.\)\:\-\s]+', '', opt_d_raw).strip()
                    
                    opt_a_ta = re.sub(r'^\s*[A-D][\.\)\:\-\s]+', '', opt_a_ta_raw).strip()
                    opt_b_ta = re.sub(r'^\s*[A-D][\.\)\:\-\s]+', '', opt_b_ta_raw).strip()
                    opt_c_ta = re.sub(r'^\s*[A-D][\.\)\:\-\s]+', '', opt_c_ta_raw).strip()
                    opt_d_ta = re.sub(r'^\s*[A-D][\.\)\:\-\s]+', '', opt_d_ta_raw).strip()
                    
                    ans = "A"
                    for cell in reversed(row):
                        if cell and str(cell).strip().upper() in ['A', 'B', 'C', 'D']:
                            ans = str(cell).strip().upper()
                            break
                            
                    has_img = False
                    img_filename = f"{bank_id}_q{q_id}_clean.png"
                    img_save_path = os.path.join(img_dir, img_filename)
                    
                    # Extract diagram strictly from graphics (curves, lines, images) inside cell, below text
                    c1_bbox = row_obj.cells[1] if len(row_obj.cells) > 1 else None
                    if c1_bbox and page_cv_img is not None:
                        cx0, cy0, cx1, cy1 = c1_bbox
                        words = [w for w in page.extract_words() if w['x0'] >= cx0 - 2 and w['x1'] <= cx1 + 2 and w['top'] >= cy0 - 2 and w['bottom'] <= cy1 + 2]
                        text_b = max((w['bottom'] for w in words), default=cy0 + 10)
                        
                        m = 4
                        inner_box = (cx0 + m, cy0 + m, cx1 - m, cy1 - m)
                        diag_curves = [c for c in page.curves if c['x0'] >= inner_box[0] and c['x1'] <= inner_box[2] and c['top'] >= text_b - 2 and c['bottom'] <= inner_box[3]]
                        diag_lines = [l for l in page.lines if l['x0'] >= inner_box[0] and l['x1'] <= inner_box[2] and l['top'] >= text_b - 2 and l['bottom'] <= inner_box[3]]
                        diag_imgs = [im for im in getattr(page, 'images', []) if im['x0'] >= inner_box[0] and im['x1'] <= inner_box[2] and im['top'] >= text_b - 2 and im['bottom'] <= inner_box[3]]
                        
                        all_diag_items = diag_curves + diag_lines + diag_imgs
                        if (len(diag_curves) + len(diag_lines) >= 8) or len(diag_imgs) > 0:
                            all_x = [it['x0'] for it in all_diag_items] + [it['x1'] for it in all_diag_items]
                            all_y = [it['top'] for it in all_diag_items] + [it['bottom'] for it in all_diag_items]
                            xmin, xmax = min(all_x) - 4, max(all_x) + 4
                            ymin, ymax = min(all_y) - 4, max(all_y) + 4
                            
                            px0 = max(0, int(xmin * scale_x))
                            px1 = min(img_w, int(xmax * scale_x))
                            py0 = max(0, int(ymin * scale_y))
                            py1 = min(img_h, int(ymax * scale_y))
                            
                            if (px1 - px0) >= 30 and (py1 - py0) >= 30:
                                crop = crop_box(page_cv_img, px0, py0, px1, py1)
                                if cv2 is not None and hasattr(crop, 'shape'):
                                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                                    _, th = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY_INV)
                                    is_valid = cv2.countNonZero(th) > 150
                                elif isinstance(crop, Image.Image):
                                    gray = crop.convert('L')
                                    lut = [255 if p < 230 else 0 for p in range(256)]
                                    mask = gray.point(lut, mode='1')
                                    is_valid = (mask.tobytes().count(b'\xff') > 150)
                                elif np is not None and hasattr(crop, 'shape'):
                                    gray = np.mean(crop, axis=2).astype(np.uint8) if len(crop.shape) == 3 else crop
                                    is_valid = np.count_nonzero(gray < 230) > 150
                                else:
                                    is_valid = True
                                if is_valid:
                                    save_crop_image(img_save_path, crop)
                                    has_img = True
                                
                    q_obj = {
                        "orig_id": q_id,
                        "global_id": global_q_counter,
                        "module": "General",
                        "q_en": q_en,
                        "q_ta": q_ta if q_ta else q_en,
                        "options": [
                            {"opt": "A", "en": opt_a, "ta": opt_a_ta if opt_a_ta else opt_a},
                            {"opt": "B", "en": opt_b, "ta": opt_b_ta if opt_b_ta else opt_b},
                            {"opt": "C", "en": opt_c, "ta": opt_c_ta if opt_c_ta else opt_c},
                            {"opt": "D", "en": opt_d, "ta": opt_d_ta if opt_d_ta else opt_d}
                        ],
                        "ans": ans,
                        "has_img": has_img,
                        "img_file": img_filename if has_img else None
                    }
                    extracted_questions.append(q_obj)
                    global_q_counter += 1

    try:
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)
    except:
        pass

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    base_name = re.sub(r'^(bank_|custom_)[a-f0-9]+_', '', base_name)
    clean_title = base_name.replace('_', ' ').replace('-', ' ').title()

    return {
        "module_id": bank_id,
        "module_name": clean_title,
        "trade": trade_name,
        "modules": ["General"],
        "questions": extracted_questions
    }

def analyze_pdf(pdf_path, img_dir, bank_id=None, trade_name="General Trade"):
    """
    Analyzes any uploaded PDF, automatically determining whether it is a scanned
    image-based PDF, table-based, or sequential/flowing document PDF.
    """
    if not bank_id:
        bank_id = f"bank_{uuid.uuid4().hex[:8]}"
        
    os.makedirs(img_dir, exist_ok=True)
    
    # 1. Check if scanned / image-based PDF
    try:
        from scanned_analyzer import is_scanned_pdf, extract_all_scanned_questions
        if is_scanned_pdf(pdf_path):
            print(f"Analyzing {pdf_path} using Scanned Image-based OCR Parser...")
            return extract_all_scanned_questions(pdf_path, img_dir, bank_id, trade_name)
    except Exception as e:
        print(f"Scanned parser check failed or error: {e}")
    
    # 2. Check if table grid exists in first 3 pages
    is_table = False
    with pdfplumber.open(pdf_path) as pdf:
        check_pages = min(3, len(pdf.pages))
        for pno in range(check_pages):
            tables = pdf.pages[pno].find_tables()
            if tables:
                extracted = pdf.pages[pno].extract_tables()
                if extracted and len(extracted[0]) > 0 and len(extracted[0][0]) >= 5:
                    is_table = True
                    break
                    
    if is_table:
        print(f"Analyzing {pdf_path} using Table Grid Parser...")
        bank_data = analyze_table_pdf(pdf_path, img_dir, bank_id, trade_name)
        if len(bank_data.get('questions', [])) >= 3:
            return bank_data
            
    print(f"Analyzing {pdf_path} using Sequential Document Parser...")
    return analyze_sequential_pdf(pdf_path, img_dir, bank_id, trade_name)
