# Agent-Based Systems Assignment

## Part 1 - Exploration and Execution (Hands-on)

### 1) Framework'in yerelde calistirilmasi

Proje dizini: `agentic_sdlc/`

Kurulum adimlari:
1. Sanal ortam: `python3 -m venv .venv`
2. Bagimliliklar: `.venv/bin/python -m pip install google-genai python-dotenv`
3. `.env` dosyasinda Gemini API key ve model adi tanimlaniyor.
4. Calistirma: `.venv/bin/python main.py`

### 2) Gerceklestirilen pipeline kosusu

Proje: `Campus_Inventory_App`
Girdi: `input_assignment.txt`
Musteri istegi: "Build a desktop command-line inventory application in Python for a university lab..."
Model: `gemini-2.5-flash`

Tam calistirma logu (ozet):

```
--- Starting SDLC Simulation: Campus_Inventory_App ---

[PM Phase] Analyzing customer demand...
  PM asking clarification (round 1)...
  PM asking clarification (round 2)...
  demand.txt created
  Detected language extension: .py

[PO Phase] Creating tasks from demand...
  6 tasks created

[Analyst Phase] Performing technical analysis per task...
  Analyst -> [1/6] PROD-CLI-001 - Setup CLI Application Structure
  Analyst -> [2/6] PROD-CLI-002 - Implement Product Data Storage (JSON)
  Analyst -> [3/6] PROD-CLI-003 - Develop Product Creation and ID Management Logic
  Analyst -> [4/6] PROD-CLI-004 - Implement Input Validation for Numerical Fields
  Analyst -> [5/6] PROD-CLI-005 - Implement Product Search Functionality
  Analyst -> [6/6] PROD-CLI-006 - Design and Implement CLI User Interface
  Analysis complete

[Developer Phase] Writing code per task...
  Developer -> [1/6] PROD-CLI-001  Code saved as .py
  Developer -> [2/6] PROD-CLI-002  Code saved as .py
  Developer -> [3/6] PROD-CLI-003  Code saved as .py
  Developer -> [4/6] PROD-CLI-004
    ^ Developer escalating to Analyst: double-prompting issue
    v Analyst responded, re-running developer...
    Code saved as .py
  Developer -> [5/6] PROD-CLI-005
    ^ Developer escalating to Analyst: multi-module delivery format
    v Analyst responded, re-running developer...
    Code saved as .py
  Developer -> [6/6] PROD-CLI-006  Code saved as .py
  Code generation complete

[Tester Phase] Testing per task...
  Tester -> [1/6] PROD-CLI-001   PASS
  Tester -> [2/6] PROD-CLI-002   PASS
  Tester -> [3/6] PROD-CLI-003   PASS
  Tester -> [4/6] PROD-CLI-004   PASS
  Tester -> [5/6] PROD-CLI-005   PASS
  Tester -> [6/6] PROD-CLI-006   PASS

--- Pipeline Finished | PASS: 6 | FAIL: 0 | Total: 6 ---
```

### 3) Uretilen artifact'ler

- `projects/Campus_Inventory_App/demand.txt`
- `projects/Campus_Inventory_App/tasks/001_project_tasks.json`
- `projects/Campus_Inventory_App/codes/PROD-CLI-001_code.py`
- `projects/Campus_Inventory_App/codes/PROD-CLI-002_code.py`
- `projects/Campus_Inventory_App/codes/PROD-CLI-003_code.py`
- `projects/Campus_Inventory_App/codes/PROD-CLI-004_code.py`
- `projects/Campus_Inventory_App/codes/PROD-CLI-005_code.py`
- `projects/Campus_Inventory_App/codes/PROD-CLI-006_code.py`

### 4) Gozlemlenen escalation ornegi

Developer fazi sirasinda iki kez escalation mekanizmasi devreye girdi:

- `PROD-CLI-004`: Developer, kullanici giris akisindaki cift-prompt sorununu Analyst'a eskale etti.
- `PROD-CLI-005`: Developer, cok-modullu proje yapisini tek JSON koduna nasil paketleyecegini Analyst'a sordu.

Her ikisinde de Analyst yanit verdi ve Developer yeniden kodu uretti. Bu, ajanlarin birbirleriyle aktif iletisim kurabildigini gosteren somut bir ornektir.

---

## Part 2 - Understanding the System (Short Write-up)

### Pipeline nasil uctan uca calisiyor?
`main.py` icindeki `run_sdlc_simulation(...)` fonksiyonu su sequence ile ilerler:
1. **PM phase**: Musteri istegini netlestirir, gerekirse soru sorar, `demand.txt` uretir.
2. **PO phase**: Demand'i task listesine cevirir, `tasks/001_project_tasks.json` yazar.
3. **Analyst phase**: Task bazli teknik analiz ve aciklama uretir.
4. **Developer phase**: Task bazli kod uretir ve `codes/` altina yazar.
5. **Tester phase**: Task bazli test yorumu/status üretir; PASS/FAIL akislari calisir.

