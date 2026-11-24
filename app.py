import os
import re
import json
import uuid
import shutil
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response
from werkzeug.utils import secure_filename
from urllib.parse import parse_qs, urlencode, unquote

from extractor import load_question_bank, allocate_questions
from pdf_generator import generate_html, compile_pdf
from google_forms_generator import generate_google_apps_script, generate_manual_form_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

class VercelMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        raw_qs = environ.get('QUERY_STRING', '')
        qs = parse_qs(raw_qs, keep_blank_values=True)
        if '__path' in qs and qs['__path']:
            orig_path = unquote(qs['__path'][0])
            if not orig_path.startswith('/'):
                orig_path = '/' + orig_path
            environ['PATH_INFO'] = orig_path
            del qs['__path']
            environ['QUERY_STRING'] = urlencode(qs, doseq=True)
        elif environ.get('HTTP_X_MATCHED_PATH') and environ.get('HTTP_X_MATCHED_PATH') not in ['/api/index.py', '/api/index']:
            environ['PATH_INFO'] = environ['HTTP_X_MATCHED_PATH']
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelMiddleware(app.wsgi_app)

BANKS_DIR = os.path.join(BASE_DIR, 'question_banks')
IMG_DIR = os.path.join(BANKS_DIR, 'extracted_imgs')

if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    CUSTOM_BANKS_DIR = '/tmp/question_banks'
    CUSTOM_IMG_DIR = '/tmp/extracted_imgs'
    EXPORTS_DIR = '/tmp/exports'
    UPLOADS_DIR = '/tmp/uploads'
else:
    CUSTOM_BANKS_DIR = BANKS_DIR
    CUSTOM_IMG_DIR = IMG_DIR
    EXPORTS_DIR = os.path.join(BASE_DIR, 'exports')
    UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')

for d in [CUSTOM_BANKS_DIR, CUSTOM_IMG_DIR, EXPORTS_DIR, UPLOADS_DIR]:
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass

def find_bank_file(bank_id):
    if not bank_id:
        return None
    if not bank_id.endswith('.json'):
        bank_id = f"{bank_id}.json"
    p = os.path.join(CUSTOM_BANKS_DIR, bank_id)
    if os.path.exists(p):
        return p
    p = os.path.join(BANKS_DIR, bank_id)
    if os.path.exists(p):
        return p
    return os.path.join(CUSTOM_BANKS_DIR, bank_id)

