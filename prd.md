PRD: Multi-Agent Social Media Post Automation System
1. Project Name

Smart Social Media Agent Orchestrator

2. Product Goal

Bu projenin amacı, kullanıcının sosyal medya paylaşımı isteğini analiz eden ve ihtiyaca göre farklı uzman ajanları çalıştıran otomatik bir sistem geliştirmektir.

Sistem her istekte aynı adımları çalıştırmayacaktır. Kullanıcı zaten metin verdiyse Writer Agent atlanacaktır. Kullanıcı trend istemediyse Researcher Agent atlanacaktır. Böylece sistem daha hızlı, daha ucuz ve daha sürdürülebilir çalışacaktır.

3. Problem Statement

Sosyal medya paylaşımı hazırlamak çok adımlı bir süreçtir:

Trend araştırması yapmak
Caption yazmak
Görsel veya video oluşturmak
İçeriği kalite ve güvenlik açısından kontrol etmek
Sosyal medya platformuna yüklemek

Ancak her kullanıcı isteği aynı detay seviyesinde değildir.

Örnek:

Post a Pilates picture.

Bu istek için sistemin araştırma, yazı yazma, görsel oluşturma ve yükleme adımlarını yapması gerekir.

Başka bir örnek:

Share this exact text: "Join my class!" with a picture of a reformer bed.

Bu istekte metin zaten hazırdır. Bu yüzden Writer Agent çalıştırılmamalıdır.

Eğer tek bir agent bütün işi yaparsa, görev karmaşıklaşır ve hata yapma ihtimali artar. Bu yüzden sistem birden fazla uzman agent kullanacaktır.

4. Target Users

Bu sistem şu kullanıcılar için tasarlanmıştır:

Küçük işletme sahipleri
Fitness / Pilates eğitmenleri
İçerik üreticileri
Sosyal medya yöneticileri
Ajanslar
Otomasyon sistemi geliştirmek isteyen yazılımcılar
5. Main User Stories
User Story 1

Kullanıcı kısa bir prompt verir.

Make a post about Pilates.

Sistem trendleri araştırır, caption yazar, görsel promptu üretir, görsel oluşturur, kalite kontrol yapar ve paylaşım aşamasına geçer.

User Story 2

Kullanıcı hazır metin verir.

Share this exact text: "Join my Pilates class today!" with a picture of a reformer bed.

Sistem Writer Agent’ı atlar. Sadece görsel üretir, QA yapar ve browser automation aşamasına geçer.

User Story 3

Kullanıcı sadece caption ister.

Write a caption for a calm morning yoga post.

Sistem sadece Researcher ve Writer Agent’ı çalıştırabilir. Media Creator ve Browser Agent çalıştırılmaz.

User Story 4

Kullanıcı sadece upload ister.

Upload this caption and image to Instagram.

Sistem Researcher, Writer ve Media Creator agentlarını atlar. QA ve Browser Agent çalışır.

6. Core Features
6.1 Task Manager Agent

Task Manager sistemin merkezidir.

Görevleri:

Kullanıcı promptunu analiz eder.
Hangi agentların çalışması gerektiğine karar verir.
Her agenttan gelen çıktıyı kontrol eder.
Eksik bilgi varsa başka agent çağırır.
Hatalı çıktı varsa ilgili agentı tekrar çalıştırır.
Final durumda Browser Agent’a paylaşım görevini verir.

Task Manager şu kararları verebilmelidir:

has_caption: true / false
needs_research: true / false
needs_media: true / false
has_media_file: true / false
needs_upload: true / false
needs_qa: true / false
6.2 Trend Researcher Agent

Görevi:

Konuyla ilgili trend keyword ve hashtag bulmak.
Ücretsiz modda internet scraping yapılmadan mock veya basit kaynaklarla çalışabilir.
Gelişmiş modda web search API kullanılabilir.

Output örneği:

{
  "keywords": ["pilates", "reformer pilates", "wellness", "morning routine"],
  "hashtags": ["#pilates", "#reformerpilates", "#wellness", "#fitnessmotivation"]
}
6.3 Content Writer Agent

Görevi:

Caption oluşturmak.
Media Creator Agent için görsel promptu oluşturmak.
Kullanıcının tonunu dikkate almak.

Input:

{
  "topic": "Pilates",
  "keywords": ["pilates", "wellness"],
  "style": "friendly and motivational"
}

