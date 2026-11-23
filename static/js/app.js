// Question Paper Studio Client Logic

let currentPayload = {
  bank_id: 'fitter_mod2_basic_fitting.json',
  range_type: 'preset',
  preset_start: 1,
  preset_count: 20,
  page_range_text: '',
  total_questions: 20,
  target_pages: 2,
  shuffle: true,
  seed: 42,
  header: {
    enabled: true,
    page1_only: true,
    inst_name: 'FITTER, GITI.,VEERAKERLAMPUDUR.',
    test_title: 'MONTHLY TEST - FIRST YEAR',
    session_text: 'NOVEMBER 2026',
    date_text: 'Date: ____________________',
    time_text: 'Time: ____________________',
    reg_no_text: 'Register No.: ____________________',
    marks_text: 'Maximum Marks: 50',
    trade_text: 'TRADE: FITTER (1st SEM)',
    divider_char: '=',
    include_instructions: false,
    instructions: [
      '1. Answer all questions.',
      '2. Choose the correct answer for each multiple-choice question.',
      '3. Write answers neatly and clearly.',
      '4. Marks are indicated against each section.'
    ],
    part_a_title: 'PART - A : MULTIPLE CHOICE QUESTIONS',
    part_a_subtitle: '(20 x 1 = 20 Marks) - Answer all questions. Choose the correct option.',
    part_b_enabled: false,
    part_b_title: 'PART - B : SHORT ANSWER QUESTIONS',
    part_b_subtitle: '(5 x 2 = 10 Marks) - Answer all questions.',
    part_b_questions: [
      'What is the purpose of a try square?',
      'State the use of a prick punch.',
      'Name four types of cold chisels.',
      'What is the least count of a metric vernier caliper?',
      'Explain the safety precautions while using a bench grinder.'
    ],
    part_c_enabled: false,
    part_c_title: 'PART - C : DESCRIPTIVE ANSWER QUESTIONS',
    part_c_subtitle: '(4 x 5 = 20 Marks) - Answer all questions.',
    part_c_questions: [
      'Explain the construction and working principle of a micrometer with a neat sketch.',
      'Describe the different types of files according to their shapes and cut.',
      'What is heat treatment? Explain the hardening and tempering processes.',
      'Detail the procedure for filing a flat surface and checking flatness with a try square.'
    ]
  },
  footer: {
    enabled: false,
    page_number: true,
    text: ''
  },
  styling: {
    auto_fit: true,
    page_size: 'A4',
    orientation: 'portrait',
    landscape_columns: true,
    page_border: false,
    show_marks_table: false,
    end_marker: false,
    end_marker_text: '******************** END OF QUESTION PAPER ********************',
    q_font_size: 11,
    opt_font_size: 9.5,
    question_divider: 'dashed',
    options_layout: '2col',
    language_mode: 'bilingual',
    conditions_text: ''
  }
};

let currentZoom = 1.0;
const PAGE_DIMENSIONS_PX = {
  'A4': { portrait: { w: 794, h: 1123 }, landscape: { w: 1123, h: 794 } },
  'A3': { portrait: { w: 1123, h: 1587 }, landscape: { w: 1587, h: 1123 } },
  'Letter': { portrait: { w: 816, h: 1056 }, landscape: { w: 1056, h: 816 } },
  'Legal': { portrait: { w: 816, h: 1344 }, landscape: { w: 1344, h: 816 } },
  'A5': { portrait: { w: 559, h: 794 }, landscape: { w: 794, h: 559 } }
};

let currentAnswerKey = [];

// Register Service Worker for PWA Mobile & Web App
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js').then((reg) => {
      console.log('QP Studio ServiceWorker registered:', reg.scope);
    }).catch((err) => {
      console.log('QP Studio ServiceWorker error:', err);
    });
  });
}

// PWA Install Prompt (Android/Chrome/Edge)
let deferredInstallPrompt = null;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  const btnInstall = document.getElementById('btn-install-app');
  if (btnInstall) {
    btnInstall.classList.remove('hidden');
    btnInstall.onclick = async () => {
      if (deferredInstallPrompt) {
        deferredInstallPrompt.prompt();
        const choice = await deferredInstallPrompt.userChoice;
        if (choice.outcome === 'accepted') {
          btnInstall.classList.add('hidden');
        }
        deferredInstallPrompt = null;
      }
    };
  }
});

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  setupUploadModal();
  setupSubjectBookModal();
  setupManualQuestionModal();
  setupGoogleFormModal();
  setupFormatModal();
  loadQuestionBanks();
  updateIframeDimensions();
  updatePreview();
  setTimeout(() => {
    if (window.innerWidth < 768) {
      fitWidth();
    } else {
      fitPage();
    }
  }, 350);

  // Responsive resize
  window.addEventListener('resize', () => {
    const viewport = document.getElementById('tab-content-preview');
    const iframe = document.getElementById('preview-frame');
    if (viewport && iframe) {
      const availableWidth = viewport.clientWidth - 40;
      const iframeW = parseFloat(iframe.style.width) || 794;
      if (availableWidth < iframeW * currentZoom) {
        fitWidth();
      }
    }
  });
});

