"""
Generate updated Assignment 4 HTML report with embedded charts and correct repo link.
Then convert to PDF using weasyprint or pdfkit.
"""

import os
import sys
import base64

# ── Paths ─────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR  = os.path.dirname(SCRIPT_DIR)
VISUALS_DIR  = os.path.join(PROJECT_DIR, "outputs", "assignment4_visuals")
OUTPUT_HTML  = os.path.join(PROJECT_DIR, "assignment4_report.html")
OUTPUT_PDF   = os.path.join(PROJECT_DIR, "assignment4_report.pdf")
REPO_URL     = "https://github.com/SelenArikan/agentic"


def img_b64(filename):
    """Return a base64-encoded data URI for a PNG."""
    path = os.path.join(VISUALS_DIR, filename)
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{data}"


def build_html():
    fig1 = img_b64("fig1_aggregate_comparison.png")
    fig2 = img_b64("fig2_per_test_scores.png")
    fig3 = img_b64("fig3_latency.png")
    fig4 = img_b64("fig4_requirement_score.png")
    fig5 = img_b64("fig5_pipeline_diagram.png")
    fig6 = img_b64("fig6_radar.png")

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Assignment 4 Report</title>
<style>
@page {{ size: A4; margin: 14mm 12mm; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  color: #161616; line-height: 1.36; font-size: 9.6pt;
}}
h1 {{ font-size: 18pt; margin: 0 0 8px; }}
h2 {{
  font-size: 13pt; margin: 14px 0 5px; padding-top: 4px;
  border-top: 1.5px solid #ccc;
}}
h3 {{ font-size: 10.5pt; margin: 9px 0 4px; }}
p  {{ margin: 3px 0; }}
ul {{ margin: 3px 0 6px 16px; padding: 0; }}
li {{ margin: 2px 0; }}
table {{
  width: 100%; border-collapse: collapse; margin: 6px 0 10px;
  font-size: 7.5pt; page-break-inside: avoid;
}}
th, td {{
  border: 1px solid #ccc; padding: 3px 4px; vertical-align: top;
}}
th {{ background: #eef3f1; font-weight: 700; }}
pre {{
  background: #f6f6f6; border: 1px solid #ddd; padding: 7px;
  white-space: pre-wrap; overflow-wrap: anywhere; font-size: 7.6pt;
}}
code {{ font-family: Menlo, Consolas, monospace; font-size: .91em; }}
hr {{ border: 0; border-top: 1px solid #ddd; margin: 8px 0; }}
.fig {{
  text-align: center; margin: 10px 0 14px;
  page-break-inside: avoid;
}}
.fig img {{
  max-width: 100%; height: auto;
  border: 1px solid #e0e0e0; border-radius: 4px;
}}
.fig-caption {{
  font-size: 8pt; color: #555; margin-top: 4px; font-style: italic;
}}
.repo-link {{
  background: #f0f7ff; border: 1px solid #b0d0f0; border-radius: 4px;
  padding: 6px 10px; font-size: 8.5pt; display: inline-block; margin: 4px 0;
}}
</style>
</head>
<body>

<h1>Assignment 4: Improving Requirement Reliability in a Multi-Agent Social Media System</h1>

<h2>Objective</h2>
<p>This assignment improves the multi-agent social media system developed and evaluated in the earlier assignments. Assignment 3 showed that a multi-agent pipeline is easier to inspect than a single-agent pipeline, but orchestration alone does not guarantee that user requirements are preserved. If the system extracts the wrong topic or loses a visual constraint, later agents can complete the workflow and still produce an unsuitable post.</p>
<p>The research question for this assignment is:</p>
<p><strong>Can a structured request-verification stage and a requirement-aware QA loop improve the reliability of a multi-agent social media generation pipeline?</strong></p>
<p>Code repository link: <span class="repo-link">&#128279; <a href="{REPO_URL}">{REPO_URL}</a></span></p>

<hr>

<h2>Part 1 – Baseline System</h2>

<h3>Problem Definition</h3>
<p>The system automates social media post preparation. A user provides a prompt such as "Make a post about Pilates" or a more detailed product request. The pipeline should:</p>
<ul>
  <li>Infer the post topic and language.</li>
  <li>Decide whether writing, visual generation, QA, and upload are needed.</li>
  <li>Produce a caption.</li>
  <li>Produce a visual brief and image file when media is requested.</li>
  <li>Validate the output.</li>
  <li>Simulate a local browser upload when publishing is requested.</li>
</ul>

<h3>Baseline Agent Roles</h3>
<table><thead><tr><th>Agent</th><th>Baseline Role</th></tr></thead><tbody>
<tr><td>Task Manager</td><td>Creates route, validates steps, retries failed agents</td></tr>
<tr><td>Trend Researcher</td><td>Adds keywords and hashtags for short or trend-based prompts</td></tr>
<tr><td>Content Writer</td><td>Writes caption and rough media prompt</td></tr>
<tr><td>Visual Prompt Engineer</td><td>Converts rough media prompt into structured photo prompt</td></tr>
<tr><td>Media Creator</td><td>Creates an image with provider or local placeholder path</td></tr>
<tr><td>QA Agent</td><td>Checks caption/media completeness and safety</td></tr>
<tr><td>Browser Operator</td><td>Simulates upload to local demo page</td></tr>
</tbody></table>

<h3>Baseline Workflow vs Improved Pipeline</h3>
<div class="fig">
  <img src="{fig5}" alt="Figure 5 — Pipeline Diagram">
  <div class="fig-caption">Figure 5 — System Architecture: Baseline Pipeline (left) vs Improved Pipeline with new verification stages (right)</div>
</div>

<h3>Current Limitations of the Baseline</h3>
<ul>
  <li>A prompt containing an ambiguous reference can produce a generic topic such as <code>this and it</code>.</li>
  <li>A content pipeline can approve a post although a specific image instruction is only partially represented.</li>
  <li>Completion success can hide upstream mistakes because every downstream agent works from the initial topic.</li>
  <li>More agents produce more external model/API calls, increasing timeout and provider-failure exposure.</li>
</ul>

<hr>

<h2>Part 2 – Identify Weaknesses</h2>

<h3>Weakness 1: Low-Confidence Topic Extraction</h3>
<p>The baseline Task Manager tries to infer a topic from prompt text. For vague prompts such as "Make a post about this and share it," the baseline may extract the literal phrase <code>this and it</code> as a topic. The remaining agents then receive that topic and produce a generic caption and generic image brief.</p>
<p><strong>Why it occurs:</strong></p>
<ul>
  <li>The pipeline treats any non-empty topic-like phrase as usable unless it matches a small blocked set.</li>
  <li>The baseline does not maintain an explicit confidence score for topic extraction.</li>
  <li>QA sees a caption and media file, so it can approve the run even though the topic is semantically weak.</li>
</ul>
<p><strong>Why it matters:</strong> The system can publish a meaningless post. Later agents cannot recover if the initial topic is wrong.</p>

<h3>Weakness 2: User Visual Requirements Are Not Explicit Contracts</h3>
<p>Some prompts contain visual constraints such as "Outdoor mat Pilates in a park, not an indoor studio" or "A close-up of a woman's ear with three silver earrings." The baseline QA Agent mainly checks safety and media existence, not every visual condition as an explicit checklist.</p>
<p><strong>Why it occurs:</strong> Visual constraints are carried in free-form text fields. A media prompt can mention the topic <code>silver earrings</code> while missing details such as count or close-up framing.</p>
<p><strong>Why it matters:</strong> A generated post can be plausible but not satisfy the user request. Product posts are especially sensitive to count, material, setting, and composition constraints.</p>

<h3>Weakness 3: Completion Does Not Mean Reliability</h3>
<p>Multi-agent orchestration adds logs, validation calls, and provider calls. In real API mode, Assignment 3 exposed timeouts and provider connection errors. Extra agent calls increase the surface area for latency and service failures.</p>
<p><strong>Why it occurs:</strong> Specialized agents create more handoffs than a single combined call. Text and image providers can fail independently.</p>
<p><strong>Why it matters:</strong> The system needs verification and fallback behavior, not only more agents. Some steps should stop early when confidence is low.</p>

<hr>

<h2>Part 3 – System Improvements</h2>

<p>Three connected improvements were implemented, designed to improve requirement quality before adding more generation cost.</p>

<h3>Improvement 1: Structured Request Brief Verifier</h3>
<p>Added <code>RequestBriefVerifierAgent</code> in <code>agents/requirement_brief.py</code>. Before the improved Task Manager executes the normal route, this verifier creates a structured brief:</p>
<pre><code>{{
  "topic": "silver earrings",
  "language": "en",
  "media_required": true,
  "visual_constraints": [
    "close-up composition",
    "earrings visible on a woman's ear",
    "three earrings",
    "silver earrings"
  ],
  "avoid_constraints": [],
  "confidence": 0.92
}}</code></pre>

<h3>Improvement 2: Confidence Gate and Human Approval State</h3>
<p>The improved pipeline uses <code>ImprovedTaskManagerAgent</code> in <code>agents/improved_task_manager.py</code>. If the request brief confidence is low and the topic is ambiguous, the improved system does not proceed blindly — it asks for topic clarification. This is a controlled human-in-the-loop change:</p>
<ul>
  <li>High-confidence prompts continue automatically.</li>
  <li>Ambiguous prompts ask for clarification.</li>
  <li>Repaired or low-confidence publish operations can require human approval.</li>
</ul>

<h3>Improvement 3: Requirement-Aware QA and Feedback Repair</h3>
<p>Added <code>RequirementAwareQAAgent</code> in <code>agents/requirement_qa.py</code>. It runs after normal QA approval and checks the structured request brief. If this QA rejects a visual requirement mismatch, the improved Task Manager routes the feedback back into the visual branch for repair.</p>

<h3>Implementation Footprint</h3>
<table><thead><tr><th>File</th><th>Purpose</th></tr></thead><tbody>
<tr><td><code>models.py</code></td><td>Adds request brief, confidence, and human approval state</td></tr>
<tr><td><code>agents/requirement_brief.py</code></td><td>Structured request brief and constraint injection</td></tr>
<tr><td><code>agents/requirement_qa.py</code></td><td>Requirement-aware verification</td></tr>
<tr><td><code>agents/improved_task_manager.py</code></td><td>Improved route, feedback repair, approval gate</td></tr>
<tr><td><code>tools/run_assignment4_experiment.py</code></td><td>Original vs improved experiment runner</td></tr>
<tr><td><code>tests/test_assignment4_improvements.py</code></td><td>Focused improvement tests</td></tr>
</tbody></table>

<hr>

<h2>Part 4 – Experimental Comparison</h2>

<h3>Experiment Design</h3>
<p>The experiment compares <code>original_multi_agent</code> (existing baseline <code>TaskManagerAgent</code>) with <code>improved_multi_agent</code> (<code>ImprovedTaskManagerAgent</code>). Both systems use the same seven prompts in deterministic local mode (<code>--provider mock --image-provider pillow</code>).</p>

<h3>Test Cases</h3>
<table><thead><tr><th>Case</th><th>Weakness Target</th></tr></thead><tbody>
<tr><td>A4-T1 Short Pilates</td><td>No-regression clear prompt</td></tr>
<tr><td>A4-T2 Ambiguous <code>this</code></td><td>Confidence gate and clarification</td></tr>
<tr><td>A4-T3 Outdoor mat Pilates</td><td>Preserve environment and mat/studio constraint</td></tr>
<tr><td>A4-T4 Jewelry constraints</td><td>Preserve close-up, count, and material</td></tr>
<tr><td>A4-T5 Exact caption</td><td>Preserve mixed caption + image intent</td></tr>
<tr><td>A4-T6 Turkish outdoor</td><td>Preserve Turkish topic and visual direction</td></tr>
<tr><td>A4-T7 Caption only</td><td>Preserve efficient text-only route</td></tr>
</tbody></table>

<h3>Aggregate Results</h3>
<table><thead><tr><th>System</th><th>Mean Overall</th><th>Correctness</th><th>Requirement</th><th>Completeness</th><th>Latency ms</th><th>Logs</th><th>LLM Step Proxy</th><th>Human Approvals</th><th>Failure Rate</th></tr></thead><tbody>
<tr><td>Original Multi-Agent</td><td>0.85</td><td>0.85</td><td>0.95</td><td>0.86</td><td>15.02</td><td>13.71</td><td>3.00</td><td>0.00</td><td>0.14</td></tr>
<tr><td>Improved Multi-Agent</td><td>1.00</td><td>1.00</td><td>1.00</td><td>1.00</td><td>10.42</td><td>14.71</td><td>2.43</td><td>0.14</td><td>0.00</td></tr>
</tbody></table>

<div class="fig">
  <img src="{fig1}" alt="Figure 1 — Aggregate Comparison">
  <div class="fig-caption">Figure 1 — Aggregate metric comparison across all test cases. The improved system achieves perfect scores on all dimensions and eliminates the failure rate.</div>
</div>

<div class="fig">
  <img src="{fig2}" alt="Figure 2 — Per-Test Scores">
  <div class="fig-caption">Figure 2 — Per-test overall score. The ambiguous prompt T2 (red zone) exposes the original system's 0.00 score, while the improved system scores 1.00 by requesting clarification instead of publishing.</div>
</div>

<div class="fig">
  <img src="{fig4}" alt="Figure 4 — Requirement Score">
  <div class="fig-caption">Figure 4 — Requirement score per test case. The jewelry constraint test (T4) shows a +0.33 gain from structured visual constraint injection.</div>
</div>

<div class="fig">
  <img src="{fig3}" alt="Figure 3 — Latency">
  <div class="fig-caption">Figure 3 — Latency per test case (ms). The improved system achieves lower mean latency (10.4 ms vs 15.0 ms) by stopping early on low-confidence prompts instead of running the full pipeline.</div>
</div>

<div class="fig">
  <img src="{fig6}" alt="Figure 6 — Radar Chart">
  <div class="fig-caption">Figure 6 — Performance radar chart. The improved system (green) fully covers the original (blue) on every dimension.</div>
</div>

<h3>Key Per-Test Results</h3>
<table><thead><tr><th>Case</th><th>Original Result</th><th>Improved Result</th><th>Interpretation</th></tr></thead><tbody>
<tr><td>A4-T2 Ambiguous <code>this</code></td><td>Published with topic <code>this and it</code>; score 0.00</td><td>Asked for topic clarification; score 1.00</td><td>Confidence gate prevents meaningless publish</td></tr>
<tr><td>A4-T4 Jewelry constraints</td><td>Requirement score 0.67</td><td>Requirement score 1.00</td><td>Structured constraints improve image brief coverage</td></tr>
<tr><td>A4-T1, T3, T5, T6, T7</td><td>Complete and approved</td><td>Complete and approved</td><td>Improvements did not break normal routes</td></tr>
</tbody></table>

<h3>Representative Logs</h3>
<p>Original ambiguous flow:</p>
<pre><code>topic: this and it
qa_status: approved
browser_status: success</code></pre>
<p>Improved ambiguous flow:</p>
<pre><code>request_brief_verifier low_confidence
task_manager clarification_needed
question: What specific topic or product should the post cover?</code></pre>
<p>Improved constraint-aware flow:</p>
<pre><code>request_brief_verifier constraints_applied
visual_prompt_engineer validated
requirement_qa approved</code></pre>

<hr>

<h2>Part 5 – Discussion</h2>

<h3>Which Improvements Worked Well?</h3>
<p>The structured request brief worked well. It created a clear topic/constraint boundary before generation. The largest gain appeared in the ambiguous prompt: the original system completed a meaningless post, while the improved system treated the same input as insufficient information.</p>
<p>Constraint injection and requirement-aware QA also improved product visual reliability. In the jewelry case, the original result was approved but received only <code>0.67</code> visual requirement coverage. The improved result preserved the close-up, material, and count expectations and reached <code>1.00</code>.</p>

<h3>Which Improvements Did Not Add Visible Benefit in Every Case?</h3>
<p>The improved system adds extra logs and verifier state even for easy prompts. For T1, T3, T5, T6, and T7 both systems already produced correct deterministic outputs. The extra verification did not change the final score there.</p>
<p>The requirement repair feedback loop did not trigger in the deterministic aggregate run. This is not a bug: the pre-generation request brief constraint injection prevented the tested mismatches before QA. The repair path is still needed for real provider outputs, where a text or image model may ignore instructions after prompt generation.</p>

<h3>Unexpected Outcomes</h3>
<p>Mean latency became lower for the improved system in the deterministic run. This occurs because the improved ambiguous run stops after three logs, while the original baseline continues through writing, media generation, QA, and browser upload. The result supports early stopping as an efficiency strategy for low-confidence requests.</p>

<h3>New Problems or Trade-Offs</h3>
<ul>
  <li>More state fields must remain consistent.</li>
  <li>The verifier rules need maintenance as new domains and languages are added.</li>
  <li>Human approval gates can slow publishing if triggered too often.</li>
  <li>Requirement scoring currently checks prompt coverage, not the final aesthetics of a generated image.</li>
</ul>
<p>The improved design is still better for this workflow because it makes uncertain decisions explicit rather than hiding them behind a completed pipeline.</p>

<hr>

<h2>Part 6 – Reflection: Human + AI Collaboration</h2>
<p>Humans should not manually approve every low-risk draft. AI agents can independently route work, draft captions, generate image prompts, validate file existence, and prepare local previews when confidence is high and requirements are clear.</p>
<p>Human oversight is appropriate when:</p>
<ul>
  <li>Topic confidence is low.</li>
  <li>A post is being published to a real external account.</li>
  <li>Brand, legal, safety, or sensitive product claims are involved.</li>
  <li>QA had to repair a requirement mismatch.</li>
  <li>Generated media must accurately represent a product or person.</li>
</ul>
<p>The practical design principle is selective oversight. Humans should remain in the loop for high-impact or low-confidence decisions, while agents handle repetitive drafting and validation steps. A reliable agentic system is not one that runs autonomously at all costs. It is one that knows when autonomy is justified and when uncertainty should be exposed to a human.</p>

<hr>

<h2>Responsible Use of AI</h2>
<p>AI tools were used to help implement, test, and document the system. The experiment design, metric definitions, interpretation of results, and limitations remain the responsibility of the authors. The deterministic experiment is intentionally separated from real provider behavior so that architectural improvements are not confused with temporary API availability.</p>

</body>
</html>"""
    return html


def main():
    print("\nBuilding updated HTML report...")
    html = build_html()
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ HTML saved: {OUTPUT_HTML}")

    # ── Try weasyprint for PDF ─────────────────────────────────────
    try:
        import weasyprint
        print("  Converting to PDF with weasyprint...")
        weasyprint.HTML(filename=OUTPUT_HTML).write_pdf(OUTPUT_PDF)
        print(f"  ✓ PDF saved: {OUTPUT_PDF}")
    except ImportError:
        # ── Try pdfkit (wkhtmltopdf) ─────────────────────────────
        try:
            import pdfkit
            print("  Converting to PDF with pdfkit...")
            options = {
                "page-size": "A4",
                "margin-top": "14mm",
                "margin-right": "12mm",
                "margin-bottom": "14mm",
                "margin-left": "12mm",
                "encoding": "UTF-8",
                "enable-local-file-access": "",
                "quiet": "",
            }
            pdfkit.from_file(OUTPUT_HTML, OUTPUT_PDF, options=options)
            print(f"  ✓ PDF saved: {OUTPUT_PDF}")
        except Exception as e2:
            print(f"  ⚠ PDF generation skipped ({e2})")
            print("    Install weasyprint: pip install weasyprint")
            print(f"    HTML report is ready at: {OUTPUT_HTML}")

    print("\n✅ Report generation complete!")


if __name__ == "__main__":
    main()