Output:

{
  "caption": "Start your day strong with mindful Pilates movement. Build strength, balance, and confidence one breath at a time. #pilates #wellness",
  "media_prompt": "A bright and calming Pilates studio with a reformer bed, soft morning light, minimal aesthetic"
}
6.4 Media Creator Agent

Görevi:

Görsel veya video üretmek.
Ücretsiz prototipte gerçek AI image API kullanmak zorunda değildir.
İlk versiyonda placeholder görsel kullanılabilir.
Daha sonra Stable Diffusion veya başka image API entegre edilebilir.

Ücretsiz öneri:

Placeholder image generator
Local image template
PIL / Pillow ile basit görsel oluşturma
Unsplash API yerine manuel local image klasörü

Output:

{
  "media_path": "outputs/pilates_post.jpg",
  "media_type": "image"
}
6.5 QA Agent

Görevi:

Caption uygun mu?
Görsel prompt ile konu uyumlu mu?
Hassas, zararlı veya marka açısından riskli içerik var mı?
Metin çok uzun mu?
Hashtag sayısı uygun mu?

Output:

{
  "status": "approved",
  "feedback": "Caption and media are aligned with the Pilates topic."
}

veya

{
  "status": "rejected",
  "feedback": "Caption is too generic. Add a clearer call to action."
}
6.6 Browser Operator Agent

Görevi:

Playwright ile browser açmak.
Login gerektiren işlemler için kullanıcı oturumunun daha önce açılmış olmasını beklemek.
Dosya upload etmek.
Caption eklemek.
Share / Post butonuna basmak.
Ekranı kontrol ederek başarılı olup olmadığını raporlamak.

İlk versiyonda gerçek Instagram paylaşımı yerine local demo sayfası kullanılmalıdır.

Neden?

Instagram, TikTok, Facebook gibi platformlarda otomasyon kuralları, bot algılama ve login sorunları olabilir. Bu yüzden ilk MVP’de browser automation bir demo HTML sayfası üzerinde test edilmelidir.

7. MVP Scope

İlk versiyonda yapılacaklar:

CLI veya basit web arayüzü
Task Manager routing logic
Researcher mock data
Writer agent
Media Creator placeholder image
QA agent
Browser Agent ile local demo page upload
JSON tabanlı step logs
Hata durumunda retry mekanizması
8. Out of Scope for MVP

İlk versiyonda yapılmayacaklar:

Gerçek Instagram / TikTok paylaşımı
Gerçek trend API entegrasyonu
Ücretli image generation API kullanımı
Çok kullanıcılı authentication sistemi
Database kullanımı
Production deployment
Video generation
9. Recommended Free Tech Stack
Backend
Python 3.11+
Agent Framework

İki seçenek var:

Seçenek A: Framework kullanmadan custom agent routing

MVP için en iyi seçenek budur.

Avantajları:

Ücretsiz
Daha anlaşılır
Daha az bağımlılık
Proje sunumu için daha net
Task Manager mantığı kolay gösterilir
Seçenek B: LangChain

Avantajları:

Agent mimarisi daha profesyonel görünür
Daha sonra LLM entegrasyonu kolay olur

Dezavantajları:

Yeni başlayanlar için karmaşık olabilir
Gereksiz bağımlılık ekleyebilir

Benim önerim:

MVP için custom Python classes kullan.
Final raporda LangChain veya CrewAI ile genişletilebilir olduğunu belirt.
Browser Automation
Playwright

Ücretsizdir.

Kurulum:

pip install playwright
playwright install
Image Generation

MVP için ücretsiz seçenek:

Pillow ile otomatik placeholder görsel oluşturma

Kurulum:

pip install pillow

Örnek çıktı:

outputs/pilates_post.jpg
LLM Kullanımı

Ücretsiz kalmak için ilk prototipte gerçek LLM API kullanmadan rule-based logic kullanılabilir.

Örneğin:

Kullanıcı promptunda "share this exact text" geçiyorsa Writer Agent atlanır.
Promptta "post", "upload", "share" varsa Browser Agent çalışır.
Promptta "picture", "image", "photo" varsa Media Creator çalışır.
Prompt kısa ve genel ise Researcher çalışır.

Daha sonra LLM eklenebilir.

10. Ücret Gerektirebilecek Kısımlar

