import os
import json
import random
import math

def load_question_bank(bank_path):
    if os.path.exists(bank_path):
        with open(bank_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def allocate_questions(questions_list, total_q, target_pages, shuffle=True, seed=None, start_idx=0):
    # Slice or select
    if start_idx < len(questions_list):
        subset = questions_list[start_idx:start_idx + total_q]
    else:
        subset = questions_list[:total_q]
        
    if len(subset) < total_q:
        # Loop or pad if total requested is larger than available
        subset = (questions_list * (math.ceil(total_q / len(questions_list))))[:total_q]
        
    selected = list(subset)
    
    if shuffle:
        if seed is not None:
            random.seed(seed)
        else:
            random.seed()
        random.shuffle(selected)
        
    # Split across target pages evenly
    # e.g., 20 questions in 2 pages -> [10, 10]
    # 25 questions in 3 pages -> [9, 8, 8]
    pages = []
    base_per_page = total_q // target_pages
    remainder = total_q % target_pages
    
    curr = 0
    for p in range(target_pages):
        count_for_p = base_per_page + (1 if p < remainder else 0)
        page_slice = selected[curr:curr + count_for_p]
        pages.append(page_slice)
        curr += count_for_p
        
    return pages
