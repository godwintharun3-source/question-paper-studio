import os
import re
try:
    import cv2
except ImportError:
    cv2 = None
import json
import glob
import subprocess
import numpy as np
try:
    import pytesseract
    from pytesseract import Output
except ImportError:
    pytesseract = None
    Output = None
from concurrent.futures import ThreadPoolExecutor

MODULE_RANGES = [
    {"name": "Assembly", "start": 2, "end": 25, "key": 26},
    {"name": "Gauges", "start": 27, "end": 32, "key": 33},
    {"name": "Pipe and Pipe Fitting", "start": 34, "end": 39, "key": 40},
    {"name": "Drilling Jig", "start": 41, "end": 44, "key": 45},
    {"name": "Repairing Technique", "start": 46, "end": 56, "key": 57},
    {"name": "Hydraulics and Pneumatics", "start": 58, "end": 69, "key": 70},
    {"name": "Preventive Maintenance", "start": 71, "end": 75, "key": 76},
    {"name": "Erection and Testing", "start": 77, "end": 81, "key": 82},
]

def is_scanned_pdf(pdf_path):
    """
    Checks if the PDF is scanned / raster image based.
    """
    import pypdf
    try:
        reader = pypdf.PdfReader(pdf_path)
        total_chars = 0
        check_pages = min(5, len(reader.pages))
        for i in range(check_pages):
            text = reader.pages[i].extract_text() or ""
            total_chars += len(text.strip())
        return total_chars < 60
    except Exception:
        return False

def parse_key_paper(img_path):
    """
    Parses answer key paper from image.
    Returns {level: {q_num: ans_letter}}
    """
    img = cv2.imread(img_path)
    if img is None:
        return {}
    txt = pytesseract.image_to_string(img, lang='eng').replace('|', ' ')
    level_chunks = re.split(r'Questions:\s*Level\s*(\d+)', txt, flags=re.I)
    keys_by_level = {}
    if len(level_chunks) > 1:
        for idx in range(1, len(level_chunks), 2):
            try:
                lvl = int(level_chunks[idx])
            except ValueError:
                lvl = 1
            chunk = level_chunks[idx+1]
            matches = re.findall(r'(\d+)[\.\s\:\-]+([A-D0-9Oa-d])', chunk)
            lvl_ans = {}
            for qn_str, ans_char in matches:
                ans_char = ans_char.upper()
                if ans_char in ['0', 'O']:
                    ans_char = 'D'
                elif ans_char == '4':
                    ans_char = 'A'
                elif ans_char == '8':
                    ans_char = 'B'
                try:
                    lvl_ans[int(qn_str)] = ans_char
                except ValueError:
                    pass
            keys_by_level[lvl] = lvl_ans
    return keys_by_level

def find_diagram_in_row(row_img, v_mid):
    """
    Detects technical illustration contours inside a row slice.
    Masks out text words and table borders so only pure drawings are captured.
    Returns (diag_crop, diag_bbox_in_row)
    """
    rh, rw, _ = row_img.shape
    if rh < 35 or rw < 35:
        return None, None
        
    # 1. OCR text detection to mask text bounding boxes
    try:
        d = pytesseract.image_to_data(row_img, output_type=pytesseract.Output.DICT)
        text_mask = np.zeros((rh, rw), dtype=np.uint8)
        for i in range(len(d['text'])):
            t = d['text'][i].strip()
            if t:
                x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
                cv2.rectangle(text_mask, (max(0, x-5), max(0, y-5)), (min(rw, x+w+5), min(rh, y+h+5)), 255, -1)
    except Exception:
        text_mask = np.zeros((rh, rw), dtype=np.uint8)

    # 2. Thresholding
    gray = cv2.cvtColor(row_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)
    
    # Clear margins & vertical separator
    thresh[:5, :] = 0
    thresh[-5:, :] = 0
    thresh[:, :5] = 0
    thresh[:, -5:] = 0
    if 0 <= v_mid < rw:
        thresh[:, max(0, v_mid-8):min(rw, v_mid+8)] = 0

    # 3. Morphological removal of table grid lines
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    lines_h = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_h)
    thresh[lines_h > 0] = 0
    
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    lines_v = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_v)
    thresh[lines_v > 0] = 0

    # Mask out text
    thresh[text_mask > 0] = 0

    # 4. Find graphic illustration contours
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    diag_contours = []
    for c in cnts:
        bx, by, bw, bh = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        if area > 400 and bw >= 30 and bh >= 30:
            if 0.15 < (bw / bh) < 6.5:
                diag_contours.append((bx, by, bw, bh, area, c))
                
    if not diag_contours:
        return None, None
        
    en_diags = [d for d in diag_contours if d[0] < v_mid]
    candidates = en_diags if en_diags else diag_contours
    
    best_diag = max(candidates, key=lambda x: x[4])
    bx, by, bw, bh, area, _ = best_diag
    
    group_x0 = bx
    group_y0 = by
    group_x1 = bx + bw
    group_y1 = by + bh
    for d in candidates:
        if d == best_diag:
            continue
        dbx, dby, dbw, dbh, _, _ = d
        if abs(dbx - group_x1) < 25 or abs((dbx + dbw) - group_x0) < 25 or abs(dby - group_y1) < 25 or abs((dby + dbh) - group_y0) < 25:
            group_x0 = min(group_x0, dbx)
            group_y0 = min(group_y0, dby)
            group_x1 = max(group_x1, dbx + dbw)
            group_y1 = max(group_y1, dby + dbh)
            
    pad = 6
    crop = row_img[max(0, group_y0-pad):min(rh, group_y1+pad), max(0, group_x0-pad):min(rw, group_x1+pad)]
    bbox = (group_x0, group_y0, group_x1 - group_x0, group_y1 - group_y0)
    return crop, bbox