Bu projeyi tamamen ücretsiz MVP olarak yapabilirsin. Ancak aşağıdaki özellikler eklenirse ücret gerekebilir:

Özellik	Ücret Gerekir mi?	Açıklama
Python	Hayır	Ücretsiz
Playwright	Hayır	Ücretsiz
Pillow	Hayır	Ücretsiz
Local demo upload page	Hayır	Ücretsiz
LangChain	Hayır	Kütüphane ücretsiz
CrewAI	Genelde hayır	Bazı cloud özellikleri ücretli olabilir
OpenAI API	Evet	Token bazlı ücretlidir
Claude API	Evet	Token bazlı ücretlidir
Gemini API	Bazen	Free tier olabilir ama limitlidir
Real image generation API	Genelde evet	DALL·E, Midjourney, Runway vb. ücretli olabilir
Instagram API	Duruma bağlı	Meta developer setup ve onay süreçleri gerekebilir
Gerçek Instagram browser automation	Riskli	Platform kurallarına ve bot algılamaya takılabilir
Hosting / deployment	Bazen	Render, Railway, Vercel free tier kullanılabilir ama limitli
11. Recommended MVP Architecture
project/
│
├── main.py
├── config.py
├── requirements.txt
├── README.md
│
├── agents/
│   ├── task_manager.py
│   ├── researcher.py
│   ├── writer.py
│   ├── media_creator.py
│   ├── qa_agent.py
│   └── browser_operator.py
│
├── outputs/
│   ├── generated_post.jpg
│   └── logs.json
│
├── browser/
│   ├── demo_upload_page.html
│   └── upload_script.py
│
└── tests/
    ├── test_task_manager.py
    ├── test_writer.py
    └── test_qa.py
12. System Flow
Scenario A: Short Prompt

Input:

Make a post about Pilates.

Flow:

User
↓
Task Manager
↓
Researcher Agent
↓
Task Manager
↓
Writer Agent
↓
Task Manager
↓
Media Creator Agent
↓
Task Manager
↓
QA Agent
↓
Task Manager
↓
Browser Operator Agent
↓
Success Message
Scenario B: Detailed Prompt

Input:

Share this exact text: "Join my class!" with a picture of a reformer bed.

Flow:

User
↓
Task Manager
↓
Media Creator Agent
↓
Task Manager
↓
QA Agent
↓
Task Manager
↓
Browser Operator Agent
↓
Success Message

Skipped agents:

Researcher Agent
Writer Agent
13. Functional Requirements
FR1: Prompt Analysis

The system must analyze user prompts and extract:

{
  "topic": "Pilates",
  "caption": null,
  "needs_research": true,
  "needs_writer": true,
  "needs_media": true,
  "needs_upload": true
}
FR2: Dynamic Routing

The Task Manager must decide which agents to call.

Example:

{
  "researcher": true,
  "writer": true,
  "media_creator": true,
  "qa": true,
  "browser": true
}
FR3: Agent Output Validation

The Task Manager must validate each agent output.

Example checks:

Researcher returns at least 3 keywords.
Writer returns caption and media prompt.
Media Creator returns an existing file path.
QA returns approved or rejected.
Browser Operator returns success or error.
FR4: Retry Logic

If an agent fails, the Task Manager should retry once.

Example:

Media Creator failed because file was not created.
Retrying Media Creator one more time.
FR5: Logging

Every step should be logged into:

outputs/logs.json

Example log:

[
  {
    "step": "task_manager",
    "status": "success",
    "message": "Prompt analyzed successfully."
  },
  {
    "step": "writer",
    "status": "success",
    "message": "Caption generated."
  }
]
14. Non-Functional Requirements
Performance

The MVP should complete a basic post generation flow in under 30 seconds on a local machine.

Cost

The MVP must work without paid APIs.

Maintainability

Each agent should be a separate Python class.

Sustainability

The system should avoid unnecessary agent calls.

Reliability

If one agent fails, the whole system should not immediately crash. The Task Manager should handle the error.

15. Acceptance Criteria

The project is successful if:

