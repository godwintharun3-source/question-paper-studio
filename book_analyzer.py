"""
book_analyzer.py - Subject Book & Textbook to Question Paper Synthesizer
Generates Part A (MCQ 1-Mark), Part B (2/3 Marks Short Answer), and Part C (10/16 Marks Descriptive)
questions from raw subject book / textbook PDFs.
"""

import os
import re
import cv2
import json
import uuid
import pdfplumber
import numpy as np

STOPWORDS = {
    'actually', 'based', 'every', 'each', 'this', 'that', 'these', 'those', 'when',
    'which', 'where', 'what', 'there', 'their', 'figure', 'table', 'note', 'step',
    'moreover', 'nevertheless', 'fortunately', 'getting', 'october', 'november',
    'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
    'september', 'december', 'chapter', 'section', 'author', 'editor', 'press',
    'first', 'second', 'third', 'fourth', 'fifth', 'about', 'above', 'after',
    'again', 'against', 'almost', 'along', 'also', 'although', 'always', 'among',
    'another', 'because', 'before', 'behind', 'below', 'between', 'both', 'during',
    'either', 'enough', 'further', 'having', 'however', 'itself', 'neither',
    'nothing', 'perhaps', 'rather', 'really', 'several', 'should', 'similar',
    'simple', 'simply', 'since', 'some', 'someone', 'something', 'sometimes',
    'somewhere', 'still', 'such', 'than', 'thank', 'thanks', 'then', 'thereby',
    'therefore', 'though', 'through', 'throughout', 'together', 'toward', 'towards',
    'under', 'unless', 'until', 'upon', 'using', 'various', 'very', 'well', 'were',
    'what', 'whatever', 'whether', 'while', 'whose', 'without', 'would', 'david', 'rose'
}

def parse_page_range(range_str):
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