function setupEventListeners() {
  // Preset buttons & Page Range
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.preset-btn').forEach(b => {
        b.classList.remove('border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-semibold', 'border-purple-600', 'bg-purple-100', 'text-purple-800');
        b.classList.add('border-gray-300', 'text-gray-700');
      });

      const rangeWrapper = document.getElementById('page-range-wrapper');

      if (btn.dataset.range === 'page_range') {
        btn.classList.add('border-purple-600', 'bg-purple-100', 'text-purple-800', 'font-semibold');
        btn.classList.remove('border-gray-300', 'text-gray-700');
        if (rangeWrapper) rangeWrapper.style.display = 'block';
        currentPayload.range_type = 'page_range';
        const pageRangeVal = document.getElementById('input-page-range')?.value.trim() || '';
        currentPayload.page_range_text = pageRangeVal;
      } else {
        btn.classList.add('border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-semibold');
        btn.classList.remove('border-gray-300', 'text-gray-700');
        if (rangeWrapper) rangeWrapper.style.display = 'none';
        currentPayload.range_type = btn.dataset.range;
        if (btn.dataset.range === 'preset') {
          currentPayload.preset_start = parseInt(btn.dataset.start);
          currentPayload.preset_count = parseInt(btn.dataset.count);
          document.getElementById('input-total-q').value = currentPayload.preset_count;
          currentPayload.total_questions = currentPayload.preset_count;
        }
      }
      updatePreview();
    });
  });

  // Page range apply button & input
  const btnApplyPageRange = document.getElementById('btn-apply-page-range');
  const inputPageRange = document.getElementById('input-page-range');
  if (btnApplyPageRange && inputPageRange) {
    btnApplyPageRange.addEventListener('click', () => {
      currentPayload.range_type = 'page_range';
      currentPayload.page_range_text = inputPageRange.value.trim();
      updatePreview();
    });
    inputPageRange.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        currentPayload.range_type = 'page_range';
        currentPayload.page_range_text = inputPageRange.value.trim();
        updatePreview();
      }
    });
  }

  // Page buttons
  document.querySelectorAll('.page-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.page-btn').forEach(b => {
        b.classList.remove('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        b.classList.add('border-gray-300');
      });
      btn.classList.add('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
      btn.classList.remove('border-gray-300');

      const pages = parseInt(btn.dataset.pages);
      currentPayload.target_pages = pages;
      document.getElementById('input-target-pages').value = pages;
      updatePreview();
    });
  });

  // Custom pages input
  document.getElementById('input-target-pages').addEventListener('change', (e) => {
    let p = parseInt(e.target.value) || 2;
    if (p < 1) p = 1;
    currentPayload.target_pages = p;
    updatePreview();
  });

  // Total questions input
  document.getElementById('input-total-q').addEventListener('change', (e) => {
    currentPayload.total_questions = parseInt(e.target.value) || 20;
    updatePreview();
  });

  // Allocation select (random vs sequential)
  document.getElementById('select-allocation').addEventListener('change', (e) => {
    currentPayload.shuffle = (e.target.value === 'random');
    document.getElementById('seed-container').style.display = currentPayload.shuffle ? 'flex' : 'none';
    updatePreview();
  });

  // Seed input & re-shuffle button
  document.getElementById('input-seed').addEventListener('change', (e) => {
    currentPayload.seed = parseInt(e.target.value) || 42;
    updatePreview();
  });
  document.getElementById('btn-re-shuffle').addEventListener('click', () => {
    currentPayload.seed = Math.floor(Math.random() * 1000);
    document.getElementById('input-seed').value = currentPayload.seed;
    updatePreview();
  });

  // Auto-fit toggle & manual sliders
  const checkAutoFit = document.getElementById('check-auto-fit');
  const manualControls = document.getElementById('manual-font-controls');
  checkAutoFit.addEventListener('change', (e) => {
    currentPayload.styling.auto_fit = e.target.checked;
    manualControls.classList.toggle('hidden', e.target.checked);
    updatePreview();
  });

  document.getElementById('slider-q-font').addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    document.getElementById('val-q-font').textContent = `${val}pt`;
    currentPayload.styling.q_font_size = val;
    if (!currentPayload.styling.auto_fit) updatePreview();
  });

  document.getElementById('slider-opt-font').addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    document.getElementById('val-opt-font').textContent = `${val}pt`;
    currentPayload.styling.opt_font_size = val;
    if (!currentPayload.styling.auto_fit) updatePreview();
  });

  // Header toggles & inputs
  const checkHeader = document.getElementById('check-enable-header');
  const headerFields = document.getElementById('header-fields');
  checkHeader.addEventListener('change', (e) => {
    currentPayload.header.enabled = e.target.checked;
    headerFields.classList.toggle('opacity-50', !e.target.checked);
    headerFields.classList.toggle('pointer-events-none', !e.target.checked);
    updatePreview();
  });

  ['hdr-inst', 'hdr-title', 'hdr-session', 'hdr-date', 'hdr-time', 'hdr-reg', 'hdr-marks'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        currentPayload.header.inst_name = document.getElementById('hdr-inst').value;
        currentPayload.header.test_title = document.getElementById('hdr-title').value;
        if (document.getElementById('hdr-session')) currentPayload.header.session_text = document.getElementById('hdr-session').value;
        if (document.getElementById('hdr-date')) currentPayload.header.date_text = document.getElementById('hdr-date').value;
        if (document.getElementById('hdr-time')) currentPayload.header.time_text = document.getElementById('hdr-time').value;
        if (document.getElementById('hdr-reg')) currentPayload.header.reg_no_text = document.getElementById('hdr-reg').value;
        if (document.getElementById('hdr-marks')) currentPayload.header.marks_text = document.getElementById('hdr-marks').value;
        updatePreview();
      });
    }
  });

  const checkInstructions = document.getElementById('check-enable-instructions');
  const instructionsContainer = document.getElementById('instructions-container');
  const txtInstructions = document.getElementById('hdr-instructions');
  if (checkInstructions && instructionsContainer) {
    checkInstructions.addEventListener('change', (e) => {
      currentPayload.header.include_instructions = e.target.checked;
      instructionsContainer.classList.toggle('hidden', !e.target.checked);
      if (e.target.checked && txtInstructions && !txtInstructions.value.trim()) {
        txtInstructions.value = (currentPayload.header.instructions || []).join('\n');
      }
      updatePreview();
    });
  }
  if (txtInstructions) {
    txtInstructions.addEventListener('input', (e) => {
      currentPayload.header.instructions = e.target.value.split('\n').map(l => l.trim()).filter(Boolean);
      updatePreview();
    });
  }

  const checkPartB = document.getElementById('check-enable-part-b');
  if (checkPartB) {
    checkPartB.addEventListener('change', (e) => {
      currentPayload.header.part_b_enabled = e.target.checked;
      updatePreview();
    });
  }

  const checkPartC = document.getElementById('check-enable-part-c');
  if (checkPartC) {
    checkPartC.addEventListener('change', (e) => {
      currentPayload.header.part_c_enabled = e.target.checked;
      updatePreview();
    });
  }

  const checkPageBorder = document.getElementById('check-page-border');
  if (checkPageBorder) {
    checkPageBorder.addEventListener('change', (e) => {
      currentPayload.styling.page_border = e.target.checked;
      updatePreview();
    });
  }

  const checkMarksTable = document.getElementById('check-marks-table');
  if (checkMarksTable) {
    checkMarksTable.addEventListener('change', (e) => {
      currentPayload.styling.show_marks_table = e.target.checked;
      updatePreview();
    });
  }

  const checkEndMarker = document.getElementById('check-end-marker');
  if (checkEndMarker) {
    checkEndMarker.addEventListener('change', (e) => {
      currentPayload.styling.end_marker = e.target.checked;
      updatePreview();
    });
  }

  document.getElementById('hdr-placement').addEventListener('change', (e) => {
    currentPayload.header.page1_only = (e.target.value === 'p1_only');
    updatePreview();
  });

  // Footer toggles & inputs
  const checkFooter = document.getElementById('check-enable-footer');
  const footerFields = document.getElementById('footer-fields');
  checkFooter.addEventListener('change', (e) => {
    currentPayload.footer.enabled = e.target.checked;
    footerFields.classList.toggle('opacity-50', !e.target.checked);
    footerFields.classList.toggle('pointer-events-none', !e.target.checked);
    updatePreview();
  });

  document.getElementById('ftr-text').addEventListener('input', (e) => {
    currentPayload.footer.text = e.target.value;
    updatePreview();
  });

  document.getElementById('check-ftr-pagenum').addEventListener('change', (e) => {
    currentPayload.footer.page_number = e.target.checked;
    updatePreview();
  });

  // Divider & Layout
  document.getElementById('select-divider').addEventListener('change', (e) => {
    currentPayload.styling.question_divider = e.target.value;
    updatePreview();
  });

  document.getElementById('select-options-layout').addEventListener('change', (e) => {
    currentPayload.styling.options_layout = e.target.value;
    updatePreview();
  });

  const selectLangMode = document.getElementById('select-language-mode');
  if (selectLangMode) {
    selectLangMode.addEventListener('change', (e) => {
      currentPayload.styling.language_mode = e.target.value;
      updatePreview();
    });
  }

  document.getElementById('input-conditions').addEventListener('input', (e) => {
    currentPayload.styling.conditions_text = e.target.value;
    updatePreview();
  });

  // Page Size Selector
  const selectPageSize = document.getElementById('select-page-size');
  if (selectPageSize) {
    selectPageSize.addEventListener('change', (e) => {
      currentPayload.styling.page_size = e.target.value;
      updateIframeDimensions();
      fitWidth();
      updatePreview();
    });
  }

  // Orientation Buttons
  const btnOrientPortrait = document.getElementById('btn-orient-portrait');
  const btnOrientLandscape = document.getElementById('btn-orient-landscape');
  const landscapeContainer = document.getElementById('landscape-columns-container');

  const setOrientation = (orient) => {
    currentPayload.styling.orientation = orient;
    if (orient === 'portrait') {
      if (btnOrientPortrait) {
        btnOrientPortrait.classList.add('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        btnOrientPortrait.classList.remove('border-gray-300', 'text-gray-700');
      }
      if (btnOrientLandscape) {
        btnOrientLandscape.classList.remove('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        btnOrientLandscape.classList.add('border-gray-300', 'text-gray-700');
      }
      if (landscapeContainer) landscapeContainer.classList.add('hidden');
    } else {
      if (btnOrientLandscape) {
        btnOrientLandscape.classList.add('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        btnOrientLandscape.classList.remove('border-gray-300', 'text-gray-700');
      }
      if (btnOrientPortrait) {
        btnOrientPortrait.classList.remove('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        btnOrientPortrait.classList.add('border-gray-300', 'text-gray-700');
      }
      if (landscapeContainer) landscapeContainer.classList.remove('hidden');
    }
    updateIframeDimensions();
    fitWidth();
    updatePreview();
  };

  if (btnOrientPortrait) {
    btnOrientPortrait.addEventListener('click', () => setOrientation('portrait'));
  }
  if (btnOrientLandscape) {
    btnOrientLandscape.addEventListener('click', () => setOrientation('landscape'));
  }

  // Landscape 2-Column Checkbox
  const checkLandscapeCols = document.getElementById('check-landscape-columns');
  if (checkLandscapeCols) {
    checkLandscapeCols.addEventListener('change', (e) => {
      currentPayload.styling.landscape_columns = e.target.checked;
      updatePreview();
    });
  }

  // Sidebar Toggle
  const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
  if (btnToggleSidebar) {
    btnToggleSidebar.addEventListener('click', () => {
      const sidebar = document.getElementById('sidebar');
      const toggleText = document.getElementById('sidebar-toggle-text');
      if (window.innerWidth < 768) {
        openMobileSidebar();
      } else if (sidebar) {
        sidebar.classList.toggle('hidden');
        const isHidden = sidebar.classList.contains('hidden');
        if (toggleText) toggleText.textContent = isHidden ? 'Show Controls' : 'Controls';
        setTimeout(fitWidth, 120);
      }
    });
  }

  const btnMobileSidebar = document.getElementById('btn-mobile-sidebar-toggle');
  if (btnMobileSidebar) {
    btnMobileSidebar.addEventListener('click', openMobileSidebar);
  }

  const btnCloseSidebarMobile = document.getElementById('btn-close-sidebar-mobile');
  if (btnCloseSidebarMobile) {
    btnCloseSidebarMobile.addEventListener('click', closeMobileSidebar);
  }

  const sidebarBackdrop = document.getElementById('sidebar-backdrop');
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', closeMobileSidebar);
  }

  const btnApplyAndView = document.getElementById('btn-apply-and-view');
  if (btnApplyAndView) {
    btnApplyAndView.addEventListener('click', () => {
      closeMobileSidebar();
      updatePreview();
      setTimeout(fitWidth, 150);
    });
  }

  // Zoom Controls
  const btnZoomFitWidth = document.getElementById('btn-zoom-fit-width');
  const btnZoomFitPage = document.getElementById('btn-zoom-fit-page');
  const btnZoomIn = document.getElementById('btn-zoom-in');
  const btnZoomOut = document.getElementById('btn-zoom-out');

  if (btnZoomFitWidth) btnZoomFitWidth.addEventListener('click', fitWidth);
  if (btnZoomFitPage) btnZoomFitPage.addEventListener('click', fitPage);
  if (btnZoomIn) btnZoomIn.addEventListener('click', () => setZoom(currentZoom + 0.1));
  if (btnZoomOut) btnZoomOut.addEventListener('click', () => setZoom(currentZoom - 0.1));

  // Copy Answer Table
  const btnCopyAnswers = document.getElementById('btn-copy-answers');
  if (btnCopyAnswers) {
    btnCopyAnswers.addEventListener('click', async () => {
      if (!currentAnswerKey || currentAnswerKey.length === 0) return;
      let tsv = "Q#\tOrig #\tPage\tQuestion\tKey\tCorrect Answer\n";
      currentAnswerKey.forEach(q => {
        tsv += `${q.num}\t${q.orig_id}\t${q.page}\t"${(q.q_en || '').replace(/"/g, '""')}"\t${q.ans_opt}\t"${(q.ans_text || '').replace(/"/g, '""')}"\n`;
      });
      await navigator.clipboard.writeText(tsv);
      const orig = btnCopyAnswers.innerHTML;
      btnCopyAnswers.innerHTML = '<i class="fa-solid fa-check mr-1 text-green-600"></i> Copied!';
      setTimeout(() => { btnCopyAnswers.innerHTML = orig; }, 2000);
    });
  }

  // PDF View Toggle
  const btnTogglePdf = document.getElementById('btn-toggle-pdf');
  if (btnTogglePdf) {
    btnTogglePdf.addEventListener('click', togglePdfView);
  }

  // Tabs
  setupTabs();

  // Export buttons
  document.getElementById('btn-export-pdf').addEventListener('click', exportPDF);
  document.getElementById('btn-export-docx').addEventListener('click', exportDOCX);
}

function setupTabs() {
  const tabs = [
    { btn: 'tab-btn-preview', content: 'tab-content-preview' },
    { btn: 'tab-btn-diagrams', content: 'tab-content-diagrams' },
    { btn: 'tab-btn-answers', content: 'tab-content-answers' }
  ];

  tabs.forEach(t => {
    document.getElementById(t.btn).addEventListener('click', () => {
      tabs.forEach(other => {
        const otherBtn = document.getElementById(other.btn);
        const otherContent = document.getElementById(other.content);
        if (other.btn === t.btn) {
          otherBtn.classList.add('bg-white', 'text-indigo-700', 'font-bold', 'shadow-sm', 'border');
          otherBtn.classList.remove('text-gray-600');
          otherContent.classList.remove('hidden');
        } else {
          otherBtn.classList.remove('bg-white', 'text-indigo-700', 'font-bold', 'shadow-sm', 'border');
          otherBtn.classList.add('text-gray-600');
          otherContent.classList.add('hidden');
        }
      });
    });
  });
}

let loadedBanks = [];

async function loadQuestionBanks() {
  try {
    const res = await fetch('/api/banks');
    const data = await res.json();
    loadedBanks = data.banks || [];
    const select = document.getElementById('bank-select');
    select.innerHTML = '';
    loadedBanks.forEach(b => {
      const opt = document.createElement('option');
      opt.value = b.id;
      opt.textContent = `${b.name} (${b.total_questions} Questions)`;
      select.appendChild(opt);
    });

    const manualBankSelect = document.getElementById('manual-bank-select');
    if (manualBankSelect) {
      manualBankSelect.innerHTML = '<option value="new">+ Create New Custom Bank</option>';
      loadedBanks.forEach(b => {
        const mOpt = document.createElement('option');
        mOpt.value = b.id;
        mOpt.textContent = `${b.name} (${b.total_questions} Questions)`;
        manualBankSelect.appendChild(mOpt);
      });
      if (select.value) {
        manualBankSelect.value = select.value;
      }
    }

    const updateModuleDropdown = () => {
      const currentBank = loadedBanks.find(b => b.id === select.value);
      const modContainer = document.getElementById('module-filter-container');
      const modSelect = document.getElementById('module-filter-select');
      if (currentBank && currentBank.modules && currentBank.modules.length > 1) {
        modContainer.classList.remove('hidden');
        modSelect.innerHTML = '<option value="all">All Modules in Bank</option>';
        currentBank.modules.forEach(m => {
          const mOpt = document.createElement('option');
          mOpt.value = m;
          mOpt.textContent = m;
          modSelect.appendChild(mOpt);
        });
      } else {
        modContainer.classList.add('hidden');
        currentPayload.module_filter = 'all';
      }
    };

    select.addEventListener('change', (e) => {
      currentPayload.bank_id = e.target.value;
      updateModuleDropdown();
      currentPayload.module_filter = 'all';
      updatePreview();
    });

    const modSelect = document.getElementById('module-filter-select');
    if (modSelect) {
      modSelect.addEventListener('change', (e) => {
        currentPayload.module_filter = e.target.value;
        updatePreview();
      });
    }

    updateModuleDropdown();
  } catch (err) {
    console.error('Failed to load banks', err);
  }
}

let debounceTimer = null;
function updatePreview() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(async () => {
    try {
      const res = await fetch('/api/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentPayload)
      });
      const data = await res.json();

      if (data.status === 'success') {
        renderIframe(data.html);
        updateStatus(data.stats, data.answer_key);
        renderDiagrams(data.answer_key);
        renderAnswerKey(data.answer_key);
      } else {
        console.error('Preview error:', data.message);
      }
    } catch (err) {
      console.error('Network error during preview:', err);
    }
  }, 150);
}