A user can enter a prompt.
The Task Manager creates a routing plan.
Only necessary agents are called.
The system creates or accepts a caption.
The system creates a local image file.
QA approves or rejects the result.
Browser Agent uploads the content to a local demo page.
Logs are saved.
At least two scenarios are demonstrated:
Short prompt
Detailed prompt
To-Do List for Codex
Phase 1: Project Setup
[ ] Create Python project structure.
[ ] Create requirements.txt.
[ ] Add playwright and pillow dependencies.
[ ] Create README.md.
[ ] Create outputs/ folder.
[ ] Create agents/ folder.
[ ] Create browser/ folder.
[ ] Create tests/ folder.
Phase 2: Define Shared Data Model
[ ] Create a PostRequest data structure.
[ ] Create a PostState data structure.
[ ] Store user_prompt.
[ ] Store topic.
[ ] Store caption.
[ ] Store media_prompt.
[ ] Store media_path.
[ ] Store keywords.
[ ] Store hashtags.
[ ] Store routing_plan.
[ ] Store QA result.
[ ] Store browser result.

Önerilen basit Python modeli:

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class PostState:
    user_prompt: str
    topic: Optional[str] = None
    caption: Optional[str] = None
    media_prompt: Optional[str] = None
    media_path: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    routing_plan: Dict[str, bool] = field(default_factory=dict)
    qa_status: Optional[str] = None
    qa_feedback: Optional[str] = None
    browser_status: Optional[str] = None
    logs: List[Dict[str, Any]] = field(default_factory=list)
Phase 3: Build Task Manager Agent
[ ] Create agents/task_manager.py.
[ ] Implement analyze_prompt().
[ ] Detect if prompt contains exact caption.
[ ] Detect if prompt needs image.
[ ] Detect if prompt needs upload.
[ ] Detect if prompt is short and needs research.
[ ] Create routing plan.
[ ] Add validation after each agent output.
[ ] Add retry logic.
[ ] Add final success response.

Routing rules:

If prompt contains "exact text" or quotation marks, assume caption is provided.
If prompt contains "picture", "image", "photo", "video", assume media is needed.
If prompt contains "post", "upload", "share", assume upload is needed.
If prompt has fewer than 10 words and no caption, assume research is needed.
If caption is missing, Writer Agent is needed.
QA should always run before Browser Agent.
Browser Agent should only run if upload is needed.
Phase 4: Build Researcher Agent
[ ] Create agents/researcher.py.
[ ] Implement get_trends(topic).
[ ] Return mock keywords.
[ ] Return mock hashtags.
[ ] Make output JSON-compatible.

Example output:

{
    "keywords": ["pilates", "reformer pilates", "wellness", "core strength"],
    "hashtags": ["#pilates", "#reformerpilates", "#wellness", "#fitness"]
}
Phase 5: Build Writer Agent
[ ] Create agents/writer.py.
[ ] Implement write_content(state).
[ ] Generate caption from topic, keywords, and hashtags.
[ ] Generate media_prompt.
[ ] If user already gave caption, do not overwrite it.
[ ] Return updated state.
Phase 6: Build Media Creator Agent
[ ] Create agents/media_creator.py.
[ ] Use Pillow to create a simple image.
[ ] Add title text to image.
[ ] Save image to outputs/generated_post.jpg.
[ ] Return media_path.
[ ] Validate that file exists.
Phase 7: Build QA Agent
[ ] Create agents/qa_agent.py.
[ ] Check caption is not empty.
[ ] Check caption length is acceptable.
[ ] Check media file exists if media is required.
[ ] Check banned words list.
[ ] Return approved or rejected.
[ ] Include feedback message.

Example banned words list:

["hate", "violence", "illegal"]
Phase 8: Build Browser Operator Agent
[ ] Create browser/demo_upload_page.html.
[ ] Create agents/browser_operator.py.
[ ] Use Playwright to open the local HTML file.
[ ] Fill caption input.
[ ] Upload image file.
[ ] Click fake Share button.
[ ] Read success message from page.
[ ] Return success or error.

Important:

Do not automate real Instagram in MVP.
Use local demo page first.
Phase 9: Build Main Program
[ ] Create main.py.
[ ] Accept user prompt from CLI.
[ ] Create PostState.
[ ] Run Task Manager.
[ ] Print routing plan.
[ ] Print final caption.
[ ] Print media path.
[ ] Print QA result.
[ ] Print browser result.
[ ] Save logs to outputs/logs.json.

Example CLI usage:

