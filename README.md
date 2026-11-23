# Question Paper Studio - ITI Trade & Engineering Exams

A production-grade, full-featured web application for creating, customizing, synthesizing, and exporting professional bilingual (English & Tamil) examination question papers. Features automated multi-page distribution, exact auto-fit font tuning, pure diagram extraction, subject book AI/NLP synthesis, Google Form progression, and dual export to **PDF** and **Microsoft Word (DOCX)**.

---

## 🚀 Quick Start & Launch

### 1. Run Locally (Desktop / Laptop)
In your terminal, navigate to the folder and run:
```bash
cd /Users/tharungodwin/Downloads/question_paper_app
./run.sh
```
The server will boot and display your local and network access links:
- **Local Access:** `http://localhost:5050`
- **Network Access:** `http://192.168.1.4:5050` (or your machine's Wi-Fi IP)

### 2. Access on Mobile Phones & Tablets
Any device connected to the same Wi-Fi network (Android smartphones, iPhones, iPads, Android tablets) can open the application instantly:
1. Connect your mobile or tablet to the same Wi-Fi network.
2. Open Chrome or Safari and enter: `http://192.168.1.4:5050`
3. Enjoy a fully responsive mobile interface with off-canvas slide-out controls drawer, touch-friendly zoom, and auto-scaled live previews.

### 3. Production Deployment with Docker
For 1-command deployment on any Linux server, VPS, or cloud host:
```bash
docker-compose up -d --build
```

---

## 🌟 Complete Feature Overview

### 1. Cross-Device Responsive UI/UX (Mobile, Tablet & Desktop)
- **Mobile Off-Canvas Controls**: On screens `< 768px`, the sidebar smoothly slides out as an off-canvas drawer with backdrop overlay. Tap **View Question Paper** or the backdrop to dismiss.
- **Auto-Fit Scaled Canvas**: Dynamic zoom calculation (`Fit Width` and `Fit Page`) prevents any unwanted horizontal overflow on narrow smartphone viewports.
- **Scroll-Proof Modals**: All dialogs (`Upload PDF`, `Subject Book`, `Add Question`, `Google Form`, `Paper Format`) adapt with responsive max-height and internal scrolling so action buttons are never cut off.

### 2. Question Banks & Page Range Selection
- **Pre-analyzed NIMI Question Banks**: Fitter Trade Theory (Modules 1, 2, and Semester 1 Tamil).
- **Custom Page Range Filtering**: Select questions from specific PDF pages:
  - Continuous ranges: `1-10, 15, 24-32`
  - Discrete / random page ranges: `1, 4, 6, 8`
  - Full Question Bank allocation or predefined sets (`Q1–Q20`, `Q21–Q40`, etc.).
- **Sequential vs. Random Allocation**: Shuffle with a reproducible random seed or preserve exact book sequence.

### 3. Subject Book to Question Paper Synthesis (`book_analyzer.py`)
- Turn **raw textbook / subject book PDFs** (without existing question banks) into structured exam papers.
- Automatically extracts chapters, topics, definitions, and technical principles.
- Synthesizes:
  - **Part A (1-Mark MCQs)**: Synthesizes core questions with 4 plausible technical distractors.
  - **Part B (2/3-Mark Short Answer)**: Generates conceptual definitions, distinctions, and functions.
  - **Part C (10/16-Mark Descriptive & Essay)**: Creates in-depth analytical questions with neat sketch requirements.
- Configures comprehensive blueprints and calculates Maximum Marks automatically.

### 4. Pure Technical Diagram Extraction & Filtering
- **Pure Diagram Isolation**: Zero text word capture inside diagrams—eliminates question stems, table borders, and option letters from image boxes.
- **False-Positive Elimination**: Completely removes accidental image slices from plain-text multi-line questions.
- **Bilingual Diagram Integration**: Displays Tamil translation under English text while keeping pure diagrams crisp and sharply bounded.

### 5. Multi-Page Auto-Fitting & Dimensions
- **Strict Page Count Fitting**: Target 1, 2, 3, 4, or custom page counts. The auto-fit engine dynamically calculates font sizes (`7.5pt` to `12pt`), line spacing, padding, and image heights so the exam strictly fills the target pages with zero trailing blank sheets.
- **Paper Formats**: Supports **A4**, **A3**, **Letter**, **Legal**, and **A5**.
- **Angle / Orientation**: Supports **Vertical (Portrait)** and **Horizontal (Landscape)** with automatic 2-column NCVT board exam layout.

### 6. Institutional Header & Footer Customization
- **Header Placement**: Page 1 only or All Pages.
- **Fields**: Institution Name, Test Title, Session / Month-Year, Date, Time, Registration Number, and Maximum Marks.
- **General Instructions**: Standard examination instructions box.
- **Footer**: Custom footer text and dynamic page numbering (`Page 1 of 2`).

### 7. Google Form Quiz Generator
- **Auto Progression (Google Apps Script)**: Generates a complete `.gs` script that creates an authenticated Google Form Quiz in your Google Drive with 1 click, complete with bilingual questions, options, answer keys, and point values.
- **Manual Form Builder Text**: Formatted plain-text quiz for quick copy-pasting into Form Builder extensions or Google Docs.

### 8. Manual Question Builder
- Add single questions directly into any bank.
- Toggle between Multiple Choice (A/B/C/D) and Short/Essay questions.
- Attach custom image/diagram files.
- Full bilingual English + Tamil support.

### 9. Dual Export: Vector PDF & Microsoft Word (DOCX)
- **PDF Export**: Pixel-perfect vector PDF compiled via headless Google Chrome / Chromium.
- **DOCX Export**: Structured Word document with embedded tables, native headings, and crisp images.

---

## 🛠️ Technology Stack
- **Backend**: Python 3.12, Flask, Gunicorn WSGI.
- **PDF Engine**: Google Chrome / Chromium Headless (`--print-to-pdf`), PyMuPDF (`fitz`), pypdf.
- **DOCX Engine**: `python-docx` with XML cell shading and responsive table layouts.
- **OCR & Computer Vision**: OpenCV (`cv2`), PyTesseract, Pillow (`PIL`).
- **Frontend**: HTML5, TailwindCSS, FontAwesome 6, Vanilla JavaScript.

---

## 📄 License & Attribution
Developed for Government ITI Veerakerlampudur & Technical Vocational Institutes.