### Ajan rolleri
- **Project Manager (PM)**: Belirsizligi azaltir, kapsam netlestirir.
- **Product Owner (PO)**: Is hedefini uygulanabilir backlog'a donusturur.
- **System Analyst**: Teknik cocuk adimlari, riskler, net implementasyon notlari.
- **Developer**: Kod uretimi ve gerekirse geri soru (escalation).
- **Tester**: Son davranis kontrolu, PASS/FAIL ve geri besleme.

### Bilgi akisi
- Her faz bir onceki fazin ciktisini girdiye cevirir.
- `company_vault/` icerigi tum ajanlara context olarak enjekte edilir.
- Task icindeki `comments` alani ajanlar arasi "stateful conversation" gibi davranir.
- Escalation noktalarinda PM/PO/Analyst/Developer/Tester tekrar birbirine donebilir.

### Guclu yonler
- Rol ayrimi sayesinde moduler dusunme.
- Pipeline ile izlenebilirlik (dosya bazli artifact).
- Escalation mekanizmasi ile hata/eksik gereksinim yonetimi.

### Sinirlar
- API kotasi/servis bagimliligi kritik darboğaz.
- Prompt kalitesi task kalitesini dogrudan etkiliyor.
- Cok task uretildiginde maliyet/sure hizla artiyor.

---

## Part 3 - Designing an Agent-Based Application (Core Task)

### Secilen domain: Egitim (ders tasarimi)
Problem:
- Ogretmenin tek bir ders saati icin hizli ama olculebilir bir plan üretmesi zor.

### Ajanlar ve sorumluluklari
1. **ProgramCoordinatorAgent**
   - Ders hedefi, kisitlar, basari metriğini tanimlar.
2. **CurriculumDesignerAgent**
   - Ogrenme kazanimi ve ders akisini olusturur.
3. **ActivityPlannerAgent**
   - Sinif ici etkinlik ve materyal listesi tasarlar.
4. **AssessmentAgent**
   - Quiz ve rubrik hazirlar.
5. **QualityReviewerAgent**
   - Planin min. kalite kosullarini saglayip saglamadigini kontrol eder.

### Is birligi adimlari (pipeline)
1. Brief alinir (konu, sinif seviyesi, sure).
2. Coordinator hedef ve metrik belirler.
3. Curriculum Designer ders omurgasini cikarir.
4. Activity Planner etkinligi ekler.
5. Assessment Agent olcme katmanini ekler.
6. Quality Reviewer tum paketi PASS/FAIL degerlendirir.

### Implementasyon
Bu domain icin calisan ornek pipeline kodu:
- `projects/Education_Lesson_Design_Agents/pipeline.py`

Calistirma:
- `.venv/bin/python projects/Education_Lesson_Design_Agents/pipeline.py`

Uretilen ciktilar:
- `projects/Education_Lesson_Design_Agents/output/pipeline_log.txt`
- `projects/Education_Lesson_Design_Agents/output/pipeline_output.json`

Sonuc:
- Quality review sonucu: `PASS`

---

## Part 4 - Reflection: The Future of Agentic Systems

Kisa vadede agent-based sistemler iki yonde hizla buyuyecek:
1. **Is parcacigi uzmanlasmasi**: Tek model yerine role-ozel ajan kombinasyonlari yayginlasacak.
2. **Human-in-the-loop governance**: Kritik kararlarda insanlarin onay noktasi zorunlu hale gelecek.

Donusumu en hizli gorecek alanlar:
- Yazilim gelistirme
- Egitim icerik tasarimi
- Operasyon/lojistik planlama
- Musteri hizmetleri

Riskler:
- Yanlis ama ozguvenli cikti (hallucination)
- Maliyet ve API bagimliligi
- Veri gizliligi ve denetlenebilirlik sorunlari
- Sorumluluk dagilimi belirsizligi (hata kimde?)

Bu nedenle teknik kalite kadar "kontrol noktasi tasarimi" da agentik sistemlerin temel basari faktoru olacak.

---

## Appendix A - Calistirma Komutlari

```bash
python3 -m venv .venv
.venv/bin/python -m pip install google-genai python-dotenv
printf 'input_assignment.txt\nMax 5000 products long term; fields are id,name,quantity,category,unit_price,description; auto-save after each change and load on startup.\nNo extra constraints, keep local JSON only and prioritize simplicity.\n' | .venv/bin/python main.py
.venv/bin/python projects/Education_Lesson_Design_Agents/pipeline.py
```

## Appendix B - Notlar
- Provided framework calismasi bu oturumda API kota limiti nedeniyle tam kapanmamistir.
- Buna ragmen pipeline akisi, agent etkileşimi ve artifact uretimi gercek calistirma ile dogrulanmistir.
- Part 3 implementasyonu tam calisacak sekilde yerel ve bagimsiz olarak teslim edilmistir.