let currentPageView = 'all'; // 'all', '0', '1', etc.
let isPdfView = false;
let lastHtmlContent = '';

function renderPageNav(numPages) {
  const container = document.getElementById('page-buttons-container');
  if (!container) return;
  container.innerHTML = '';
  
  // All button
  const allBtn = document.createElement('button');
  allBtn.className = `page-view-btn px-2.5 py-0.5 rounded text-xs font-semibold transition-colors ${currentPageView === 'all' ? 'bg-indigo-600 text-white shadow-xs' : 'text-gray-700 hover:bg-gray-200'}`;
  allBtn.textContent = 'All';
  allBtn.dataset.page = 'all';
  allBtn.addEventListener('click', () => setPageView('all'));
  container.appendChild(allBtn);
  
  for (let i = 0; i < numPages; i++) {
    const btn = document.createElement('button');
    btn.className = `page-view-btn px-2.5 py-0.5 rounded text-xs font-semibold transition-colors ${currentPageView === i.toString() ? 'bg-indigo-600 text-white shadow-xs' : 'text-gray-700 hover:bg-gray-200'}`;
    btn.textContent = `P${i + 1}`;
    btn.dataset.page = i.toString();
    btn.addEventListener('click', () => setPageView(i.toString()));
    container.appendChild(btn);
  }
}

function setPageView(pageVal) {
  currentPageView = pageVal;
  document.querySelectorAll('.page-view-btn').forEach(btn => {
    if (btn.dataset.page === pageVal) {
      btn.className = 'page-view-btn px-2.5 py-0.5 rounded text-xs font-semibold bg-indigo-600 text-white shadow-xs';
    } else {
      btn.className = 'page-view-btn px-2.5 py-0.5 rounded text-xs font-semibold text-gray-700 hover:bg-gray-200';
    }
  });
  applyPageView(pageVal);
}