def parse_options_text(text):
    """
    Extracts options A, B, C, D from text.
    """
    opts = {}
    matches = list(re.finditer(r'(?:^|\s|\n)([A-Da-d0])[\.\)]\s*', text))
    if matches:
        for i in range(len(matches)):
            raw_letter = matches[i].group(1).upper()
            if raw_letter == '0':
                raw_letter = 'D'
            start = matches[i].end()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            opt_val = text[start:end].strip()
            opt_val = ' '.join(opt_val.split())
            opts[raw_letter] = opt_val
    return opts

def clean_stem(raw_text):
    if not raw_text:
        return ""
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    text = " ".join(lines)
    # Strip any level or section headings embedded in question text
    text = re.sub(r'^(?:Questions\s*:\s*)?Level\s*\d+[\s\:\.\-]+', '', text, flags=re.I).strip()
    text = re.sub(r'^(?:Section|Part|Topic)\s*[:\-]?\s*[A-Za-z0-9]+[\s\:\.\-]+', '', text, flags=re.I).strip()
    # Strip leading noise, question numbers, bullets
    text = re.sub(r'^[^\w\u0B80-\u0BFF]*\d+[\.\)\:\-\s]+', '', text).strip()
    text = re.sub(r'^[^\w\u0B80-\u0BFF]+', '', text).strip()
    return text