python main.py "Make a post about Pilates."
Phase 10: Testing
[ ] Test short prompt scenario.
[ ] Test detailed prompt scenario.
[ ] Test prompt with exact caption.
[ ] Test prompt without media request.
[ ] Test QA rejection.
[ ] Test media file creation.
[ ] Test browser upload on local demo page.
Suggested Implementation Prompt for Codex

Bunu direkt Codex’e verebilirsin:

Build a Python MVP for a multi-agent social media post automation system.

Use only free tools and local logic. Do not use paid APIs.

Project requirements:

1. Use Python 3.11+.
2. Use separate agent classes:
   - TaskManagerAgent
   - TrendResearcherAgent
   - ContentWriterAgent
   - MediaCreatorAgent
   - QAAgent
   - BrowserOperatorAgent

3. Use custom routing logic instead of paid LLM APIs.

4. The TaskManagerAgent must:
   - Analyze the user prompt.
   - Detect whether the user already provided caption text.
   - Decide whether research is needed.
   - Decide whether writing is needed.
   - Decide whether media generation is needed.
   - Decide whether browser upload is needed.
   - Skip unnecessary agents.
   - Validate every step.
   - Retry failed agents once.
   - Save logs.

5. The TrendResearcherAgent should return mock trend keywords and hashtags based on the topic.

6. The ContentWriterAgent should generate:
   - caption
   - media_prompt

7. The MediaCreatorAgent should use Pillow to generate a local placeholder image and save it to outputs/generated_post.jpg.

8. The QAAgent should check:
   - caption exists
   - caption length is reasonable
   - media file exists when required
   - banned words are not included

9. The BrowserOperatorAgent should use Playwright to open a local demo_upload_page.html file, fill the caption, upload the generated image, click a fake Share button, and confirm success.

10. Do not automate real Instagram, TikTok, or Facebook in the MVP.

11. Create this project structure:

project/
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── agents/
│   ├── __init__.py
│   ├── task_manager.py
│   ├── researcher.py
│   ├── writer.py
│   ├── media_creator.py
│   ├── qa_agent.py
│   └── browser_operator.py
├── browser/
│   └── demo_upload_page.html
├── outputs/
└── tests/

12. Include example commands in README.md.

13. Include at least two demo prompts:
   - "Make a post about Pilates."
   - "Share this exact text: 'Join my class!' with a picture of a reformer bed."

14. Make sure the code runs with:
   pip install -r requirements.txt
   playwright install
   python main.py "Make a post about Pilates."

15. Keep the code simple, readable, and suitable for a university project prototype.
Final Recommendation

Bu proje için en mantıklı MVP yaklaşımı:

Custom Python routing + Pillow image generation + Playwright local demo upload

Bu sayede:

API ücreti ödemezsin.
Gerçek sosyal medya hesabı riske girmez.
Multi-agent mantığını net şekilde gösterirsin.
Green coding / sustainability argümanını güçlü anlatırsın.
Proje sunumu için çalışan demo çıkarabilirsin.

Ücret çıkabilecek tek ciddi kısımlar şunlar olur:

Gerçek LLM API kullanmak
Gerçek AI image/video generation kullanmak
Gerçek Instagram/TikTok/Facebook paylaşımı yapmak
Cloud deployment yapmak

MVP’de bunların hiçbirine gerek yok.

PRD Update: Task Manager Clarification Logic
New Requirement: User Clarification

Task Manager Agent sadece agentları yönlendirmez; aynı zamanda eksik veya belirsiz bilgi olduğunda kullanıcıdan açıklama ister.

Bu sayede sistem yanlış işlem yapmak yerine önce eksik bilgiyi tamamlar.

Task Manager Agent Updated Responsibility

Task Manager Agent şunları yapmalıdır:

Kullanıcı promptunu analiz eder.
Hangi agentların çalışacağını belirler.
Eksik bilgi varsa kullanıcıya soru sorar.
Kullanıcı cevabını aldıktan sonra workflow’a devam eder.
Gereksiz agentları atlar.
Her agent çıktısını kontrol eder.
Hata durumunda retry yapar.
When Should Task Manager Ask the User?

Task Manager şu durumlarda kullanıcıya soru sormalıdır:

1. Platform belli değilse:
   "Which platform do you want to post on? Instagram, TikTok, LinkedIn, or X?"

2. Kullanıcı upload istiyor ama görsel veya metin eksikse:
   "Do you want me to create the caption, the image, or both?"