function applyPageView(pageVal) {
  const iframe = document.getElementById('preview-frame');
  if (!iframe || !iframe.contentDocument) return;
  
  const pages = iframe.contentDocument.querySelectorAll('.page');
  if (!pages || pages.length === 0) return;
  
  const size = currentPayload.styling.page_size || 'A4';
  const orient = currentPayload.styling.orientation || 'portrait';
  const dims = PAGE_DIMENSIONS_PX[size] ? PAGE_DIMENSIONS_PX[size][orient] : PAGE_DIMENSIONS_PX['A4'][orient];
  const singlePageH = dims.h;

  if (pageVal === 'all') {
    pages.forEach(p => p.classList.remove('page-hidden'));
    iframe.style.height = `${pages.length * singlePageH + (pages.length - 1) * 24 + 32}px`;
    setZoom(currentZoom);
    if (window.innerWidth < 768) {
      setTimeout(fitWidth, 50);
    }
  } else {
    const targetIdx = parseInt(pageVal);
    pages.forEach((p, idx) => {
      if (idx === targetIdx) {
        p.classList.remove('page-hidden');
      } else {
        p.classList.add('page-hidden');
      }
    });
    iframe.style.height = `${singlePageH + 32}px`;
    setZoom(currentZoom);
    setTimeout(fitPage, 50);
  }
}

async function togglePdfView() {
  isPdfView = !isPdfView;
  const btn = document.getElementById('btn-toggle-pdf');
  const iframe = document.getElementById('preview-frame');
  const pageNav = document.getElementById('page-nav-group');
  if (!btn || !iframe) return;

  if (isPdfView) {
    btn.innerHTML = '<i class="fa-solid fa-code mr-1 text-indigo-600"></i> <span id="pdf-toggle-label">Interactive Sheets</span>';
    btn.classList.remove('text-red-700', 'hover:bg-red-50');
    btn.classList.add('text-indigo-700', 'bg-indigo-50');
    if (pageNav) pageNav.classList.add('opacity-40', 'pointer-events-none');
    
    try {
      const res = await fetch('/api/export/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentPayload)
      });
      if (!res.ok) throw new Error('PDF export failed');
      const blob = await res.blob();
      iframe.src = URL.createObjectURL(blob);
      const size = currentPayload.styling.page_size || 'A4';
      const orient = currentPayload.styling.orientation || 'portrait';
      const dims = PAGE_DIMENSIONS_PX[size] ? PAGE_DIMENSIONS_PX[size][orient] : PAGE_DIMENSIONS_PX['A4'][orient];
      iframe.style.width = `${dims.w}px`;
      iframe.style.height = `${dims.h + 80}px`;
      setTimeout(fitPage, 200);
    } catch (e) {
      console.error('Failed to load PDF preview:', e);
      togglePdfView();
    }
  } else {
    btn.innerHTML = '<i class="fa-solid fa-file-pdf mr-1 text-red-500"></i> <span id="pdf-toggle-label">Exact PDF</span>';
    btn.classList.remove('text-indigo-700', 'bg-indigo-50');
    btn.classList.add('text-red-700', 'hover:bg-red-50');
    if (pageNav) pageNav.classList.remove('opacity-40', 'pointer-events-none');
    
    renderIframe(lastHtmlContent);
  }
}

function openMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (sidebar) sidebar.classList.remove('-translate-x-full');
  if (backdrop) backdrop.classList.remove('hidden');
}

function closeMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (sidebar) sidebar.classList.add('-translate-x-full');
  if (backdrop) backdrop.classList.add('hidden');
}

function updateIframeDimensions() {
  const iframe = document.getElementById('preview-frame');
  if (!iframe) return;
  const size = currentPayload.styling.page_size || 'A4';
  const orient = currentPayload.styling.orientation || 'portrait';
  const dims = PAGE_DIMENSIONS_PX[size] ? PAGE_DIMENSIONS_PX[size][orient] : PAGE_DIMENSIONS_PX['A4'][orient];
  
  iframe.style.width = `${dims.w}px`;
  const singlePageH = dims.h;
  const count = (currentPageView === 'all') ? (parseInt(currentPayload.target_pages) || 2) : 1;
  const totalH = count * singlePageH + (count - 1) * 24 + 32;
  iframe.style.height = `${totalH}px`;
  setZoom(currentZoom);
}

function setZoom(zoom) {
  currentZoom = Math.max(0.18, Math.min(2.5, Math.round(zoom * 100) / 100));
  const scalerBox = document.getElementById('preview-scaler-box') || document.getElementById('preview-wrapper');
  const zoomText = document.getElementById('zoom-level-text');
  const iframe = document.getElementById('preview-frame');
  
  if (scalerBox && iframe) {
    const baseW = parseFloat(iframe.style.width) || 794;
    const baseH = parseFloat(iframe.style.height) || 1123;
    
    const scaledW = Math.round(baseW * currentZoom);
    const scaledH = Math.round(baseH * currentZoom);
    
    scalerBox.style.width = `${scaledW}px`;
    scalerBox.style.height = `${scaledH}px`;
    scalerBox.style.minWidth = `${scaledW}px`;
    scalerBox.style.minHeight = `${scaledH}px`;
    scalerBox.style.overflow = 'hidden';
    
    iframe.style.width = `${baseW}px`;
    iframe.style.height = `${baseH}px`;
    iframe.style.transform = `scale(${currentZoom})`;
    iframe.style.transformOrigin = 'top left';
    iframe.style.position = 'absolute';
    iframe.style.left = '0';
    iframe.style.top = '0';
  }
  if (zoomText) {
    zoomText.textContent = `${Math.round(currentZoom * 100)}%`;
  }
}

function fitWidth() {
  const viewport = document.getElementById('tab-content-preview');
  const iframe = document.getElementById('preview-frame');
  if (!viewport || !iframe) return;
  const pad = window.innerWidth < 640 ? 16 : 40;
  const availableWidth = viewport.clientWidth - pad;
  const iframeW = parseFloat(iframe.style.width) || 794;
  if (availableWidth > 50 && iframeW > 0) {
    const targetZoom = Math.min(1.25, Math.max(0.18, availableWidth / iframeW));
    setZoom(targetZoom);
  }
}

function fitPage() {
  const viewport = document.getElementById('tab-content-preview');
  const iframe = document.getElementById('preview-frame');
  if (!viewport || !iframe) return;
  const size = currentPayload.styling.page_size || 'A4';
  const orient = currentPayload.styling.orientation || 'portrait';
  const dims = PAGE_DIMENSIONS_PX[size] ? PAGE_DIMENSIONS_PX[size][orient] : PAGE_DIMENSIONS_PX['A4'][orient];
  
  const pad = window.innerWidth < 640 ? 16 : 40;
  const availableWidth = viewport.clientWidth - pad;
  const availableHeight = viewport.clientHeight - pad;
  
  const scaleW = availableWidth / dims.w;
  const scaleH = availableHeight / dims.h;
  const targetZoom = Math.min(scaleW, scaleH, 1.25);
  setZoom(Math.max(0.18, targetZoom));
}

function renderIframe(htmlContent) {
  const iframe = document.getElementById('preview-frame');
  if (!iframe) return;
  lastHtmlContent = htmlContent;

  if (isPdfView) {
    fetch('/api/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentPayload)
    }).then(r => r.blob()).then(blob => {
      iframe.src = URL.createObjectURL(blob);
    }).catch(e => console.error(e));
    return;
  }

  iframe.onload = () => {
    try {
      const doc = iframe.contentDocument;
      if (doc) {
        const pages = doc.querySelectorAll('.page');
        if (pages.length > 0) {
          renderPageNav(pages.length);
          applyPageView(currentPageView);
        }
      }
    } catch (e) {
      console.warn('iframe load inspect:', e);
    }
  };

  const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
  iframe.src = URL.createObjectURL(blob);
  updateIframeDimensions();
}

function updateStatus(stats, answerKey) {
  const size = currentPayload.styling.page_size || 'A4';
  const orient = currentPayload.styling.orientation === 'landscape' ? 'Landscape' : 'Portrait';
  const totalDiagrams = (stats.diagrams_per_page || []).reduce((a, b) => a + b, 0);

  const statusPill = document.getElementById('status-pill');
  if (statusPill) {
    statusPill.textContent = `${stats.total_questions} Questions • ${stats.target_pages} Pages • ${size} ${orient} • ${totalDiagrams} Diagrams`;
  }
  
  const qCountEl = document.getElementById('status-q-count');
  if (qCountEl) qCountEl.innerHTML = `<strong class="text-gray-800">${stats.total_questions}</strong> Questions`;
  const pCountEl = document.getElementById('status-pages-count');
  if (pCountEl) pCountEl.innerHTML = `<strong class="text-gray-800">${stats.target_pages}</strong> Pages`;
  const imgCountEl = document.getElementById('status-img-count');
  if (imgCountEl) imgCountEl.innerHTML = `<strong class="text-gray-800">${totalDiagrams}</strong> Diagrams Verified`;

  const diagBadge = document.getElementById('diagram-count-badge');
  if (diagBadge) diagBadge.textContent = totalDiagrams;
}

