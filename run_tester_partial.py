"""
Belirtilen task ID'leri için sadece Tester ajanını çalıştırır,
mevcut tasks JSON dosyasını okur, kod dosyalarını context'e ekler,
tester sonuçlarını comments'e yazar ve dosyayı kaydeder.

Kullanım:
  .venv/bin/python run_tester_partial.py Campus_Inventory_App PROD-CLI-005 PROD-CLI-006
"""
import json
import sys
import time
import os
from pathlib import Path
from core.agent import AIAgent
from core.io_manager import IOManager
from config import BASE_PROJECT_PATH, COMPANY_VAULT_PATH


def clean_json_string(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw.rsplit("\n", 1)[0]
    raw = raw.strip()
    for i, char in enumerate(raw):
        if char in ("[", "{"):
            return raw[i:]
    return raw


def main():
    if len(sys.argv) < 3:
        print("Kullanim: python run_tester_partial.py <proje_adi> <TASK_ID> [TASK_ID2 ...]")
        sys.exit(1)

    project_name = sys.argv[1]
    target_ids = sys.argv[2:]

    project_path = Path(BASE_PROJECT_PATH) / project_name
    tasks_file = project_path / "tasks" / "001_project_tasks.json"
    codes_dir = project_path / "codes"

    # company context yükle
    io = IOManager()
    company_context = ""
    for root, _, files in os.walk(COMPANY_VAULT_PATH):
        for f in files:
            if f.endswith((".txt", ".md")):
                company_context += io.read_file(os.path.join(root, f)) + "\n"

    # görevleri yükle
    tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
    tester = AIAgent("Tester", "agents/tester_prompt.txt")

    pass_count = fail_count = 0

    for task in tasks:
        if task["id"] not in target_ids:
            continue

        # kod dosyasını bul ve içeriğini task context'ine ekle
        code_content = ""
        for code_file in sorted(codes_dir.glob(f"{task['id']}_code.*")):
            code_content = code_file.read_text(encoding="utf-8")
            break

        # developer comment olarak ekle (tester için context)
        if code_content:
            task.setdefault("comments", []).append({
                "author": "developer",
                "content": f"Implementation complete.",
                "code": code_content,
                "assigned_to": "tester"
            })

        print(f"\n[Tester] -> {task['id']} - {task['title']}")
        time.sleep(2)

        test_raw = tester.execute_task(json.dumps(task), company_context)
        try:
            test_comment = json.loads(clean_json_string(test_raw))
        except json.JSONDecodeError:
            test_comment = {
                "author": "tester",
                "content": test_raw,
                "status": "FAIL",
                "assigned_to": "developer"
            }

        task["comments"].append(test_comment)
        status = test_comment.get("status", "FAIL")
        task["assigned_to"] = "closed"

        if status == "PASS":
            pass_count += 1
            print(f"    PASS: {task['id']}")
        else:
            fail_count += 1
            print(f"    FAIL: {task['id']}")

    # güncellenmiş task listesini kaydet
    tasks_file.write_text(json.dumps(tasks, indent=4, ensure_ascii=False), encoding="utf-8")
    total = pass_count + fail_count
    print(f"\n--- Partial Tester Done | PASS: {pass_count} | FAIL: {fail_count} | Total: {total} ---")
    print(f"Kaydedildi: {tasks_file}")


if __name__ == "__main__":
    main()