def extract_text_and_diagrams_from_book(pdf_path, img_dir, bank_id, selected_pages=None):
    """
    Extracts text paragraphs, headings, key terms, definitions, and diagrams from the book.
    """
    os.makedirs(img_dir, exist_ok=True)
    extracted_data = {
        'chapters': [],
        'paragraphs': [],
        'key_definitions': [],
        'lists': [],
        'diagrams': [],
        'technical_terms': set()
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        total_p = len(pdf.pages)
        pages_to_process = [
            (i, p) for i, p in enumerate(pdf.pages)
            if not selected_pages or (i + 1) in selected_pages
        ]
        
        for p_idx, page in pages_to_process:
            pno = p_idx + 1
            raw_text = page.extract_text() or ""
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            
            # Detect chapter / topic headings
            for line in lines:
                if re.match(r'^(?:CHAPTER|UNIT|MODULE|SECTION|\d+[\.\s]+[A-Z])\s+[A-Z0-9]', line, re.I) or (line.isupper() and 6 < len(line) < 60):
                    clean_heading = re.sub(r'^[#\d\.\-\s]+', '', line).strip()
                    if clean_heading and clean_heading not in extracted_data['chapters']:
                        extracted_data['chapters'].append(clean_heading)
            
            # Extract paragraphs and definitions
            sentences = re.split(r'(?<=[.!?])\s+', raw_text)
            for s in sentences:
                s_clean = " ".join(s.split()).strip()
                if len(s_clean) < 25 or len(s_clean) > 300:
                    continue
                
                # Check definition / function patterns
                if re.search(r'\b(is defined as|is used (?:to|for)|purpose of|principle of|consists of|classified into|types of|is known as|refers to|measured by|least count of|function of)\b', s_clean, re.I):
                    extracted_data['key_definitions'].append({'page': pno, 'text': s_clean})
                else:
                    extracted_data['paragraphs'].append({'page': pno, 'text': s_clean})
                    
                # Extract technical terms (Compound noun phrases)
                terms = re.findall(r'\b[A-Z][a-zA-Z0-9\-_]+(?:\s+[A-Z][a-zA-Z0-9\-_]+)*\b', s_clean)
                for t in terms:
                    clean_t = t.strip()
                    first_word = clean_t.split()[0].lower()
                    last_word = clean_t.split()[-1].lower()
                    if len(clean_t) > 3 and first_word not in STOPWORDS and last_word not in STOPWORDS:
                        extracted_data['technical_terms'].add(clean_t)

            # Extract diagrams / figures if present on page
            if hasattr(page, 'curves') and hasattr(page, 'lines'):
                diag_curves = [c for c in page.curves if c['x1'] - c['x0'] > 15 and c['bottom'] - c['top'] > 15]
                diag_lines = [l for l in page.lines if l['x1'] - l['x0'] > 15 or l['bottom'] - l['top'] > 15]
                if len(diag_curves) + len(diag_lines) >= 15:
                    all_x = [c['x0'] for c in diag_curves] + [c['x1'] for c in diag_curves]
                    all_y = [c['top'] for c in diag_curves] + [c['bottom'] for c in diag_curves]
                    if all_x and all_y:
                        xmin, xmax = max(0, min(all_x) - 5), min(page.width, max(all_x) + 5)
                        ymin, ymax = max(0, min(all_y) - 5), min(page.height, max(all_y) + 5)
                        if (xmax - xmin) > 40 and (ymax - ymin) > 40:
                            try:
                                page_img = page.to_image(resolution=150).original
                                scale_x = page_img.width / page.width
                                scale_y = page_img.height / page.height
                                crop_img = page_img.crop((
                                    int(xmin * scale_x), int(ymin * scale_y),
                                    int(xmax * scale_x), int(ymax * scale_y)
                                ))
                                diag_fname = f"{bank_id}_p{pno:02d}_fig.png"
                                crop_img.save(os.path.join(img_dir, diag_fname))
                                extracted_data['diagrams'].append({
                                    'page': pno,
                                    'file': diag_fname,
                                    'bbox': (xmin, ymin, xmax, ymax)
                                })
                            except Exception:
                                pass

    # Sort terms by length (compound phrases first)
    valid_terms = [t for t in extracted_data['technical_terms'] if t.lower() not in STOPWORDS]
    valid_terms.sort(key=lambda x: (-len(x.split()), -len(x)))
    extracted_data['technical_terms'] = valid_terms
    return extracted_data

def synthesize_questions_from_book(extracted_data, bank_id, subject_title="Subject Theory", config=None):
    """
    Synthesizes MCQs (1 mark), Short Answer Questions (2/3 marks), and Descriptive Questions (10/16 marks).
    """
    if config is None:
        config = {}
        
    mcq_count = int(config.get('mcq_count', 20))
    short_count = int(config.get('short_count', 5))
    long_count = int(config.get('long_count', 3))
    short_marks = int(config.get('short_marks', 2))
    long_marks = int(config.get('long_marks', 16))
    paper_format = config.get('paper_format', 'combined') # 'combined', 'mcq_only', 'short_only', 'long_only'
    
    terms = extracted_data['technical_terms']
    definitions = extracted_data['key_definitions']
    paragraphs = extracted_data['paragraphs']
    chapters = extracted_data['chapters'] if extracted_data['chapters'] else [subject_title]
    diagrams = extracted_data['diagrams']
    
    if not terms:
        terms = [
            "Precision Measurement Tool", "Vernier Caliper", "Micrometer", "Try Square",
            "Bench Vice", "Cold Chisel", "Marking Punch", "Surface Gauge", "Angle Plate",
            "V-Block", "Dial Test Indicator", "Feeler Gauge", "Standard Wire Gauge"
        ]
        
    # --- 1. Synthesize MCQs (Part A) ---
    mcq_questions = []
    used_stems = set()
    
    # 1.1 Diagram based MCQs
    for d in diagrams:
        if len(mcq_questions) >= mcq_count:
            break
        target_term = terms[len(mcq_questions) % len(terms)]
        pool = [t for t in terms if t != target_term]
        import random
        random.seed(len(mcq_questions) + 11)
        distractors = random.sample(pool, min(3, len(pool))) if len(pool) >= 3 else ["Dial Gauge", "Chisel", "Punch"]
        opts_list = [target_term] + distractors[:3]
        random.shuffle(opts_list)
        ans_char = chr(65 + opts_list.index(target_term))
        
        q_obj = {
            'orig_id': len(mcq_questions) + 1,
            'global_id': len(mcq_questions) + 1,
            'module': chapters[0] if chapters else subject_title,
            'page': d['page'],
            'q_en': f"Identify the technical equipment / tool shown in the illustration.",
            'q_ta': f"படத்தில் காட்டப்பட்டுள்ள தொழில்நுட்ப கருவி / சாதனத்தின் பெயர் என்ன?",
            'options': [
                {'opt': chr(65 + i), 'en': opts_list[i], 'ta': opts_list[i]}
                for i in range(4)
            ],
            'ans': ans_char,
            'has_img': True,
            'img_file': d['file']
        }
        mcq_questions.append(q_obj)
        used_stems.add(q_obj['q_en'])

    # 1.2 Definition / Function based MCQs
    for defn in definitions:
        if len(mcq_questions) >= mcq_count:
            break
        text = defn['text']
        m = re.search(r'([A-Z][a-zA-Z0-9\s]{2,30})\s+(?:is used to|is used for|is defined as|purpose of is to|is a tool used for)\s+([^.]+)', text, re.I)
        if m:
            subject = m.group(1).strip()
            predicate = m.group(2).strip()
            if len(subject.split()) <= 4 and subject.lower() not in STOPWORDS:
                q_en = f"What is the primary function / purpose of {subject}?"
                q_ta = f"{subject}-ன் முக்கிய பயன்பாடு / செயல்பாடு என்ன?"
                if q_en not in used_stems:
                    ans_text = predicate[:75].strip()
                    distractors = [
                        f"Holding and clamping workpieces securely during machining",
                        f"Measuring internal and external dimensions with high precision",
                        f"Cutting, shaping, and chipping metals in workshop operations",
                        f"Marking accurate reference lines and datum surfaces"
                    ]
                    distractors = [d for d in distractors if d.lower() != ans_text.lower()][:3]
                    opts = [ans_text] + distractors
                    import random
                    random.seed(len(mcq_questions) + 55)
                    random.shuffle(opts)
                    ans_char = chr(65 + opts.index(ans_text))
                    
                    mcq_questions.append({
                        'orig_id': len(mcq_questions) + 1,
                        'global_id': len(mcq_questions) + 1,
                        'module': chapters[len(mcq_questions) % len(chapters)],
                        'page': defn['page'],
                        'q_en': q_en,
                        'q_ta': q_ta,
                        'options': [
                            {'opt': chr(65 + i), 'en': opts[i], 'ta': opts[i]}
                            for i in range(4)
                        ],
                        'ans': ans_char,
                        'has_img': False,
                        'img_file': None
                    })
                    used_stems.add(q_en)

    # 1.3 Term based MCQs to reach target count
    term_idx = 0
    templates_mcq = [
        ("Which tool / instrument is primarily employed for operations involving {t}?", "{t} பணிகளுக்கு பயன்படும் முதன்மையான கருவி / சாதனம் எது?"),
        ("What is the major technical characteristic or purpose of {t}?", "{t}-ன் முக்கிய தொழில்நுட்ப பண்பு அல்லது நோக்கம் என்ன?"),
        ("In standard engineering practice, {t} is primarily utilized for which function?", "பொறியியல் நடைமுறையில் {t} எந்த பயன்பாட்டிற்கு பயன்படுகிறது?")
    ]
    
    while len(mcq_questions) < mcq_count and term_idx < len(terms):
        t = terms[term_idx]
        term_idx += 1
        tmpl_en, tmpl_ta = templates_mcq[term_idx % len(templates_mcq)]
        q_en = tmpl_en.format(t=t)
        q_ta = tmpl_ta.format(t=t)
        if q_en in used_stems:
            continue
            
        pool = [other for other in terms if other != t]
        import random
        random.seed(term_idx * 23)
        distractors = random.sample(pool, min(3, len(pool))) if len(pool) >= 3 else ["Standard Reference Gauge", "Precision Surface Plate", "Universal Bevel Protractor"]
        opts = [t] + distractors[:3]
        random.shuffle(opts)
        ans_char = chr(65 + opts.index(t))
        
        mcq_questions.append({
            'orig_id': len(mcq_questions) + 1,
            'global_id': len(mcq_questions) + 1,
            'module': chapters[len(mcq_questions) % len(chapters)],
            'page': (term_idx % 25) + 1,
            'q_en': q_en,
            'q_ta': q_ta,
            'options': [
                {'opt': chr(65 + i), 'en': opts[i], 'ta': opts[i]}
                for i in range(4)
            ],
            'ans': ans_char,
            'has_img': False,
            'img_file': None
        })
        used_stems.add(q_en)

    # --- 2. Synthesize Part B (Short Answer - 2 / 3 Marks) ---
    short_questions = []
    short_templates = [
        "Define {term} and state its primary industrial application.",
        "State any two essential safety precautions while working with {term}.",
        "What is the principle, accuracy, and least count of {term}?",
        "Mention any two key advantages of using {term} in modern manufacturing.",
        "List four common defects observed in {term} and state their preventive measures.",
        "Differentiate between {term1} and {term2} in terms of operation, construction, and accuracy."
    ]
    
    for i in range(short_count):
        t1 = terms[i % len(terms)]
        t2 = terms[(i + 3) % len(terms)]
        tmpl = short_templates[i % len(short_templates)]
        q_text = tmpl.format(term=t1, term1=t1, term2=t2)
        short_questions.append(q_text)

    # --- 3. Synthesize Part C (Long Answer / Descriptive - 10 / 16 Marks) ---
    long_questions = []
    long_templates = [
        "Explain with a neat labeled sketch the construction, working principle, and applications of {term}.",
        "Describe in detail the various types and classifications of {term} with suitable diagrams, specifications, and industrial safety procedures.",
        "Explain the complete step-by-step operational procedure for {term}, including preparation, setting, inspection methods, and safety precautions.",
        "(a) Explain the working principle and construction of {term} with a neat sketch. \n(OR)\n(b) Discuss the applications, maintenance, and inspection procedure for {term_alt}."
    ]
    
    for i in range(long_count):
        t = terms[(i * 2 + 1) % len(terms)]
        t_alt = terms[(i * 2 + 2) % len(terms)]
        tmpl = long_templates[i % len(long_templates)]
        q_text = tmpl.format(term=t, term_alt=t_alt)
        long_questions.append(q_text)

    # Calculate Marks based on paper_format
    if paper_format == 'mcq_only':
        short_count = 0
        long_count = 0
        total_mcq_marks = len(mcq_questions) * 1
        grand_total_marks = total_mcq_marks
    elif paper_format == 'short_only':
        mcq_questions = []
        long_count = 0
        grand_total_marks = short_count * short_marks
    elif paper_format == 'long_only':
        mcq_questions = []
        short_count = 0
        grand_total_marks = long_count * long_marks
    else: # 'combined'
        total_mcq_marks = len(mcq_questions) * 1
        total_short_marks = short_count * short_marks
        total_long_marks = long_count * long_marks
        grand_total_marks = total_mcq_marks + total_short_marks + total_long_marks

    instructions = []
    if len(mcq_questions) > 0:
        instructions.append(f'1. Answer all questions in Part-A ({len(mcq_questions)} x 1 = {len(mcq_questions)} Marks).')
    if short_count > 0:
        instructions.append(f'2. Answer all questions in Part-B ({short_count} x {short_marks} = {short_count * short_marks} Marks).')
    if long_count > 0:
        instructions.append(f'3. Answer all questions in Part-C ({long_count} x {long_marks} = {long_count * long_marks} Marks - Neat sketches carry marks).')
    instructions.append('4. Write all answers neatly and clearly.')

    header_config = {
        'enabled': True,
        'page1_only': True,
        'inst_name': 'GOVERNMENT INDUSTRIAL TRAINING INSTITUTE',
        'test_title': f'{subject_title.upper()} - SEMESTER EXAMINATION',
        'session_text': 'ACADEMIC YEAR 2026',
        'date_text': 'Date: ____________________',
        'time_text': 'Time: 2 Hours 30 Mins',
        'reg_no_text': 'Register No.: ____________________',
        'marks_text': f'Maximum Marks: {grand_total_marks}',
        'trade_text': f'SUBJECT: {subject_title.upper()}',
        'divider_char': '=',
        'include_instructions': True,
        'instructions': instructions,
        'part_a_title': 'PART - A : OBJECTIVE / MULTIPLE CHOICE QUESTIONS',
        'part_a_subtitle': f'({len(mcq_questions)} x 1 = {len(mcq_questions)} Marks) - Answer all questions. Choose the correct option.',
        'part_b_enabled': short_count > 0,
        'part_b_title': f'PART - B : SHORT ANSWER QUESTIONS ({short_marks} MARKS EACH)',
        'part_b_subtitle': f'({short_count} x {short_marks} = {short_count * short_marks} Marks) - Answer all questions.',
        'part_b_questions': short_questions[:short_count],
        'part_c_enabled': long_count > 0,
        'part_c_title': f'PART - C : DESCRIPTIVE / ESSAY QUESTIONS ({long_marks} MARKS EACH)',
        'part_c_subtitle': f'({long_count} x {long_marks} = {long_count * long_marks} Marks) - Answer with neat sketches.',
        'part_c_questions': long_questions[:long_count]
    }

    bank_output = {
        'module_id': bank_id,
        'module_name': f"{subject_title} (From Subject Book)",
        'trade': subject_title,
        'modules': chapters,
        'questions': mcq_questions,
        'header_config': header_config,
        'short_questions': short_questions[:short_count],
        'long_questions': long_questions[:long_count],
        'grand_total_marks': grand_total_marks
    }
    
    return bank_output