function renderDiagrams(answerKey) {
  const grid = document.getElementById('diagrams-grid');
  grid.innerHTML = '';
  
  const diagQuestions = answerKey.filter(q => q.has_img);
  if (diagQuestions.length === 0) {
    grid.innerHTML = '<p class="col-span-full text-center text-gray-500 py-8">No diagrams in this question set.</p>';
    return;
  }

  diagQuestions.forEach(q => {
    const card = document.createElement('div');
    card.className = 'bg-gray-50 border border-gray-200 rounded-lg p-3 flex flex-col items-center justify-between text-center';
    
    // Find image in bank questions or match by q num
    card.innerHTML = `
      <div class="w-full flex justify-between items-center text-xs mb-2">
        <span class="font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">Q# ${q.num}</span>
        <span class="text-gray-500">Orig Q${q.orig_id}</span>
      </div>
      <div class="h-28 w-full flex items-center justify-center bg-white border border-gray-200 rounded p-1 mb-2">
        <img src="/extracted_imgs/${q.img_file || ('q' + q.orig_id + '_clean.png')}" onerror="this.onerror=null; this.parentElement.innerHTML='<span class=\'text-xs text-gray-400\'>Diagram not available</span>';" class="max-h-full max-w-full object-contain" alt="Diagram">
      </div>
      <div class="text-xs text-gray-600 truncate w-full" title="${q.q_en}">${q.q_en}</div>
    `;
    grid.appendChild(card);
  });
}