def get_writable_bank_file(bank_id):
    if not bank_id.endswith('.json'):
        bank_id = f"{bank_id}.json"
    return os.path.join(CUSTOM_BANKS_DIR, bank_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extracted_imgs/<filename>')
def serve_image(filename):
    if os.path.exists(os.path.join(CUSTOM_IMG_DIR, filename)):
        return send_from_directory(CUSTOM_IMG_DIR, filename)
    if os.path.exists(os.path.join(IMG_DIR, filename)):
        return send_from_directory(IMG_DIR, filename)
    fallback_dir = '/Users/tharungodwin/Downloads/question/extracted_imgs'
    if os.path.exists(os.path.join(fallback_dir, filename)):
        return send_from_directory(fallback_dir, filename)
    transparent_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(transparent_png, mimetype='image/png')

@app.route('/api/banks', methods=['GET'])
def get_banks():
    banks = []
    seen = set()
    scan_dirs = [CUSTOM_BANKS_DIR, BANKS_DIR] if CUSTOM_BANKS_DIR != BANKS_DIR else [BANKS_DIR]
    for s_dir in scan_dirs:
        if not os.path.exists(s_dir):
            continue
        for f in os.listdir(s_dir):
            if f.endswith('.json') and f not in seen:
                seen.add(f)
                path = os.path.join(s_dir, f)
                data = load_question_bank(path)
                if data:
                    modules = data.get('modules', [])
                    if not modules:
                        mods = []
                        for q in data.get('questions', []):
                            m = q.get('module')
                            if m and m not in mods:
                                mods.append(m)
                        modules = mods
                        
                    banks.append({
                        'id': f,
                        'name': data.get('module_name', f),
                        'trade': data.get('trade', 'General'),
                        'total_questions': len(data.get('questions', [])),
                        'modules': modules
                    })
    return jsonify({'banks': banks})

@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
            
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.pdf'):
            return jsonify({'status': 'error', 'message': 'Only PDF files are supported'}), 400
            
        bank_id = f"custom_{uuid.uuid4().hex[:8]}"
        saved_pdf_path = os.path.join(UPLOADS_DIR, f"{bank_id}_{filename}")
        file.save(saved_pdf_path)
        
        trade_name = request.form.get('trade_name', 'Custom Trade')
        
        # Run automated analysis
        from analyzer import analyze_pdf
        bank_data = analyze_pdf(saved_pdf_path, CUSTOM_IMG_DIR, bank_id=bank_id, trade_name=trade_name)
        
        # Save question bank JSON
        bank_json_path = get_writable_bank_file(bank_id)
        with open(bank_json_path, 'w', encoding='utf-8') as f:
            json.dump(bank_data, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'status': 'success',
            'bank': {
                'id': f"{bank_id}.json",
                'name': bank_data['module_name'],
                'trade': bank_data['trade'],
                'total_questions': len(bank_data['questions']),
                'diagrams_count': sum(1 for q in bank_data['questions'] if q.get('has_img'))
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/upload_book', methods=['POST'])
def upload_book():
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
            
        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.pdf'):
            return jsonify({'status': 'error', 'message': 'Only PDF files are supported'}), 400
            
        bank_id = f"custom_book_{uuid.uuid4().hex[:8]}"
        saved_pdf_path = os.path.join(UPLOADS_DIR, f"{bank_id}_{filename}")
        file.save(saved_pdf_path)
        
        subject_title = request.form.get('subject_title', '').strip() or os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
        page_range_text = request.form.get('page_range', '').strip()
        paper_format = request.form.get('paper_format', 'combined') # 'combined', 'mcq_only', 'short_only', 'long_only'
        
        mcq_count = int(request.form.get('mcq_count', 20))
        short_count = int(request.form.get('short_count', 5))
        long_count = int(request.form.get('long_count', 3))
        short_marks = int(request.form.get('short_marks', 2))
        long_marks = int(request.form.get('long_marks', 16))
        
        from book_analyzer import extract_text_and_diagrams_from_book, synthesize_questions_from_book, parse_page_range as parse_book_pages
        selected_pages = parse_book_pages(page_range_text) if page_range_text else None
        
        # 1. Extract text, definitions, concepts and figures from the subject book
        extracted_data = extract_text_and_diagrams_from_book(
            saved_pdf_path, CUSTOM_IMG_DIR, bank_id, selected_pages=selected_pages
        )
        
        # 2. Synthesize Part A, Part B, Part C questions
        config = {
            'mcq_count': mcq_count,
            'short_count': short_count,
            'long_count': long_count,
            'short_marks': short_marks,
            'long_marks': long_marks,
            'paper_format': paper_format
        }
        bank_data = synthesize_questions_from_book(
            extracted_data, bank_id, subject_title=subject_title, config=config
        )
        
        # 3. Save Question Bank JSON
        bank_json_path = get_writable_bank_file(bank_id)
        with open(bank_json_path, 'w', encoding='utf-8') as f:
            json.dump(bank_data, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'status': 'success',
            'bank': {
                'id': f"{bank_id}.json",
                'name': bank_data['module_name'],
                'trade': bank_data['trade'],
                'total_questions': len(bank_data['questions']),
                'diagrams_count': sum(1 for q in bank_data['questions'] if q.get('has_img')),
                'header_config': bank_data.get('header_config'),
                'grand_total_marks': bank_data.get('grand_total_marks'),
                'short_questions': bank_data.get('short_questions'),
                'long_questions': bank_data.get('long_questions')
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def strip_question_prefixes(text):
    if not text:
        return ''
    text = str(text).strip()
    import re
    while True:
        prev = text
        text = re.sub(r'^\s*(?:Question|Ques|Qn|Q)\s*\.?\s*\d+\s*[\.\:\-\)\s]*', '', text, flags=re.I)
        text = re.sub(r'^\s*\d+\s*[\.\)\:\-]+\s*', '', text)
        text = re.sub(r'^[\|\:\-\.\s]+', '', text).strip()
        if text == prev:
            break
    return text.strip()

def strip_option_prefixes(text):
    if not text:
        return ''
    text = str(text).strip()
    import re
    text = re.sub(r'^\s*(?:\([A-Da-d]\)|[A-Da-d]\s*[\.\)\:\-]+\s*|[A-Da-d]\s+)\s*', '', text)
    text = re.sub(r'^[\|\:\-\.\s]+', '', text).strip()
    return text.strip()

def parse_page_range(range_str):
    """
    Parses page expressions like '1-40, 60, 80-100' or '1,4,6,8' into a set of integers.
    """
    if not range_str or not str(range_str).strip():
        return set()
    pages = set()
    tokens = re.split(r'[,;\s]+', str(range_str).strip())
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if '-' in token:
            parts = token.split('-', 1)
            if parts[0].isdigit() and parts[1].isdigit():
                p1, p2 = int(parts[0]), int(parts[1])
                start_p, end_p = min(p1, p2), max(p1, p2)
                pages.update(range(start_p, end_p + 1))
        elif token.isdigit():
            pages.add(int(token))
    return pages

def build_paper_data(payload):
    import re
    bank_id = payload.get('bank_id', 'fitter_mod2_basic_fitting.json')
    bank_path = find_bank_file(bank_id)
    bank_data = load_question_bank(bank_path) if bank_path else None
    if not bank_data:
        raise ValueError(f"Question bank {bank_id} not found.")

    all_questions = bank_data.get('questions', [])
    
    # Filter by Module if specified
    module_filter = payload.get('module_filter', 'all')
    if module_filter and module_filter != 'all':
        filtered = [q for q in all_questions if q.get('module') == module_filter]
        if filtered:
            all_questions = filtered

    # Defensive cleaning and filtering of questions & diagrams
    import shutil
    clean_all_questions = []
    for q in all_questions:
        en = str(q.get('q_en', '')).strip()
        ta = str(q.get('q_ta', '')).strip()

        # Split pipe | if present
        if '|' in en:
            parts = en.split('|', 1)
            en = parts[0].strip()
            if not ta or ta.lower() == str(q.get('q_en', '')).strip().lower() or '|' in ta:
                ta = parts[1].strip()
        elif '|' in ta:
            parts = ta.split('|', 1)
            if not en:
                en = parts[0].strip()
            ta = parts[1].strip()

        en = en.replace('|', ' ').strip()
        ta = ta.replace('|', ' ').strip()

        if not ta:
            # Check if Tamil script is merged into English stem
            m_tam = re.search(r'[\u0B80-\u0BFF]', en)
            if m_tam:
                ta = en[m_tam.start():].strip()
                en = en[:m_tam.start()].strip()

        en = strip_question_prefixes(en)
        ta = strip_question_prefixes(ta)

        # If ta starts with identical English text, strip the duplicate prefix
        if ta and en and ta.lower().startswith(en.lower()):
            ta = ta[len(en):].strip()
            ta = strip_question_prefixes(ta)

        if ta.lower() == en.lower():
            ta = ''
        elif not re.search(r'[\u0B80-\u0BFF]', ta) and not re.search(r'[\u0B80-\u0BFF]', en):
            if ta.lower() in en.lower():
                ta = ''
            elif en.lower() in ta.lower():
                en = ta
                ta = ''

        # If en is empty or just lone number/Question XX, discard if no image
        if (not en or re.match(r'^(?:Question\s*\d+|\d+)$', en, flags=re.I) or len(en) <= 3) and ta:
            en = ta
            ta = ''

        if not en and not ta and not q.get('has_img'):
            continue

        # Filter out topic headings that slipped in
        fake_opt_count = sum(1 for o in q.get('options', []) if o.get('en') in ['Option A', 'Option B', 'Option C', 'Option D', '', None])
        is_empty_or_fake_opts = (fake_opt_count == len(q.get('options', [])))
        if is_empty_or_fake_opts and not q.get('has_img'):
            if en.endswith('-') or en.endswith('–') or en.endswith(':') or re.search(r'^(?:BUILDING|PERSONAL|MANAGING|MODULE|SECTION|CHAPTER|UNIT)\b', en, re.I):
                continue
            if '?' not in en and not re.search(r'\b(what|which|how|why|name|calculate|find|identify|choose|select|state|define|explain)\b', en, re.I):
                continue

        q['q_en'] = en
        q['q_ta'] = ta

        # Clean options
        clean_opts = []
        for o in q.get('options', []):
            o_en = str(o.get('en', '')).strip()
            o_ta = str(o.get('ta', '')).strip()
            opt_lbl = str(o.get('opt', '')).strip()

            if '|' in o_en:
                p_o = o_en.split('|', 1)
                o_en = p_o[0].strip()
                if not o_ta or o_ta.lower() == str(o.get('en', '')).strip().lower() or '|' in o_ta:
                    o_ta = p_o[1].strip()
            elif '|' in o_ta:
                p_o = o_ta.split('|', 1)
                if not o_en:
                    o_en = p_o[0].strip()
                o_ta = p_o[1].strip()

            o_en = o_en.replace('|', ' ').strip()
            o_ta = o_ta.replace('|', ' ').strip()

            o_en = strip_option_prefixes(o_en)
            o_ta = strip_option_prefixes(o_ta)

            if not o_ta:
                m_tam = re.search(r'[\u0B80-\u0BFF]', o_en)
                if m_tam:
                    o_ta = o_en[m_tam.start():].strip()
                    o_en = o_en[:m_tam.start()].strip()

            if o_ta and o_en and o_ta.lower().startswith(o_en.lower()):
                o_ta = o_ta[len(o_en):].strip()
                o_ta = strip_option_prefixes(o_ta)

            # Handle fake placeholder options
            if re.match(r'^Option\s*[A-D]$', o_en, re.I):
                if q.get('has_img'):
                    o_en = f"Fig. ({opt_lbl})"
                    o_ta = f"படம் ({opt_lbl})"
                else:
                    o_en = ''
                    o_ta = ''

            if o_ta.lower() == o_en.lower():
                o_ta = ''

            o['en'] = o_en
            o['ta'] = o_ta
            clean_opts.append(o)

        q['options'] = clean_opts

        # Resolve diagram image file if present
        if q.get('has_img') and q.get('img_file'):
            dest_img = os.path.join(IMG_DIR, q['img_file'])
            if not os.path.exists(dest_img):
                for alt_dir in [
                    '/Users/tharungodwin/Downloads/question_paper_app/question_banks/extracted_imgs',
                    '/Users/tharungodwin/Downloads/question/extracted_imgs'
                ]:
                    src_img = os.path.join(alt_dir, q['img_file'])
                    if os.path.exists(src_img):
                        try:
                            shutil.copy2(src_img, dest_img)
                        except Exception:
                            pass
                        break

        clean_all_questions.append(q)

    all_questions = clean_all_questions
    
    # Range / filter
    range_type = payload.get('range_type', 'all') # 'all', 'preset', 'custom', 'page_range'
    page_range_text = payload.get('page_range_text') or payload.get('page_range', '')
    
    if range_type == 'page_range' or (page_range_text and range_type not in ['preset', 'custom']):
        selected_pages = parse_page_range(page_range_text)
        if selected_pages:
            filtered_by_page = [q for q in all_questions if q.get('page') in selected_pages or q.get('page_num') in selected_pages]
            questions = filtered_by_page if filtered_by_page else all_questions
        else:
            questions = all_questions
    elif range_type == 'preset':
        preset_start = int(payload.get('preset_start', 1)) - 1
        preset_count = int(payload.get('preset_count', 20))
        questions = all_questions[preset_start:preset_start + preset_count]
    elif range_type == 'custom':
        start_q = max(0, int(payload.get('custom_start', 1)) - 1)
        end_q = min(len(all_questions), int(payload.get('custom_end', len(all_questions))))
        questions = all_questions[start_q:end_q]
    else:
        questions = all_questions

    total_q = int(payload.get('total_questions', 20))
    total_q = min(len(questions), total_q)
    target_pages = max(1, int(payload.get('target_pages', 2)))
    
    shuffle = payload.get('shuffle', True)
    seed = payload.get('seed')
    if seed is not None and str(seed).strip() != "":
        try:
            seed = int(seed)
        except:
            seed = 42
    else:
        seed = 42 if shuffle else None

    # Allocate across pages
    part_b_enabled = payload.get('header', {}).get('part_b_enabled', False)
    part_c_enabled = payload.get('header', {}).get('part_c_enabled', False)
    has_written_parts = part_b_enabled or part_c_enabled

    if has_written_parts and target_pages >= 2:
        mcq_pages_count = target_pages - 1
        mcq_pages = allocate_questions(questions, total_q, mcq_pages_count, shuffle=shuffle, seed=seed)
        pages = mcq_pages + [[]]
    else:
        pages = allocate_questions(questions, total_q, target_pages, shuffle=shuffle, seed=seed)

    header = payload.get('header', {})
    bank_header_config = bank_data.get('header_config', {})
    default_header = {
        'enabled': True,
        'page1_only': True,
        'inst_name': bank_header_config.get('inst_name', 'FITTER, GITI.,VEERAKERLAMPUDUR.'),
        'test_title': bank_header_config.get('test_title', 'MONTHLY TEST - FIRST YEAR'),
        'session_text': bank_header_config.get('session_text', 'NOVEMBER 2026'),
        'date_text': bank_header_config.get('date_text', 'Date: ____________________'),
        'time_text': bank_header_config.get('time_text', 'Time: ____________________'),
        'reg_no_text': bank_header_config.get('reg_no_text', 'Register No.: ____________________'),
        'marks_text': bank_header_config.get('marks_text', 'Maximum Marks: 50'),
        'trade_text': bank_header_config.get('trade_text', 'TRADE: FITTER (1st SEM)'),
        'divider_char': bank_header_config.get('divider_char', '='),
        'include_instructions': bank_header_config.get('include_instructions', False),
        'instructions': bank_header_config.get('instructions', [
            '1. Answer all questions.',
            '2. Choose the correct answer for each multiple-choice question.',
            '3. Write answers neatly and clearly.',
            '4. Marks are indicated against each section.'
        ]),
        'part_a_title': bank_header_config.get('part_a_title', 'PART - A : MULTIPLE CHOICE QUESTIONS'),
        'part_a_subtitle': bank_header_config.get('part_a_subtitle', f'({total_q} x 1 = {total_q} Marks) - Answer all questions. Choose the correct option.'),
        'part_b_enabled': bank_header_config.get('part_b_enabled', False),
        'part_b_title': bank_header_config.get('part_b_title', 'PART - B : SHORT ANSWER QUESTIONS'),
        'part_b_subtitle': bank_header_config.get('part_b_subtitle', '(5 x 2 = 10 Marks) - Answer all questions.'),
        'part_b_questions': bank_header_config.get('part_b_questions', [
            'What is the purpose of a try square?',
            'State the use of a prick punch.',
            'Name four types of cold chisels.',
            'What is the least count of a metric vernier caliper?',
            'Explain the safety precautions while using a bench grinder.'
        ]),
        'part_c_enabled': bank_header_config.get('part_c_enabled', False),
        'part_c_title': bank_header_config.get('part_c_title', 'PART - C : DESCRIPTIVE ANSWER QUESTIONS'),
        'part_c_subtitle': bank_header_config.get('part_c_subtitle', '(4 x 5 = 20 Marks) - Answer all questions.'),
        'part_c_questions': bank_header_config.get('part_c_questions', [
            'Explain the construction and working principle of a micrometer with a neat sketch.',
            'Describe the different types of files according to their shapes and cut.',
            'What is heat treatment? Explain the hardening and tempering processes.',
            'Detail the procedure for filing a flat surface and checking flatness with a try square.'
        ])
    }
    for k, v in default_header.items():
        if k not in header:
            header[k] = v

    footer = payload.get('footer', {})
    if 'enabled' not in footer: footer['enabled'] = False
    if 'page_number' not in footer: footer['page_number'] = True
    if 'text' not in footer: footer['text'] = ''

    styling = payload.get('styling', {})
    if 'auto_fit' not in styling: styling['auto_fit'] = True
    if 'page_size' not in styling: styling['page_size'] = 'A4'
    if 'orientation' not in styling: styling['orientation'] = 'portrait'
    if 'landscape_columns' not in styling: styling['landscape_columns'] = True
    if 'page_border' not in styling: styling['page_border'] = False
    if 'show_marks_table' not in styling: styling['show_marks_table'] = False
    if 'end_marker' not in styling: styling['end_marker'] = False
    if 'end_marker_text' not in styling: styling['end_marker_text'] = '******************** END OF QUESTION PAPER ********************'
    if 'q_font_size' not in styling: styling['q_font_size'] = 11
    if 'opt_font_size' not in styling: styling['opt_font_size'] = 9.5
    if 'question_divider' not in styling: styling['question_divider'] = 'dashed'
    if 'options_layout' not in styling: styling['options_layout'] = '2col'
    if 'conditions_text' not in styling: styling['conditions_text'] = ''

    return {
        'pages': pages,
        'header': header,
        'footer': footer,
        'styling': styling,
        'total_questions': total_q,
        'target_pages': target_pages
    }

@app.route('/api/preview', methods=['POST'])
def preview():
    try:
        payload = request.json or {}
        paper_data = build_paper_data(payload)
        html_content = generate_html(paper_data, IMG_DIR)
        
        # Build answer key
        answer_key = []
        curr_q = 1
        for p_idx, page in enumerate(paper_data['pages']):
            for q in page:
                ans_opt = q.get('ans', '')
                ans_en = ''
                ans_ta = ''
                for o in q.get('options', []):
                    if o['opt'] == ans_opt:
                        ans_en = o['en']
                        ans_ta = o['ta']
                        break
                ans_disp = ans_en
                if ans_ta and ans_ta.lower() != ans_en.lower():
                    ans_disp += f" / {ans_ta}"
                answer_key.append({
                    'num': curr_q,
                    'orig_id': q.get('orig_id', curr_q),
                    'page': p_idx + 1,
                    'pdf_page': q.get('page', p_idx + 1),
                    'module': q.get('module', ''),
                    'q_en': q['q_en'],
                    'ans_opt': ans_opt,
                    'ans_text': ans_disp,
                    'has_img': bool(q.get('has_img')),
                    'img_file': q.get('img_file')
                })
                curr_q += 1

        stats = {
            'total_questions': paper_data['total_questions'],
            'target_pages': paper_data['target_pages'],
            'questions_per_page': [len(p) for p in paper_data['pages']],
            'diagrams_per_page': [sum(1 for q in p if q.get('has_img')) for p in paper_data['pages']]
        }

        return jsonify({
            'status': 'success',
            'html': html_content,
            'stats': stats,
            'answer_key': answer_key
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    try:
        payload = request.json or {}
        paper_data = build_paper_data(payload)
        html_content = generate_html(paper_data, IMG_DIR)
        
        file_id = uuid.uuid4().hex[:8]
        temp_html = os.path.join(EXPORTS_DIR, f"temp_{file_id}.html")
        output_pdf = os.path.join(EXPORTS_DIR, f"question_paper_{file_id}.pdf")
        
        try:
            page_count = compile_pdf(html_content, output_pdf, temp_html)
            if os.path.exists(temp_html):
                os.remove(temp_html)
                
            return send_file(
                output_pdf,
                as_attachment=True,
                download_name=f"Question_Paper_{paper_data['total_questions']}Q_{paper_data['target_pages']}Pages.pdf",
                mimetype='application/pdf'
            )
        except Exception as compile_err:
            print(f"Serverless headless Chrome note: {compile_err}")
            return jsonify({
                'status': 'fallback_print',
                'html': html_content,
                'message': 'Triggering browser vector PDF print engine.'
            }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/export/docx', methods=['POST'])
def export_docx():
    try:
        payload = request.json or {}
        paper_data = build_paper_data(payload)
        
        file_id = uuid.uuid4().hex[:8]
        output_docx = os.path.join(EXPORTS_DIR, f"question_paper_{file_id}.docx")
        
        from docx_generator import generate_docx
        generate_docx(paper_data, output_docx, IMG_DIR)
        
        return send_file(
            output_docx,
            as_attachment=True,
            download_name=f"Question_Paper_{paper_data['total_questions']}Q_{paper_data['target_pages']}Pages.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/questions/manual', methods=['POST'])
def add_manual_question():
    try:
        bank_id = request.form.get('bank_id', '').strip()
        if not bank_id or bank_id == 'new':
            bank_id = f"custom_manual_{uuid.uuid4().hex[:6]}.json"
        elif not bank_id.endswith('.json'):
            bank_id = f"{bank_id}.json"

        bank_path = find_bank_file(bank_id)
        if bank_path and os.path.exists(bank_path):
            bank_data = load_question_bank(bank_path)
        else:
            new_title = request.form.get('new_bank_name', 'Manual Question Bank').strip() or 'Manual Question Bank'
            trade_name = request.form.get('trade_name', 'Custom Trade').strip() or 'Custom Trade'
            bank_data = {
                "module_id": os.path.splitext(bank_id)[0],
                "module_name": new_title,
                "trade": trade_name,
                "modules": ["General"],
                "questions": []
            }

        questions = bank_data.get('questions', [])
        next_id = len(questions) + 1

        q_en = request.form.get('q_en', '').strip()
        if not q_en:
            return jsonify({'status': 'error', 'message': 'Question text (EN) is required.'}), 400

        q_ta = request.form.get('q_ta', '').strip()
        module = request.form.get('module', 'General').strip() or "General"
        subheading = request.form.get('subheading', '').strip()

        # Image attachment (optional)
        has_img = False
        img_filename = None
        img_file = request.files.get('image_file') or request.files.get('diagram_file')
        if img_file and img_file.filename != '':
            s_filename = secure_filename(img_file.filename)
            ext = os.path.splitext(s_filename)[1].lower() or '.png'
            img_filename = f"manual_{uuid.uuid4().hex[:8]}{ext}"
            img_save_path = os.path.join(CUSTOM_IMG_DIR, img_filename)
            img_file.save(img_save_path)
            has_img = True

        # Check options
        has_options = request.form.get('has_options', 'true').lower() in ['true', '1', 'yes']
        options_list = []
        ans = (request.form.get('correct_ans') or request.form.get('ans', 'A')).strip().upper()

        if has_options:
            opt_a_en = request.form.get('opt_a_en', '').strip()
            opt_a_ta = request.form.get('opt_a_ta', '').strip() or opt_a_en
            opt_b_en = request.form.get('opt_b_en', '').strip()
            opt_b_ta = request.form.get('opt_b_ta', '').strip() or opt_b_en
            opt_c_en = request.form.get('opt_c_en', '').strip()
            opt_c_ta = request.form.get('opt_c_ta', '').strip() or opt_c_en
            opt_d_en = request.form.get('opt_d_en', '').strip()
            opt_d_ta = request.form.get('opt_d_ta', '').strip() or opt_d_en

            if opt_a_en or opt_b_en:
                options_list = [
                    {"opt": "A", "en": opt_a_en, "ta": opt_a_ta},
                    {"opt": "B", "en": opt_b_en, "ta": opt_b_ta},
                    {"opt": "C", "en": opt_c_en, "ta": opt_c_ta},
                    {"opt": "D", "en": opt_d_en, "ta": opt_d_ta}
                ]

        q_obj = {
            "orig_id": next_id,
            "global_id": next_id,
            "module": module,
            "subheading": subheading,
            "q_en": q_en,
            "q_ta": q_ta if q_ta else q_en,
            "options": options_list,
            "ans": ans if options_list else "",
            "has_img": has_img,
            "img_file": img_filename,
            "is_manual": True
        }

        questions.append(q_obj)
        bank_data['questions'] = questions

        if module and module not in bank_data.get('modules', []):
            bank_data.setdefault('modules', []).append(module)

        save_bank_path = get_writable_bank_file(bank_id)
        with open(save_bank_path, 'w', encoding='utf-8') as f:
            json.dump(bank_data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'status': 'success',
            'question': q_obj,
            'bank_id': bank_id,
            'bank_name': bank_data.get('module_name'),
            'total_questions': len(questions)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/export/google-form', methods=['POST'])
def export_google_form():
    try:
        payload = request.json or {}
        paper_data = build_paper_data(payload)
        apps_script = generate_google_apps_script(paper_data)
        manual_text = generate_manual_form_text(paper_data)
        title = paper_data.get('header', {}).get('test_title', 'Google Form Question Paper')
        
        return jsonify({
            'status': 'success',
            'title': title,
            'total_questions': paper_data.get('total_questions', 0),
            'apps_script': apps_script,
            'manual_text': manual_text,
            'script_url': 'https://script.google.com/new'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

def parse_template_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    res = {
        'page_size': 'A4',
        'orientation': 'portrait',
        'page_border': False,
        'inst_name': 'FITTER, GITI.,VEERAKERLAMPUDUR.',
        'test_title': 'MONTHLY TEST - FIRST YEAR',
        'session_text': 'NOVEMBER 2026',
        'date_text': 'Date: ____________________',
        'time_text': 'Time: ____________________',
        'reg_no_text': 'Register No.: ____________________',
        'marks_text': 'Maximum Marks: 50',
        'divider_char': '=',
        'footer_text': '',
        'footer_enabled': True,
        'options_layout': '2col',
        'include_instructions': False,
        'instructions': [
            '1. Answer all questions.',
            '2. Choose the correct answer for each multiple-choice question.',
            '3. Write answers neatly and clearly.',
            '4. Marks are indicated against each section.'
        ],
        'part_a_title': 'PART - A : MULTIPLE CHOICE QUESTIONS',
        'part_a_subtitle': '(20 x 1 = 20 Marks) - Answer all questions. Choose the correct option.',
        'part_b_enabled': False,
        'part_b_title': 'PART - B : SHORT ANSWER QUESTIONS',
        'part_b_subtitle': '(5 x 2 = 10 Marks) - Answer all questions.',
        'part_b_questions': [
            'What is the purpose of a try square?',
            'State the use of a prick punch.',
            'Name four types of cold chisels.',
            'What is the least count of a metric vernier caliper?',
            'Explain the safety precautions while using a bench grinder.'
        ],
        'part_c_enabled': False,
        'part_c_title': 'PART - C : DESCRIPTIVE ANSWER QUESTIONS',
        'part_c_subtitle': '(4 x 5 = 20 Marks) - Answer all questions.',
        'part_c_questions': [
            'Explain the construction and working principle of a micrometer with a neat sketch.',
            'Describe the different types of files according to their shapes and cut.',
            'What is heat treatment? Explain the hardening and tempering processes.',
            'Detail the procedure for filing a flat surface and checking flatness with a try square.'
        ],
        'show_marks_table': False,
        'end_marker': False,
        'end_marker_text': '******************** END OF QUESTION PAPER ********************'
    }
    
    if ext == '.pdf':
        import pypdf, re
        reader = pypdf.PdfReader(file_path)
        page = reader.pages[0]
        box = page.mediabox
        w_mm = round(float(box.width) * 25.4 / 72, 1)
        h_mm = round(float(box.height) * 25.4 / 72, 1)
        
        res['orientation'] = 'landscape' if w_mm > h_mm else 'portrait'
        min_dim, max_dim = sorted([w_mm, h_mm])
        if abs(min_dim - 210) < 15 and abs(max_dim - 297) < 15:
            res['page_size'] = 'A4'
        elif abs(min_dim - 297) < 20 and abs(max_dim - 420) < 20:
            res['page_size'] = 'A3'
        elif abs(min_dim - 215.9) < 10 and abs(max_dim - 279.4) < 10:
            res['page_size'] = 'Letter'
        elif abs(min_dim - 215.9) < 10 and abs(max_dim - 355.6) < 10:
            res['page_size'] = 'Legal'
        elif abs(min_dim - 148) < 10 and abs(max_dim - 210) < 10:
            res['page_size'] = 'A5'
            
        full_text = ''
        for p in reader.pages:
            full_text += (p.extract_text() or '') + '\n'
            try:
                stream = p.get_contents().get_data()
                if b' re S' in stream or b' re f' in stream or b' re B' in stream:
                    res['page_border'] = True
            except:
                pass
                
        raw_lines = [l.strip() for l in full_text.splitlines() if l.strip()]
        clean_lines = [l for l in raw_lines if not re.match(r'^page\s*\d+', l, re.I)]
        
        if clean_lines:
            res['inst_name'] = clean_lines[0]
        if len(clean_lines) > 1:
            res['test_title'] = clean_lines[1]
        if len(clean_lines) > 2 and re.search(r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|202\d|203\d|SEMESTER|YEAR)', clean_lines[2], re.I):
            res['session_text'] = clean_lines[2]
            
        for l in clean_lines:
            if re.search(r'date[:\s]', l, re.I) and not re.search(r'marks[:\s]', l, re.I):
                res['date_text'] = l
            elif re.search(r'date[:\s]', l, re.I) and re.search(r'marks[:\s]', l, re.I):
                parts = re.split(r'marks[:\s]', l, flags=re.I)
                res['date_text'] = parts[0].strip()
                res['marks_text'] = 'MARKS: ' + parts[1].strip()
            if re.search(r'time[:\s]', l, re.I):
                res['time_text'] = l
            if re.search(r'register\s*no|reg\s*no', l, re.I):
                res['reg_no_text'] = l
            if re.search(r'maximum\s*marks|total\s*marks|marks:', l, re.I):
                res['marks_text'] = l

        # General Instructions
        if 'GENERAL INSTRUCTIONS' in full_text.upper():
            res['include_instructions'] = True
            res['page_border'] = True
            idx = full_text.upper().find('GENERAL INSTRUCTIONS')
            sub = full_text[idx:].split('PART')[0]
            ins = [re.sub(r'^\d+[\.\)]\s*', '', l.strip()) for l in sub.splitlines() if re.match(r'^\d+[\.\)]', l.strip())]
            if ins:
                res['instructions'] = [f"{i+1}. {txt}" for i, txt in enumerate(ins)]

        # Part A
        if 'PART - A' in full_text or 'PART A' in full_text:
            res['page_border'] = True
            m_a = re.search(r'(PART\s*[-–]\s*A[^\n]*)\n([^\n]*)', full_text, re.I)
            if m_a:
                res['part_a_title'] = m_a.group(1).strip()
                if '(' in m_a.group(2):
                    res['part_a_subtitle'] = m_a.group(2).strip()

        # Part B
        if 'PART - B' in full_text or 'PART B' in full_text:
            res['part_b_enabled'] = True
            m_b = re.search(r'(PART\s*[-–]\s*B[^\n]*)\n([^\n]*)', full_text, re.I)
            if m_b:
                res['part_b_title'] = m_b.group(1).strip()
                if '(' in m_b.group(2):
                    res['part_b_subtitle'] = m_b.group(2).strip()
            idx_b = full_text.find('PART - B') if 'PART - B' in full_text else full_text.find('PART B')
            sub_b = full_text[idx_b:].split('PART - C')[0].split('PART C')[0].split('MARKS DISTRIBUTION')[0]
            qs_b = [re.sub(r'^\d+[\.\)]\s*', '', l.strip().replace('_', '')) for l in sub_b.splitlines() if re.match(r'^\d+[\.\)]', l.strip())]
            qs_b = [q for q in qs_b if q]
            if qs_b:
                res['part_b_questions'] = qs_b

        # Part C
        if 'PART - C' in full_text or 'PART C' in full_text:
            res['part_c_enabled'] = True
            m_c = re.search(r'(PART\s*[-–]\s*C[^\n]*)\n([^\n]*)', full_text, re.I)
            if m_c:
                res['part_c_title'] = m_c.group(1).strip()
                if '(' in m_c.group(2):
                    res['part_c_subtitle'] = m_c.group(2).strip()
            idx_c = full_text.find('PART - C') if 'PART - C' in full_text else full_text.find('PART C')
            sub_c = full_text[idx_c:].split('MARKS DISTRIBUTION')[0].split('END OF QUESTION')[0]
            qs_c = [re.sub(r'^\d+[\.\)]\s*', '', l.strip().replace('_', '')) for l in sub_c.splitlines() if re.match(r'^\d+[\.\)]', l.strip())]
            qs_c = [q for q in qs_c if q]
            if qs_c:
                res['part_c_questions'] = qs_c

        # Marks Distribution Table
        if 'MARKS DISTRIBUTION' in full_text.upper():
            res['show_marks_table'] = True

        # End of Question Paper
        if 'END OF QUESTION PAPER' in full_text.upper():
            res['end_marker'] = True
            res['end_marker_text'] = '******************** END OF QUESTION PAPER ********************'

    elif ext == '.docx':
        import docx, re
        doc = docx.Document(file_path)
        sec = doc.sections[0]
        w_in = sec.page_width.inches
        h_in = sec.page_height.inches
        res['orientation'] = 'landscape' if w_in > h_in else 'portrait'
        min_dim, max_dim = sorted([w_in, h_in])
        if abs(min_dim - 8.27) < 0.5 and abs(max_dim - 11.69) < 0.5:
            res['page_size'] = 'A4'
        elif abs(min_dim - 11.69) < 0.8 and abs(max_dim - 16.54) < 0.8:
            res['page_size'] = 'A3'
        elif abs(min_dim - 8.5) < 0.4 and abs(max_dim - 11.0) < 0.4:
            res['page_size'] = 'Letter'
        elif abs(min_dim - 8.5) < 0.4 and abs(max_dim - 14.0) < 0.4:
            res['page_size'] = 'Legal'
        elif abs(min_dim - 5.83) < 0.4 and abs(max_dim - 8.27) < 0.4:
            res['page_size'] = 'A5'
            
        paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if len(paras) > 0: res['inst_name'] = paras[0]
        if len(paras) > 1: res['test_title'] = paras[1]
        
    return res

@app.route('/api/template/analyze', methods=['POST'])
def analyze_template_endpoint():
    try:
        if 'template_file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No template file provided'}), 400
        file = request.files['template_file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
            
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.pdf', '.docx']:
            return jsonify({'status': 'error', 'message': 'Only PDF and DOCX format files are supported'}), 400
            
        temp_path = os.path.join(UPLOADS_DIR, f"template_{uuid.uuid4().hex[:8]}_{filename}")
        file.save(temp_path)
        
        parsed = parse_template_file(temp_path)
        return jsonify({
            'status': 'success',
            'filename': filename,
            'template': parsed
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/template/presets', methods=['GET'])
def get_template_presets():
    presets = [
        {
            'id': 'giti_government_formal_exam',
            'name': 'Government ITI / Board Examination Model',
            'desc': 'Complete official format: Outer Page Border, General Instructions, Date/Time/RegNo Grid, Parts A/B/C & Marks Distribution Table',
            'page_size': 'A4',
            'orientation': 'portrait',
            'page_border': True,
            'inst_name': 'FITTER, G.I.T.I., VEERAKERLAMPUDUR',
            'test_title': 'MONTHLY TEST - FIRST YEAR',
            'session_text': 'NOVEMBER 2026',
            'date_text': 'Date: ____________________',
            'time_text': 'Time: ____________________',
            'reg_no_text': 'Register No.: ____________________',
            'marks_text': 'Maximum Marks: 50',
            'divider_char': '=',
            'question_divider': 'solid',
            'options_layout': '4col',
            'include_instructions': True,
            'instructions': [
                '1. Answer all questions.',
                '2. Choose the correct answer for each multiple-choice question.',
                '3. Write answers neatly and clearly.',
                '4. Marks are indicated against each section.'
            ],
            'part_a_title': 'PART - A : MULTIPLE CHOICE QUESTIONS',
            'part_a_subtitle': '(20 x 1 = 20 Marks) - Answer all questions. Choose the correct option.',
            'part_b_enabled': True,
            'part_b_title': 'PART - B : SHORT ANSWER QUESTIONS',
            'part_b_subtitle': '(5 x 2 = 10 Marks) - Answer all questions.',
            'part_b_questions': [
                'What is the purpose of a try square?',
                'State the use of a prick punch.',
                'Name four types of cold chisels.',
                'What is the least count of a metric vernier caliper?',
                'Explain the safety precautions while using a bench grinder.'
            ],
            'part_c_enabled': True,
            'part_c_title': 'PART - C : DESCRIPTIVE ANSWER QUESTIONS',
            'part_c_subtitle': '(4 x 5 = 20 Marks) - Answer all questions.',
            'part_c_questions': [
                'Explain the construction and working principle of a micrometer with a neat sketch.',
                'Describe the different types of files according to their shapes and cut.',
                'What is heat treatment? Explain the hardening and tempering processes.',
                'Detail the procedure for filing a flat surface and checking flatness with a try square.'
            ],
            'show_marks_table': True,
            'end_marker': True,
            'end_marker_text': '******************** END OF QUESTION PAPER ********************',
            'footer_enabled': True,
            'footer_page_number': True
        },
        {
            'id': 'veerakerlampudur_standard',
            'name': 'GITI Veerakerlampudur Standard (A4 Portrait)',
            'desc': 'Traditional 2-column options with divider line and header metadata',
            'page_size': 'A4',
            'orientation': 'portrait',
            'inst_name': 'FITTER, GITI.,VEERAKERLAMPUDUR.',
            'test_title': 'MONTHLY TEST - FIRST YEAR',
            'date_text': 'DATE: ______________',
            'marks_text': 'MARKS: ______',
            'divider_char': '=',
            'question_divider': 'dashed',
            'options_layout': '2col'
        },
        {
            'id': 'ncvt_landscape_2col',
            'name': 'NCVT / NIMI Exam (A4 Landscape 2-Column)',
            'desc': 'Horizontal landscape layout with 2 balanced columns per page',
            'page_size': 'A4',
            'orientation': 'landscape',
            'inst_name': 'NATIONAL COUNCIL FOR VOCATIONAL TRAINING (NCVT)',
            'test_title': 'ALL INDIA TRADE TEST (AITT) - FIRST YEAR',
            'date_text': 'TIME: 2 HOURS',
            'marks_text': 'TOTAL MARKS: 50',
            'divider_char': '=',
            'question_divider': 'solid',
            'options_layout': '2col'
        },
        {
            'id': 'polytechnic_a3_large',
            'name': 'Large Format Workshop Exam (A3 Portrait)',
            'desc': 'High-capacity A3 examination layout for large batches',
            'page_size': 'A3',
            'orientation': 'portrait',
            'inst_name': 'DEPARTMENT OF TECHNICAL EDUCATION & TRAINING',
            'test_title': 'SEMESTER EXAMINATION',
            'date_text': 'DATE: ______________',
            'marks_text': 'MARKS: 100',
            'divider_char': '=',
            'question_divider': 'solid',
            'options_layout': '4col'
        },
        {
            'id': 'weekly_quiz_a5',
            'name': 'Compact Weekly Test (A5 Booklet)',
            'desc': 'Pocket-sized booklet format ideal for quick 10-20 question tests',
            'page_size': 'A5',
            'orientation': 'portrait',
            'inst_name': 'INDUSTRIAL TRAINING INSTITUTE',
            'test_title': 'WEEKLY ASSESSMENT TEST',
            'date_text': 'DATE: ______________',
            'marks_text': 'MARKS: 20',
            'divider_char': '-',
            'question_divider': 'dashed',
            'options_layout': '2col'
        }
    ]
    return jsonify({'presets': presets})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"Starting Question Paper Generator App on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