3. Kullanıcı sadece 'post this' diyor ama içerik vermiyorsa:
   "What topic should the post be about?"

4. Kullanıcı görsel istiyor ama görsel tarzı belirsizse:
   "What visual style do you prefer? Minimal, realistic, colorful, luxury, or fitness-focused?"

5. Kullanıcı exact text diyor ama tırnak içinde metin vermiyorsa:
   "Please provide the exact text you want me to use."

6. Kullanıcı gerçek sosyal medya upload istiyor ama MVP demo modundaysa:
   "This prototype supports local demo upload only. Should I continue with the demo upload page?"
Updated Routing Logic

Task Manager artık prompt analizinden sonra bir karar daha verir:

{
  "needs_clarification": true,
  "clarification_question": "What topic should the post be about?",
  "can_continue": false
}

Eğer açıklama gerekiyorsa sistem diğer agentları çağırmaz.

Updated Flow
[User Input]
     │
     ▼
[Task Manager]
     │
     ├── If information is missing:
     │       └── Ask user clarification question
     │
     └── If prompt is clear:
             └── Continue routing to agents
Example 1: Clarification Needed

User:

Post this.

Task Manager output:

{
  "needs_clarification": true,
  "clarification_question": "What content or topic should I post?",
  "can_continue": false
}

Assistant asks:

What content or topic should I post?
Example 2: No Clarification Needed

User:

Make a post about Pilates with a calm studio image.

Task Manager output:

{
  "needs_clarification": false,
  "can_continue": true,
  "routing_plan": {
    "researcher": true,
    "writer": true,
    "media_creator": true,
    "qa": true,
    "browser": true
  }
}
Updated Codex Prompt Section

Codex’e verdiğin prompta şunu ekle:

16. Add clarification logic to the TaskManagerAgent.

The TaskManagerAgent should be able to pause the workflow and ask the user a clarification question when the prompt is too vague or missing critical information.

Examples:
- If the user says "Post this" without content, ask: "What content or topic should I post?"
- If the platform is missing and upload is requested, ask: "Which platform should I post to?"
- If the user says "use this exact text" but does not provide the exact text, ask: "Please provide the exact text you want me to use."
- If the user asks for an image but the visual concept is unclear, ask: "What kind of image should I create?"
- If the user requests real social media upload in MVP mode, explain that the MVP supports local demo upload only and ask whether to continue with demo upload.

The TaskManagerAgent should return a structured response like:

{
  "needs_clarification": true,
  "clarification_question": "...",
  "can_continue": false
}

If needs_clarification is true:
- Do not call ResearcherAgent.
- Do not call WriterAgent.
- Do not call MediaCreatorAgent.
- Do not call QAAgent.
- Do not call BrowserOperatorAgent.
- Return the clarification question to the user.

After the user answers, merge the new answer into the existing PostState and continue the workflow.
Updated To-Do Item
Phase 3: Build Task Manager Agent

Şunu ekle:

[ ] Implement needs_clarification detection.
[ ] Add clarification_question field to PostState.
[ ] Add can_continue field to PostState.
[ ] If clarification is needed, stop agent routing.
[ ] Return the clarification question to the user.
[ ] After user response, merge clarification answer into previous state.
[ ] Continue workflow from Task Manager.
Updated PostState Model
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class PostState:
    user_prompt: str
    clarification_answer: Optional[str] = None

    topic: Optional[str] = None
    platform: Optional[str] = None
    caption: Optional[str] = None
    media_prompt: Optional[str] = None
    media_path: Optional[str] = None

    keywords: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)

    routing_plan: Dict[str, bool] = field(default_factory=dict)

    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    can_continue: bool = True

    qa_status: Optional[str] = None
    qa_feedback: Optional[str] = None
    browser_status: Optional[str] = None

    logs: List[Dict[str, Any]] = field(default_factory=list)
Important Design Note

Task Manager’ın soru sorabilmesi iyi bir özellik ama bunu sınırsız yapmamak gerekir.

Önerilen kural:

Task Manager en fazla 2 clarification question sormalı.

Çünkü sürekli soru soran sistem kullanıcı deneyimini kötüleştirir.

Bunu da PRD’ye şöyle ekleyebilirsin:

The Task Manager can ask clarification questions, but it should not ask more than 2 questions per request.