function renderAnswerKey(answerKey) {
  currentAnswerKey = answerKey;
  const tbody = document.getElementById('answers-table-body');
  tbody.innerHTML = '';
  
  answerKey.forEach(q => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-gray-50';
    tr.innerHTML = `
      <td class="px-3 py-2 font-bold text-gray-900">${q.num}</td>
      <td class="px-3 py-2 text-gray-500">Q${q.orig_id}</td>
      <td class="px-3 py-2 text-gray-500">Page ${q.page}</td>
      <td class="px-3 py-2 text-gray-800">${q.q_en.substring(0, 50)}${q.q_en.length > 50 ? '...' : ''} ${q.has_img ? '<span class="text-xs bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded font-semibold ml-1">IMG</span>' : ''}</td>
      <td class="px-3 py-2 text-center font-bold text-indigo-700">(${q.ans_opt})</td>
      <td class="px-3 py-2 text-gray-700">${q.ans_text}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function exportPDF() {
  const btn = document.getElementById('btn-export-pdf');
  const originalText = btn.innerHTML;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Generating PDF...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentPayload)
    });
    
    if (res.ok) {
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = await res.json();
        if (data.status === 'fallback_print' && data.html) {
          const printWin = window.open('', '_blank');
          if (printWin) {
            printWin.document.write(data.html);
            printWin.document.close();
            printWin.focus();
            setTimeout(() => { printWin.print(); }, 400);
            return;
          }
        }
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Fitter_Question_Paper_${currentPayload.styling.page_size}_${currentPayload.styling.orientation}_${currentPayload.total_questions}Q_${currentPayload.target_pages}Pages.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } else {
      alert('Failed to generate PDF. Check console.');
    }
  } catch (err) {
    console.error('PDF Export error:', err);
    alert('Export error: ' + err.message);
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function setupUploadModal() {
  const modal = document.getElementById('upload-modal');
  const btnOpen = document.getElementById('btn-open-upload');
  const btnClose = document.getElementById('btn-close-upload');
  const btnCancel = document.getElementById('btn-cancel-upload');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('pdf-file-input');
  const fileLabel = document.getElementById('file-chosen-label');
  const form = document.getElementById('upload-form');
  const progressContainer = document.getElementById('upload-progress-container');
  const btnSubmit = document.getElementById('btn-submit-upload');

  btnOpen.addEventListener('click', () => {
    modal.classList.remove('hidden');
    progressContainer.classList.add('hidden');
    btnSubmit.disabled = false;
    form.reset();
    fileLabel.textContent = 'Click to browse or drag & drop PDF here';
  });

  [btnClose, btnCancel].forEach(b => {
    b.addEventListener('click', () => modal.classList.add('hidden'));
  });

  dropzone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      fileLabel.innerHTML = `<span class="text-indigo-600 font-bold">${fileInput.files[0].name}</span> (${(fileInput.files[0].size / 1024 / 1024).toFixed(2)} MB)`;
    }
  });

  // Drag and drop
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('border-indigo-600', 'bg-indigo-50');
  });
  ['dragleave', 'dragend'].forEach(evt => {
    dropzone.addEventListener(evt, () => {
      dropzone.classList.remove('border-indigo-600', 'bg-indigo-50');
    });
  });
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('border-indigo-600', 'bg-indigo-50');
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      fileLabel.innerHTML = `<span class="text-indigo-600 font-bold">${fileInput.files[0].name}</span> (${(fileInput.files[0].size / 1024 / 1024).toFixed(2)} MB)`;
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileInput.files || fileInput.files.length === 0) {
      alert('Please select a PDF file first.');
      return;
    }

    const formData = new FormData();
    formData.append('pdf_file', fileInput.files[0]);
    formData.append('trade_name', document.getElementById('trade-name-input').value || 'Custom Trade');

    progressContainer.classList.remove('hidden');
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Analyzing...';

    const statusTexts = [
      'Scanning PDF pages & table structures...',
      'Extracting questions, options & answer keys...',
      'Analyzing & cropping diagrams with computer vision...',
      'Finalizing new question bank...'
    ];
    let step = 0;
    const interval = setInterval(() => {
      step = (step + 1) % statusTexts.length;
      document.getElementById('upload-status-text').textContent = statusTexts[step];
    }, 1500);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      clearInterval(interval);
      const data = await res.json();

      if (data.status === 'success') {
        modal.classList.add('hidden');
        alert(`Successfully imported: ${data.bank.name}\n\n• Total Questions: ${data.bank.total_questions}\n• Diagrams Detected: ${data.bank.diagrams_count}\n\nLoading new question bank now!`);
        
        // Reload banks and select the new one
        await loadQuestionBanks();
        const select = document.getElementById('bank-select');
        select.value = data.bank.id;
        currentPayload.bank_id = data.bank.id;
        currentPayload.total_questions = Math.min(20, data.bank.total_questions);
        document.getElementById('input-total-q').value = currentPayload.total_questions;
        updatePreview();
      } else {
        alert('Upload failed: ' + (data.message || 'Unknown error'));
      }
    } catch (err) {
      clearInterval(interval);
      console.error('Upload error:', err);
      alert('Network or processing error during PDF analysis: ' + err.message);
    } finally {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles mr-1.5"></i> Analyze & Import';
      progressContainer.classList.add('hidden');
    }
  });
}

async function exportDOCX() {
  const btn = document.getElementById('btn-export-docx');
  const originalText = btn.innerHTML;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Generating DOCX...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/export/docx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentPayload)
    });
    
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Fitter_Question_Paper_${currentPayload.styling.page_size}_${currentPayload.styling.orientation}_${currentPayload.total_questions}Q_${currentPayload.target_pages}Pages.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } else {
      alert('Failed to generate DOCX. Check console.');
    }
  } catch (err) {
    console.error('DOCX Export error:', err);
    alert('Export error: ' + err.message);
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function setupManualQuestionModal() {
  const modal = document.getElementById('manual-modal');
  const btnOpen = document.getElementById('btn-open-manual-create');
  const btnQuick = document.getElementById('btn-quick-manual');
  const btnClose = document.getElementById('btn-close-manual');
  const btnCancel = document.getElementById('btn-cancel-manual');
  const bankSelect = document.getElementById('manual-bank-select');
  const newBankFields = document.getElementById('manual-new-bank-fields');
  const hasOptionsCheck = document.getElementById('manual-has-options');
  const optionsContainer = document.getElementById('manual-options-container');
  const imgFileInput = document.getElementById('manual-img-file');
  const imgPreviewBox = document.getElementById('manual-img-preview-box');
  const imgPreview = document.getElementById('manual-img-preview');
  const btnRemoveImg = document.getElementById('btn-remove-manual-img');
  const manualForm = document.getElementById('manual-form');
  const btnSave = document.getElementById('btn-save-manual');

  const toggleNewBankFields = () => {
    if (bankSelect && bankSelect.value === 'new') {
      newBankFields.classList.remove('hidden');
      document.getElementById('manual-new-bank-name').focus();
    } else if (newBankFields) {
      newBankFields.classList.add('hidden');
    }
  };

  const openModal = () => {
    const mainSelect = document.getElementById('bank-select');
    if (mainSelect && mainSelect.value && bankSelect) {
      bankSelect.value = mainSelect.value;
    }
    toggleNewBankFields();
    if (modal) modal.classList.remove('hidden');
  };

  const closeModal = () => {
    if (modal) modal.classList.add('hidden');
  };

  if (btnOpen) btnOpen.addEventListener('click', openModal);
  if (btnQuick) btnQuick.addEventListener('click', openModal);
  if (btnClose) btnClose.addEventListener('click', closeModal);
  if (btnCancel) btnCancel.addEventListener('click', closeModal);
  if (bankSelect) bankSelect.addEventListener('change', toggleNewBankFields);

  if (hasOptionsCheck && optionsContainer) {
    hasOptionsCheck.addEventListener('change', () => {
      optionsContainer.classList.toggle('hidden', !hasOptionsCheck.checked);
    });
  }

  if (imgFileInput && imgPreviewBox && imgPreview) {
    imgFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          imgPreview.src = event.target.result;
          imgPreviewBox.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
      } else {
        imgPreviewBox.classList.add('hidden');
      }
    });
  }

  if (btnRemoveImg && imgFileInput && imgPreviewBox && imgPreview) {
    btnRemoveImg.addEventListener('click', () => {
      imgFileInput.value = '';
      imgPreviewBox.classList.add('hidden');
      imgPreview.src = '';
    });
  }

  if (manualForm) {
    manualForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const qEn = document.getElementById('manual-q-en').value.trim();
      if (!qEn) {
        alert('Please enter English question text.');
        return;
      }

      btnSave.disabled = true;
      const originalSaveHtml = btnSave.innerHTML;
      btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Saving...';

      try {
        const formData = new FormData();
        formData.append('target_bank_id', bankSelect.value);
        formData.append('new_bank_name', document.getElementById('manual-new-bank-name').value.trim());
        formData.append('module', document.getElementById('manual-module').value.trim() || 'General');
        formData.append('subheading', document.getElementById('manual-subheading').value.trim());
        formData.append('q_en', qEn);
        formData.append('q_ta', document.getElementById('manual-q-ta').value.trim());
        formData.append('has_options', hasOptionsCheck.checked ? 'true' : 'false');
        
        formData.append('opt_a_en', document.getElementById('manual-opt-a-en').value.trim());
        formData.append('opt_a_ta', document.getElementById('manual-opt-a-ta').value.trim());
        formData.append('opt_b_en', document.getElementById('manual-opt-b-en').value.trim());
        formData.append('opt_b_ta', document.getElementById('manual-opt-b-ta').value.trim());
        formData.append('opt_c_en', document.getElementById('manual-opt-c-en').value.trim());
        formData.append('opt_c_ta', document.getElementById('manual-opt-c-ta').value.trim());
        formData.append('opt_d_en', document.getElementById('manual-opt-d-en').value.trim());
        formData.append('opt_d_ta', document.getElementById('manual-opt-d-ta').value.trim());

        const correctRadio = document.querySelector('input[name="manual_correct_ans"]:checked');
        formData.append('correct_ans', correctRadio ? correctRadio.value : 'A');

        if (imgFileInput.files[0]) {
          formData.append('diagram_file', imgFileInput.files[0]);
        }

        const res = await fetch('/api/questions/manual', {
          method: 'POST',
          body: formData
        });

        const data = await res.json();
        if (data.status === 'success') {
          alert(`Question successfully saved!\n\nAdded to bank: "${data.bank_name}"\nTotal questions in bank: ${data.total_questions}`);
          closeModal();
          manualForm.reset();
          hasOptionsCheck.checked = true;
          optionsContainer.classList.remove('hidden');
          imgPreviewBox.classList.add('hidden');
          imgPreview.src = '';
          
          await loadQuestionBanks();
          const mainSelect = document.getElementById('bank-select');
          if (mainSelect) {
            mainSelect.value = data.bank_id;
            currentPayload.bank_id = data.bank_id;
          }
          updatePreview();
        } else {
          alert('Failed to save question: ' + (data.message || 'Unknown error'));
        }
      } catch (err) {
        console.error('Manual question save error:', err);
        alert('Error saving manual question: ' + err.message);
      } finally {
        btnSave.disabled = false;
        btnSave.innerHTML = originalSaveHtml;
      }
    });
  }
}

function setupGoogleFormModal() {
  const modal = document.getElementById('google-form-modal');
  const btnOpen = document.getElementById('btn-open-google-form');
  const btnClose = document.getElementById('btn-close-google-form');
  
  const tabAuto = document.getElementById('tab-btn-gf-auto');
  const tabManual = document.getElementById('tab-btn-gf-manual');
  const contentAuto = document.getElementById('tab-content-gf-auto');
  const contentManual = document.getElementById('tab-content-gf-manual');
  
  const scriptArea = document.getElementById('gf-script-code');
  const manualArea = document.getElementById('gf-manual-text');
  const statsLabel = document.getElementById('gf-script-stats');
  
  const btnCopyScript = document.getElementById('btn-copy-gf-script');
  const btnDownloadScript = document.getElementById('btn-download-gf-script');
  const btnCopyManual = document.getElementById('btn-copy-gf-text');

  const openModal = async () => {
    if (modal) modal.classList.remove('hidden');
    if (scriptArea) scriptArea.value = '// Generating Google Apps Script... please wait.';
    if (manualArea) manualArea.value = 'Formatting question paper for Google Form...';
    
    try {
      const res = await fetch('/api/export/google-form', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentPayload)
      });
      const data = await res.json();
      if (data.status === 'success') {
        if (scriptArea) scriptArea.value = data.script;
        if (manualArea) manualArea.value = data.manual_text;
        if (statsLabel) {
          statsLabel.textContent = `${data.total_questions} questions ready for Google Form Quiz`;
        }
      } else {
        if (scriptArea) scriptArea.value = '// Failed to generate script: ' + (data.message || 'Unknown error');
        if (manualArea) manualArea.value = 'Failed to generate formatted text: ' + (data.message || 'Unknown error');
      }
    } catch (err) {
      console.error('Google Form export error:', err);
      if (scriptArea) scriptArea.value = '// Network or generation error: ' + err.message;
      if (manualArea) manualArea.value = 'Error: ' + err.message;
    }
  };

  const closeModal = () => {
    if (modal) modal.classList.add('hidden');
  };

  if (btnOpen) btnOpen.addEventListener('click', openModal);
  if (btnClose) btnClose.addEventListener('click', closeModal);

  if (tabAuto && tabManual && contentAuto && contentManual) {
    tabAuto.addEventListener('click', () => {
      tabAuto.className = 'py-2 px-4 border-b-2 border-purple-600 font-bold text-xs text-purple-700 flex items-center';
      tabManual.className = 'py-2 px-4 border-b-2 border-transparent font-medium text-xs text-gray-500 hover:text-gray-700 flex items-center';
      contentAuto.classList.remove('hidden');
      contentManual.classList.add('hidden');
    });

    tabManual.addEventListener('click', () => {
      tabManual.className = 'py-2 px-4 border-b-2 border-indigo-600 font-bold text-xs text-indigo-700 flex items-center';
      tabAuto.className = 'py-2 px-4 border-b-2 border-transparent font-medium text-xs text-gray-500 hover:text-gray-700 flex items-center';
      contentManual.classList.remove('hidden');
      contentAuto.classList.add('hidden');
    });
  }

  // Copy Script
  if (btnCopyScript && scriptArea) {
    btnCopyScript.addEventListener('click', async () => {
      if (!scriptArea.value) return;
      await navigator.clipboard.writeText(scriptArea.value);
      const original = btnCopyScript.innerHTML;
      btnCopyScript.innerHTML = '<i class="fa-solid fa-check mr-1"></i> Copied!';
      btnCopyScript.classList.add('bg-emerald-600');
      setTimeout(() => {
        btnCopyScript.innerHTML = original;
        btnCopyScript.classList.remove('bg-emerald-600');
      }, 2000);
    });
  }

  // Download .gs Script
  if (btnDownloadScript && scriptArea) {
    btnDownloadScript.addEventListener('click', () => {
      if (!scriptArea.value) return;
      const blob = new Blob([scriptArea.value], { type: 'text/javascript' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Create_Google_Form_${currentPayload.total_questions}Q.gs`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  }

  // Copy Manual Text
  if (btnCopyManual && manualArea) {
    btnCopyManual.addEventListener('click', async () => {
      if (!manualArea.value) return;
      await navigator.clipboard.writeText(manualArea.value);
      const original = btnCopyManual.innerHTML;
      btnCopyManual.innerHTML = '<i class="fa-solid fa-check mr-1"></i> Copied!';
      btnCopyManual.classList.add('bg-emerald-600');
      setTimeout(() => {
        btnCopyManual.innerHTML = original;
        btnCopyManual.classList.remove('bg-emerald-600');
      }, 2000);
    });
  }
}

let detectedTemplate = null;

