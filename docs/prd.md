# PRD – Agentic SDLC (agent_ai) Değişiklik Kaydı

## Proje Tanımı
Python tabanlı yapay zeka ajanları ile simüle edilmiş bir yazılım geliştirme pipeline'ı.  
Her ajan (PM, PO, Analyst, Developer, Tester) sırayla çalışarak müşteri isteğini belgelenmiş, kodlanmış ve test edilmiş çıktıya dönüştürür.

---

## Değişiklik Kaydı

---

### [v1.2.0] – 2026-04-01

#### ✨ Feature: Odev Teslim Paketi ve Domain-Disi Agent Pipeline

| Alan | Detay |
|------|-------|
| **Yeni Dosya** | `docs/assignment_report_tr.md` |
| **Açıklama** | Agent-based systems dersi için Part 1-4 yapısında Türkçe teslim raporu eklendi. Framework çalıştırma adımları, gözlemler, sistem analizi, refleksiyon ve ekler (komutlar/notlar) dokümana işlendi. |
| **Yeni Dosya** | `projects/Education_Lesson_Design_Agents/pipeline.py` |
| **Açıklama** | Yazılım geliştirme dışı bir domain (eğitim/lesson design) için çok-ajanslı örnek pipeline implementasyonu eklendi. 5 ajanlı akış: Coordinator → CurriculumDesigner → ActivityPlanner → Assessment → QualityReviewer. |
| **Üretilen Çıktılar** | `projects/Education_Lesson_Design_Agents/output/pipeline_output.json`, `projects/Education_Lesson_Design_Agents/output/pipeline_log.txt` |
| **Açıklama** | Part 3 ekinde kullanılacak örnek pipeline çıktıları üretildi. |
| **Ek Dosyalar** | `input_assignment.txt`, `input_quick.txt` |
| **Açıklama** | Provided framework için ödev odaklı örnek input dosyaları eklendi. |

---

### [v1.2.1] – 2026-04-01

#### 📄 Dokümantasyon Otomasyonu: Markdown → PDF

| Alan | Detay |
|------|-------|
| **Yeni Dosya** | `docs/generate_assignment_pdf.py` |
| **Açıklama** | `docs/assignment_report_tr.md` dosyasını teslime uygun `PDF` formatına dönüştüren ReportLab tabanlı script eklendi. Başlıklar, alt başlıklar, madde işaretleri ve kod blokları temel biçimlendirme ile render ediliyor. |
| **Üretilen Dosya** | `docs/assignment_report_tr.pdf` |
| **Açıklama** | Ödevin doğrudan teslim edilebilir PDF çıktısı üretildi. |
| **Bağımlılık** | `reportlab` (venv içinde kuruldu) |
| **Açıklama** | PDF üretimi için `.venv` ortamına eklendi. |

---

### [v1.1.0] – 2026-03-26

#### 🐛 Bug Fix: `detect_language` – Yanlış `.r` Uzantısı

| Alan | Detay |
|------|-------|
| **Dosya** | `main.py` |
| **Fonksiyon** | `detect_language(text)` |
| **Hata** | `"r"` tek karakterli dil adı olduğundan `"r" in text_lower` neredeyse her cümlede `True` dönüyordu. Örn. `"web application"` → `"r"` bulunur → `.r` uzantısı seçiliyordu. |
| **Düzeltme** | `import re` eklendi. Uzunluğu ≤ 3 karakter olan dil adları için `re.search(r'\b<lang>\b', ...)` ile **tam kelime sınırı (word boundary)** eşleştirmesi yapılıyor. Uzun isimler (`python`, `javascript` vb.) için eski `in` kontrolü korundu. |

```python
# Önce
if lang in text_lower:
    return ext

# Sonra
if len(lang) <= 3:
    if re.search(r'\b' + re.escape(lang) + r'\b', text_lower):
        return ext
else:
    if lang in text_lower:
        return ext
```

---

#### 🐛 Bug Fix: `code` Field – `TypeError: write() argument must be str, not dict`

| Alan | Detay |
|------|-------|
| **Dosya** | `main.py` |
| **Satır** | Developer Phase – kod kaydetme bloğu |
| **Hata** | Developer ajanı zaman zaman `"code"` alanını `str` yerine `dict` / `list` olarak döndürebiliyordu. `io_manager.write_file()` yalnızca `str` kabul ettiğinden `TypeError` fırlatılıyordu. |
| **Düzeltme** | Kod kaydedilmeden önce tür kontrolü eklendi; `dict` veya `list` ise `json.dumps()` ile stringe çevriliyor. |

```python
if isinstance(code, dict) or isinstance(code, list):
    code = json.dumps(code, indent=4, ensure_ascii=False)
elif not isinstance(code, str):
    code = str(code) if code else ""
```

---

#### 📄 README Güncellemesi

| Alan | Detay |
|------|-------|
| **Dosya** | `README.md` |
| **Değişiklik** | `Output` bölümüne `io_manager.py`'de oluşturulan ancak dökümanda eksik olan `analysis/` ve `output/` klasörleri eklendi. |

---

## Mevcut Pipeline Akışı

```
input.txt
    └─► PM Agent    → demand.txt
    └─► PO Agent    → tasks/001_project_tasks.json
    └─► Analyst     → task comments (JSON)
    └─► Developer   → codes/<id>_code.<ext>
    └─► Tester      → task comments (PASS/FAIL)
```

## Proje Yapısı (Güncel)

```
agentic_sdlc/
├── agents/                  # Her ajan için prompt dosyaları
├── company_vault/           # Geçmiş projeler ve kodlama standartları
│   ├── coding_standards.md
│   └── previous_projects/
├── core/
│   ├── agent.py             # Gemini API sarmalayıcı
│   └── io_manager.py        # Dosya işlemleri
├── docs/
│   └── prd.md               # Bu döküman
├── projects/<proje_adı>/
│   ├── demand.txt
│   ├── analysis/            # Analist notları (rezerve)
│   ├── codes/               # Üretilen kaynak dosyalar
│   ├── output/              # Derlenmiş çıktı (rezerve)
│   ├── tasks/
│   └── tests/
├── static/
├── templates/
├── app.py
├── config.py
├── main.py
└── input.txt
```

## Bilinen Kısıtlamalar / Notlar

- `company_vault/previous_projects/` altındaki geçmiş projeler tüm ajanlara context olarak iletilir. Çok sayıda veya alakasız geçmiş proje varsa PO ajanı yanlış görevler üretebilir (örn. Calculator context'i yeni proje için yanlış görev seti oluşturabilir). Geçmiş projelerin ilgili ve minimal tutulması önerilir.
- Dil tespiti `demand.txt` + `initial_request` metnine dayanır; müşteri isteğinde açıkça dil belirtilmezse varsayılan `py` kullanılır.