def parse_scanned_page(img_path, page_num, module_name, key_answers, bank_id, img_dir):
    """
    Extracts all questions and diagrams from a single scanned page.
    """
    img = cv2.imread(img_path)
    if img is None:
        return []
    h, w, _ = img.shape
    v_mid = w // 2

    # Measure exact vertical center divider
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h / 30)))
    v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vert_kernel)
    v_cols = np.where(v_lines.sum(axis=0) > 255 * (h * 0.4))[0]
    for v in v_cols:
        if abs(v - w//2) < w * 0.15:
            v_mid = int(v)
            break

    en_col = img[:, :v_mid]
    data = pytesseract.image_to_data(en_col, lang='eng', output_type=Output.DICT)

    # Detect question starting positions in English column
    q_starts = []
    current_level = 1
    for i in range(len(data['text'])):
        word = data['text'][i].strip()
        y = data['top'][i]
        x = data['left'][i]
        
        # Check level heading
        if 'level' in word.lower():
            # Check next word for 1, 2, 3
            if i + 1 < len(data['text']) and data['text'][i+1].strip().isdigit():
                current_level = int(data['text'][i+1].strip())
                
        if re.match(r'^\d{1,3}[\.\)]$', word) and x < 130:
            qn = int(re.sub(r'\D', '', word))
            q_starts.append((qn, y, current_level))

    if not q_starts:
        # Fallback to horizontal lines
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horiz_kernel)
        h_rows = np.where(h_lines.sum(axis=1) > 255 * (w * 0.15))[0]
        if len(h_rows) > 0:
            def cluster(arr, gap=15):
                res = [arr[0]]
                for val in arr[1:]:
                    if val - res[-1] > gap:
                        res.append(val)
                return res
            pts = cluster(h_rows)
            for idx in range(len(pts)-1):
                if pts[idx+1] - pts[idx] > 60:
                    q_starts.append((idx+1, pts[idx], current_level))

    if not q_starts:
        return []

    # Sort and filter close starts
    q_starts.sort(key=lambda it: it[1])
    filtered_starts = [q_starts[0]]
    for it in q_starts[1:]:
        if it[1] - filtered_starts[-1][1] > 60:
            filtered_starts.append(it)

    extracted = []
    for idx in range(len(filtered_starts)):
        qn, y1, lvl = filtered_starts[idx]
        y2 = filtered_starts[idx+1][1] if idx+1 < len(filtered_starts) else min(h - 40, y1 + 320)
        if y2 - y1 < 50:
            continue

        row_img = img[max(0, y1-8):min(h, y2-4), :]
        rh, rw, _ = row_img.shape

        # Detect diagram
        diag_crop, diag_bbox = find_diagram_in_row(row_img, v_mid)
        has_img = False
        img_filename = None
        if diag_crop is not None and diag_crop.shape[0] > 25 and diag_crop.shape[1] > 25:
            has_img = True
            img_filename = f"{bank_id}_p{page_num}_q{qn}.png"
            img_save_path = os.path.join(img_dir, img_filename)
            cv2.imwrite(img_save_path, diag_crop)

        # Extract text cells for OCR (keep intact, do NOT overwrite with white)
        en_cell = row_img[:, 8:v_mid-5].copy()
        ta_cell = row_img[:, v_mid+5:rw-8].copy()

        # OCR
        txt_en = pytesseract.image_to_string(en_cell, lang='eng').strip()
        txt_ta = pytesseract.image_to_string(ta_cell, lang='eng+tam').strip()

        # Skip if header row or pure subheading
        if 'module :' in txt_en.lower() and not re.search(r'\d+\.\s+[A-Za-z]', txt_en):
            continue
        if re.search(r'^(?:questions\s*[:\-]?\s*)?level\s*\d+\s*$', txt_en.strip(), re.I):
            continue

        # Parse English stem & options
        opt_en_match = re.search(r'(?:^|\n|\s)[A-D][\.\)]\s*', txt_en)
        if opt_en_match:
            stem_en_raw = txt_en[:opt_en_match.start()]
            opts_en_raw = txt_en[opt_en_match.start():]
        else:
            stem_en_raw = txt_en
            opts_en_raw = ""

        q_en_clean = clean_stem(stem_en_raw)
        opts_en = parse_options_text(opts_en_raw)

        # Parse Tamil stem & options
        opt_ta_match = re.search(r'(?:^|\n|\s)[A-D][\.\)]\s*', txt_ta)
        if opt_ta_match:
            stem_ta_raw = txt_ta[:opt_ta_match.start()]
            opts_ta_raw = txt_ta[opt_ta_match.start():]
        else:
            stem_ta_raw = txt_ta
            opts_ta_raw = ""

        q_ta_clean = clean_stem(stem_ta_raw)
        opts_ta = parse_options_text(opts_ta_raw)

        # Skip if empty or noise
        if len(q_en_clean) < 3 and not has_img:
            continue

        # Build options only if options exist in text
        options_list = []
        if opts_en:
            opt_a = opts_en.get('A', '')
            opt_b = opts_en.get('B', '')
            opt_c = opts_en.get('C', '')
            opt_d = opts_en.get('D', '')

            opt_a_ta = opts_ta.get('A', opt_a)
            opt_b_ta = opts_ta.get('B', opt_b)
            opt_c_ta = opts_ta.get('C', opt_c)
            opt_d_ta = opts_ta.get('D', opt_d)

            options_list = [
                {"opt": "A", "en": opt_a, "ta": opt_a_ta},
                {"opt": "B", "en": opt_b, "ta": opt_b_ta},
                {"opt": "C", "en": opt_c, "ta": opt_c_ta},
                {"opt": "D", "en": opt_d, "ta": opt_d_ta}
            ]

        # Answer key lookup
        ans = "A"
        if module_name in key_answers:
            mod_keys = key_answers[module_name]
            if lvl in mod_keys and qn in mod_keys[lvl]:
                ans = mod_keys[lvl][qn]
            else:
                for l_idx in mod_keys:
                    if qn in mod_keys[l_idx]:
                        ans = mod_keys[l_idx][qn]
                        break

        # Clean up any leftover 'Question \d+' prefixes
        q_en_clean = re.sub(r'^\s*(?:Question\s*\d+|Q\d+)[\.\:\-]*\s*', '', q_en_clean, flags=re.I).strip()
        q_ta_clean = re.sub(r'^\s*(?:Question\s*\d+|Q\d+)[\.\:\-]*\s*', '', q_ta_clean, flags=re.I).strip()

        if not q_en_clean and q_ta_clean:
            q_en_clean = q_ta_clean
            q_ta_clean = ""

        # Skip if completely empty and no image
        if not q_en_clean and not q_ta_clean and not has_img:
            continue

        q_item = {
            "orig_id": qn,
            "page_num": page_num,
            "module": module_name,
            "subheading": f"Level {lvl}",
            "level": lvl,
            "q_en": q_en_clean,
            "q_ta": q_ta_clean if q_ta_clean else q_en_clean,
            "options": options_list,
            "ans": ans,
            "has_img": has_img,
            "img_file": img_filename
        }
        extracted.append(q_item)

    return extracted