function setupFormatModal() {
  const modal = document.getElementById('format-modal');
  const btnOpenModal = document.getElementById('btn-open-format-modal');
  const btnQuickFormat = document.getElementById('btn-quick-format');
  const btnCloseModal = document.getElementById('btn-close-format-modal');
  
  const dropzone = document.getElementById('format-dropzone');
  const fileInput = document.getElementById('format-file-input');
  const btnBrowse = document.getElementById('btn-browse-format');
  const progress = document.getElementById('format-analyze-progress');
  const extractedBox = document.getElementById('format-extracted-box');
  const btnApplyExtracted = document.getElementById('btn-apply-extracted-format');
  const presetsContainer = document.getElementById('format-presets-list');
  const selectPreset = document.getElementById('select-template-preset');

  const openModal = () => {
    if (modal) modal.classList.remove('hidden');
    loadFormatPresets();
  };
  const closeModal = () => {
    if (modal) modal.classList.add('hidden');
  };

  if (btnOpenModal) btnOpenModal.addEventListener('click', openModal);
  if (btnQuickFormat) btnQuickFormat.addEventListener('click', openModal);
  if (btnCloseModal) btnCloseModal.addEventListener('click', closeModal);

  // Browse button
  if (btnBrowse && fileInput) {
    btnBrowse.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }
  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('border-amber-500', 'bg-amber-100/50');
    });
    ['dragleave', 'dragend'].forEach(evt => {
      dropzone.addEventListener(evt, () => {
        dropzone.classList.remove('border-amber-500', 'bg-amber-100/50');
      });
    });
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('border-amber-500', 'bg-amber-100/50');
      if (e.dataTransfer.files.length > 0) {
        handleFormatUpload(e.dataTransfer.files[0]);
      }
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        handleFormatUpload(fileInput.files[0]);
      }
    });
  }

  const handleFormatUpload = async (file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append('template_file', file);

    if (progress) progress.classList.remove('hidden');
    if (extractedBox) extractedBox.classList.add('hidden');

    try {
      const res = await fetch('/api/template/analyze', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.status === 'success' && data.template) {
        detectedTemplate = data.template;
        const detFile = document.getElementById('format-detected-file');
        if (detFile) detFile.textContent = data.filename || file.name;
        
        const extPage = document.getElementById('ext-page-size');
        if (extPage) extPage.textContent = data.template.page_size || 'A4';
        const extOrient = document.getElementById('ext-orientation');
        if (extOrient) extOrient.textContent = (data.template.orientation || 'portrait').toUpperCase();
        const extInst = document.getElementById('ext-inst-name');
        if (extInst) extInst.textContent = data.template.inst_name || '(None)';
        const extTitle = document.getElementById('ext-test-title');
        if (extTitle) extTitle.textContent = data.template.test_title || '(None)';
        const extDate = document.getElementById('ext-date-text');
        if (extDate) extDate.textContent = data.template.date_text || '(None)';
        const extMarks = document.getElementById('ext-marks-text');
        if (extMarks) extMarks.textContent = data.template.marks_text || '(None)';

        if (extractedBox) extractedBox.classList.remove('hidden');
      } else {
        alert('Format detection error: ' + (data.message || 'Could not parse template.'));
      }
    } catch (err) {
      console.error('Format template analysis error:', err);
      alert('Error analyzing format file: ' + err.message);
    } finally {
      if (progress) progress.classList.add('hidden');
    }
  };

  if (btnApplyExtracted) {
    btnApplyExtracted.addEventListener('click', () => {
      if (detectedTemplate) {
        applyTemplateSettings(detectedTemplate);
        closeModal();
      }
    });
  }

  // Load Presets
  let loadedPresets = [];
  const loadFormatPresets = async () => {
    try {
      const res = await fetch('/api/template/presets');
      const data = await res.json();
      loadedPresets = data.presets || [];
      
      if (presetsContainer) {
        presetsContainer.innerHTML = '';
        loadedPresets.forEach(preset => {
          const card = document.createElement('div');
          card.className = 'border border-gray-200 rounded-lg p-2.5 hover:border-amber-500 hover:bg-amber-50/40 cursor-pointer transition flex flex-col justify-between text-xs';
          card.innerHTML = `
            <div>
              <div class="font-bold text-gray-900 mb-0.5 flex items-center justify-between">
                <span>${preset.name}</span>
                <span class="text-[10px] bg-amber-100 text-amber-800 font-bold px-1.5 py-0.5 rounded">${preset.page_size} • ${preset.orientation}</span>
              </div>
              <p class="text-[11px] text-gray-500 leading-tight mb-2">${preset.desc}</p>
            </div>
            <button type="button" class="mt-1 w-full text-center py-1 bg-white border border-gray-300 hover:bg-amber-600 hover:text-white rounded text-[11px] font-semibold text-gray-700 transition">
              Use This Preset
            </button>
          `;
          card.addEventListener('click', () => {
            applyTemplateSettings(preset);
            if (selectPreset) selectPreset.value = preset.id;
            closeModal();
          });
          presetsContainer.appendChild(card);
        });
      }

      if (selectPreset && selectPreset.options.length <= 1) {
        selectPreset.innerHTML = '';
        loadedPresets.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = `${p.name} (${p.page_size} ${p.orientation})`;
          selectPreset.appendChild(opt);
        });
      }
    } catch (err) {
      console.error('Failed to load presets:', err);
    }
  };

  // Quick preset selector in Section 3
  if (selectPreset) {
    selectPreset.addEventListener('change', async () => {
      if (loadedPresets.length === 0) {
        const res = await fetch('/api/template/presets');
        const data = await res.json();
        loadedPresets = data.presets || [];
      }
      const found = loadedPresets.find(p => p.id === selectPreset.value);
      if (found) {
        applyTemplateSettings(found);
      }
    });
  }

  // Pre-load presets once
  loadFormatPresets();
}

function applyTemplateSettings(tmpl) {
  if (!tmpl) return;

  // Page size & orientation
  if (tmpl.page_size) {
    currentPayload.styling.page_size = tmpl.page_size;
    const selPage = document.getElementById('select-page-size');
    if (selPage) selPage.value = tmpl.page_size;
  }
  if (tmpl.orientation) {
    currentPayload.styling.orientation = tmpl.orientation;
    const btnP = document.getElementById('btn-orient-portrait');
    const btnL = document.getElementById('btn-orient-landscape');
    const lContainer = document.getElementById('landscape-columns-container');
    if (tmpl.orientation === 'portrait') {
      if (btnP) {
        btnP.classList.add('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        btnP.classList.remove('border-gray-300', 'text-gray-700');
      }
      if (btnL) {
        btnL.classList.remove('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        btnL.classList.add('border-gray-300', 'text-gray-700');
      }
      if (lContainer) lContainer.classList.add('hidden');
    } else {
      if (btnL) {
        btnL.classList.add('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        btnL.classList.remove('border-gray-300', 'text-gray-700');
      }
      if (btnP) {
        btnP.classList.remove('border-2', 'border-indigo-600', 'bg-indigo-50', 'text-indigo-700', 'font-bold');
        btnP.classList.add('border-gray-300', 'text-gray-700');
      }
      if (lContainer) lContainer.classList.remove('hidden');
    }
  }

  // Header settings
  if (tmpl.inst_name !== undefined) {
    currentPayload.header.inst_name = tmpl.inst_name;
    const hdrInst = document.getElementById('hdr-inst');
    if (hdrInst) hdrInst.value = tmpl.inst_name;
  }
  if (tmpl.test_title !== undefined) {
    currentPayload.header.test_title = tmpl.test_title;
    const hdrTitle = document.getElementById('hdr-title');
    if (hdrTitle) hdrTitle.value = tmpl.test_title;
  }
  if (tmpl.session_text !== undefined) {
    currentPayload.header.session_text = tmpl.session_text;
    const hdrSession = document.getElementById('hdr-session');
    if (hdrSession) hdrSession.value = tmpl.session_text;
  }
  if (tmpl.date_text !== undefined) {
    currentPayload.header.date_text = tmpl.date_text;
    const hdrDate = document.getElementById('hdr-date');
    if (hdrDate) hdrDate.value = tmpl.date_text;
  }
  if (tmpl.time_text !== undefined) {
    currentPayload.header.time_text = tmpl.time_text;
    const hdrTime = document.getElementById('hdr-time');
    if (hdrTime) hdrTime.value = tmpl.time_text;
  }
  if (tmpl.reg_no_text !== undefined) {
    currentPayload.header.reg_no_text = tmpl.reg_no_text;
    const hdrReg = document.getElementById('hdr-reg');
    if (hdrReg) hdrReg.value = tmpl.reg_no_text;
  }
  if (tmpl.marks_text !== undefined) {
    currentPayload.header.marks_text = tmpl.marks_text;
    const hdrMarks = document.getElementById('hdr-marks');
    if (hdrMarks) hdrMarks.value = tmpl.marks_text;
  }

  // Instructions
  if (tmpl.include_instructions !== undefined) {
    currentPayload.header.include_instructions = tmpl.include_instructions;
    const chkIns = document.getElementById('check-enable-instructions');
    const insCont = document.getElementById('instructions-container');
    const txtIns = document.getElementById('hdr-instructions');
    if (chkIns) chkIns.checked = tmpl.include_instructions;
    if (insCont) insCont.classList.toggle('hidden', !tmpl.include_instructions);
    if (tmpl.instructions && txtIns) {
      currentPayload.header.instructions = tmpl.instructions;
      txtIns.value = tmpl.instructions.join('\n');
    }
  }

  // Parts B & C
  if (tmpl.part_b_enabled !== undefined) {
    currentPayload.header.part_b_enabled = tmpl.part_b_enabled;
    const chkPartB = document.getElementById('check-enable-part-b');
    if (chkPartB) chkPartB.checked = tmpl.part_b_enabled;
    if (tmpl.part_b_title) currentPayload.header.part_b_title = tmpl.part_b_title;
    if (tmpl.part_b_subtitle) currentPayload.header.part_b_subtitle = tmpl.part_b_subtitle;
    if (tmpl.part_b_questions && tmpl.part_b_questions.length) currentPayload.header.part_b_questions = tmpl.part_b_questions;
  }
  if (tmpl.part_c_enabled !== undefined) {
    currentPayload.header.part_c_enabled = tmpl.part_c_enabled;
    const chkPartC = document.getElementById('check-enable-part-c');
    if (chkPartC) chkPartC.checked = tmpl.part_c_enabled;
    if (tmpl.part_c_title) currentPayload.header.part_c_title = tmpl.part_c_title;
    if (tmpl.part_c_subtitle) currentPayload.header.part_c_subtitle = tmpl.part_c_subtitle;
    if (tmpl.part_c_questions && tmpl.part_c_questions.length) currentPayload.header.part_c_questions = tmpl.part_c_questions;
  }

  // Page Border
  if (tmpl.page_border !== undefined) {
    currentPayload.styling.page_border = tmpl.page_border;
    const chkBorder = document.getElementById('check-page-border');
    if (chkBorder) chkBorder.checked = tmpl.page_border;
  }

  // Marks Distribution Table
  if (tmpl.show_marks_table !== undefined) {
    currentPayload.styling.show_marks_table = tmpl.show_marks_table;
    const chkMarksTbl = document.getElementById('check-marks-table');
    if (chkMarksTbl) chkMarksTbl.checked = tmpl.show_marks_table;
  }

  // End of paper marker
  if (tmpl.end_marker !== undefined) {
    currentPayload.styling.end_marker = tmpl.end_marker;
    const chkEnd = document.getElementById('check-end-marker');
    if (chkEnd) chkEnd.checked = tmpl.end_marker;
  }
  if (tmpl.end_marker_text !== undefined) {
    currentPayload.styling.end_marker_text = tmpl.end_marker_text;
  }

  // Footer settings
  if (tmpl.footer_enabled !== undefined) {
    currentPayload.footer.enabled = tmpl.footer_enabled;
    const chkFtr = document.getElementById('check-enable-footer');
    const ftrFields = document.getElementById('footer-fields');
    if (chkFtr) chkFtr.checked = tmpl.footer_enabled;
    if (ftrFields) {
      ftrFields.classList.toggle('opacity-50', !tmpl.footer_enabled);
      ftrFields.classList.toggle('pointer-events-none', !tmpl.footer_enabled);
    }
  }
  if (tmpl.footer_text !== undefined) {
    currentPayload.footer.text = tmpl.footer_text;
    const ftrText = document.getElementById('ftr-text');
    if (ftrText) ftrText.value = tmpl.footer_text;
  }

  // Styling
  if (tmpl.question_divider) {
    currentPayload.styling.question_divider = tmpl.question_divider;
    const selDiv = document.getElementById('select-divider');
    if (selDiv) selDiv.value = tmpl.question_divider;
  }
  if (tmpl.options_layout) {
    currentPayload.styling.options_layout = tmpl.options_layout;
    const selOpt = document.getElementById('select-options-layout');
    if (selOpt) selOpt.value = tmpl.options_layout;
  }
  if (tmpl.language_mode) {
    currentPayload.styling.language_mode = tmpl.language_mode;
    const selLang = document.getElementById('select-language-mode');
    if (selLang) selLang.value = tmpl.language_mode;
  }

  updateIframeDimensions();
  fitWidth();
  updatePreview();
}

function setupSubjectBookModal() {
  const modal = document.getElementById('book-modal');
  const btnOpen = document.getElementById('btn-open-book-modal');
  const btnClose = document.getElementById('btn-close-book');
  const btnCancel = document.getElementById('btn-cancel-book');
  const dropzone = document.getElementById('book-dropzone');
  const fileInput = document.getElementById('book-file-input');
  const fileLabel = document.getElementById('book-file-label');
  const form = document.getElementById('book-form');
  const progressContainer = document.getElementById('book-progress-container');
  const btnSubmit = document.getElementById('btn-submit-book');

  if (!btnOpen || !modal) return;

  btnOpen.addEventListener('click', () => {
    modal.classList.remove('hidden');
    progressContainer.classList.add('hidden');
    btnSubmit.disabled = false;
    form.reset();
    fileLabel.textContent = 'Click to browse or drop Subject Book PDF';
  });

  [btnClose, btnCancel].forEach(b => {
    b.addEventListener('click', () => modal.classList.add('hidden'));
  });

  dropzone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      fileLabel.innerHTML = `<span class="text-amber-700 font-bold">${fileInput.files[0].name}</span> (${(fileInput.files[0].size / 1024 / 1024).toFixed(2)} MB)`;
      const titleInput = document.getElementById('book-subject-title');
      if (!titleInput.value) {
        let cleanName = fileInput.files[0].name.replace(/\.pdf$/i, '').replace(/[-_]+/g, ' ').trim();
        titleInput.value = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);
      }
    }
  });

  // Drag and drop
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('border-amber-600', 'bg-amber-100/50');
  });
  ['dragleave', 'dragend'].forEach(evt => {
    dropzone.addEventListener(evt, () => {
      dropzone.classList.remove('border-amber-600', 'bg-amber-100/50');
    });
  });
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('border-amber-600', 'bg-amber-100/50');
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      fileLabel.innerHTML = `<span class="text-amber-700 font-bold">${fileInput.files[0].name}</span> (${(fileInput.files[0].size / 1024 / 1024).toFixed(2)} MB)`;
      const titleInput = document.getElementById('book-subject-title');
      if (!titleInput.value) {
        let cleanName = fileInput.files[0].name.replace(/\.pdf$/i, '').replace(/[-_]+/g, ' ').trim();
        titleInput.value = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);
      }
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileInput.files.length) {
      alert('Please select a subject book PDF file to synthesize questions.');
      return;
    }

    const formData = new FormData(form);
    progressContainer.classList.remove('hidden');
    btnSubmit.disabled = true;

    try {
      const res = await fetch('/api/upload_book', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.status === 'success') {
        modal.classList.add('hidden');
        await loadQuestionBanks();
        
        // Select the synthesized bank
        currentPayload.bank_id = data.bank.id;
        const sel = document.getElementById('bank-select');
        if (sel) sel.value = data.bank.id;
        
        // If header config is provided, apply to currentPayload
        if (data.bank.header_config) {
          currentPayload.header = Object.assign({}, currentPayload.header, data.bank.header_config);
          if (document.getElementById('input-inst-name')) document.getElementById('input-inst-name').value = data.bank.header_config.inst_name || '';
          if (document.getElementById('input-test-title')) document.getElementById('input-test-title').value = data.bank.header_config.test_title || '';
          if (document.getElementById('input-marks-text')) document.getElementById('input-marks-text').value = data.bank.header_config.marks_text || '';
        }
        
        currentPayload.range_type = 'all';
        currentPayload.total_questions = data.bank.total_questions || 20;
        document.getElementById('input-total-q').value = currentPayload.total_questions;
        
        updatePreview();
        alert(`Success! Generated Question Paper from Subject Book:\n• Part A: ${data.bank.total_questions} MCQs (1 Mark)\n• Part B: ${data.bank.short_questions?.length || 0} Short Answer Questions\n• Part C: ${data.bank.long_questions?.length || 0} Descriptive / 16-Mark Questions\n• Total Marks: ${data.bank.grand_total_marks || 50}`);
      } else {
        alert('Synthesis failed: ' + (data.message || 'Unknown error'));
      }
    } catch (err) {
      alert('Upload error: ' + err.message);
    } finally {
      progressContainer.classList.add('hidden');
      btnSubmit.disabled = false;
    }
  });
}