def extract_all_scanned_questions(pdf_path, img_dir, bank_id, trade_name="Fitter Trade"):
    """
    Main entry point for extracting all modules, questions, diagrams and keys
    from scanned PDF books. Supports both predefined NIMI module ranges and
    fully automatic dynamic detection for any scanned question bank.
    """
    os.makedirs(img_dir, exist_ok=True)
    temp_render = os.path.join(os.path.dirname(pdf_path), f"scanned_render_{bank_id}")
    os.makedirs(temp_render, exist_ok=True)

    existing_pages = sorted(glob.glob(os.path.join(temp_render, "page-*.png")))
    if len(existing_pages) < 2:
        if os.path.exists("/tmp/scanned_all_pages") and len(glob.glob("/tmp/scanned_all_pages/page-*.png")) >= 80 and "6613ba81" in bank_id:
            print("Reusing pre-rendered pages from /tmp/scanned_all_pages...")
            for f in glob.glob("/tmp/scanned_all_pages/page-*.png"):
                dest = os.path.join(temp_render, os.path.basename(f))
                if not os.path.exists(dest):
                    import shutil
                    shutil.copy2(f, dest)
            existing_pages = sorted(glob.glob(os.path.join(temp_render, "page-*.png")))
        else:
            print(f"Rendering {pdf_path} to PNGs...")
            subprocess.run(['pdftoppm', '-png', '-r', '150', pdf_path, os.path.join(temp_render, "page")])
            existing_pages = sorted(glob.glob(os.path.join(temp_render, "page-*.png")))

    total_pages = len(existing_pages)
    print(f"Total rendered pages: {total_pages}")

    # Determine module plan
    key_answers = {}
    tasks = []

    if total_pages >= 80:
        # Standard 82-page NIMI 2nd Year Question Bank
        for mod_info in MODULE_RANGES:
            kp_num = mod_info["key"]
            kp_path = os.path.join(temp_render, f"page-{kp_num:02d}.png")
            if os.path.exists(kp_path):
                key_answers[mod_info["name"]] = parse_key_paper(kp_path)

        for mod_info in MODULE_RANGES:
            m_name = mod_info["name"]
            for pno in range(mod_info["start"], mod_info["end"] + 1):
                p_path = os.path.join(temp_render, f"page-{pno:02d}.png")
                if os.path.exists(p_path):
                    tasks.append((p_path, pno, m_name))
    else:
        # Dynamic module and key page detection for custom/different scanned books
        print("Running dynamic module and key paper detection...")
        key_page_indices = []
        for idx, p_path in enumerate(existing_pages, start=1):
            im = cv2.imread(p_path)
            if im is not None:
                header_crop = im[:int(im.shape[0] * 0.25), :]
                txt = pytesseract.image_to_string(header_crop, lang='eng').lower()
                if 'key paper' in txt or 'key-paper' in txt or 'answer key' in txt:
                    key_page_indices.append(idx)
                    mod_match = re.search(r'module\s*[:\-]?\s*(\d+)?\s*[:\-]?\s*([A-Za-z\s]+)', txt)
                    m_title = mod_match.group(2).strip().title() if mod_match else f"Module {len(key_page_indices)}"
                    key_answers[m_title] = parse_key_paper(p_path)

        # Build page slices
        start_p = 2 if total_pages > 2 else 1
        curr_mod_idx = 1
        for idx, p_path in enumerate(existing_pages, start=1):
            if idx in key_page_indices or idx == 1:
                continue
            mod_title = f"Module {curr_mod_idx}"
            tasks.append((p_path, idx, mod_title))

    print(f"Processing {len(tasks)} question pages in parallel...")
    all_extracted_questions = []

    def worker(args):
        p_path, pno, m_name = args
        return parse_scanned_page(p_path, pno, m_name, key_answers, bank_id, img_dir)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(worker, tasks))

    global_id = 1
    final_questions = []
    all_modules = []

    for page_q_list in results:
        for q in page_q_list:
            q["global_id"] = global_id
            global_id += 1
            if q["module"] not in all_modules:
                all_modules.append(q["module"])
            final_questions.append(q)

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    base_name = re.sub(r'^(bank_|custom_)[a-f0-9]+_', '', base_name)
    clean_title = base_name.replace('_', ' ').replace('-', ' ').title()

    bank_data = {
        "module_id": bank_id,
        "module_name": clean_title,
        "trade": trade_name,
        "modules": all_modules,
        "questions": final_questions
    }

    return bank_data
