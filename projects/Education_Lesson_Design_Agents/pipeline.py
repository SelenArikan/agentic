import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List


@dataclass
class Task:
    id: str
    title: str
    owner: str
    status: str
    details: Dict[str, str]


class ProgramCoordinatorAgent:
    def run(self, brief: Dict[str, str]) -> Dict[str, str]:
        return {
            "goal": f"{brief['topic']} konusunda 45 dakikalik ders tasarimi",
            "grade_level": brief["grade_level"],
            "constraints": "Tek ders, etkilesimli etkinlik, olculebilir cikti",
            "success_metric": "Ders sonu mini quizde en az %70 dogru",
        }


class CurriculumDesignerAgent:
    def run(self, plan: Dict[str, str]) -> List[Task]:
        return [
            Task(
                id="EDU-001",
                title="Ogrenme kazanimi yaz",
                owner="curriculum_designer",
                status="done",
                details={"learning_outcome": "Ogrenci fotosentez surecini 3 adimda aciklar."},
            ),
            Task(
                id="EDU-002",
                title="Ders akis plani olustur",
                owner="curriculum_designer",
                status="done",
                details={"lesson_flow": "10 dk giris, 20 dk etkinlik, 10 dk uygulama, 5 dk degerlendirme"},
            ),
        ]


class ActivityPlannerAgent:
    def run(self, tasks: List[Task]) -> Task:
        return Task(
            id="EDU-003",
            title="Sinif ici etkinlik tasarla",
            owner="activity_planner",
            status="done",
            details={
                "activity": "Yaprak modeli uzerinde isik, su ve CO2 etkisini kucuk gruplarla canlandirma",
                "material": "Kagit yaprak kartlari, renkli kalem, cikis karti",
            },
        )


class AssessmentAgent:
    def run(self, tasks: List[Task]) -> Task:
        return Task(
            id="EDU-004",
            title="Olcme degerlendirme hazirla",
            owner="assessment_agent",
            status="done",
            details={
                "quiz": "5 soruluk cikis quizi",
                "rubric": "Bilgi dogrulugu %50, aciklama netligi %30, kavram baglantisi %20",
            },
        )


class QualityReviewerAgent:
    def run(self, all_tasks: List[Task], success_metric: str) -> Dict[str, str]:
        has_activity = any(t.id == "EDU-003" for t in all_tasks)
        has_assessment = any(t.id == "EDU-004" for t in all_tasks)
        status = "PASS" if has_activity and has_assessment else "FAIL"
        return {
            "status": status,
        "review_note": "Plan sinif ici etkinlik ve olcme adimini iceriyor.",
            "target_metric": success_metric,
        }


def run_pipeline() -> None:
    brief = {
        "topic": "Fotosentez",
        "grade_level": "7. sinif",
        "duration": "45 dakika",
    }

    coordinator = ProgramCoordinatorAgent()
    designer = CurriculumDesignerAgent()
    activity = ActivityPlannerAgent()
    assessment = AssessmentAgent()
    reviewer = QualityReviewerAgent()

    output_dir = Path("projects/Education_Lesson_Design_Agents/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    plan = coordinator.run(brief)
    tasks = designer.run(plan)
    tasks.append(activity.run(tasks))
    tasks.append(assessment.run(tasks))
    qa_result = reviewer.run(tasks, plan["success_metric"])

    report = {
        "brief": brief,
        "program_plan": plan,
        "tasks": [asdict(t) for t in tasks],
        "quality_review": qa_result,
    }

    (output_dir / "pipeline_output.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "[Coordinator] hedef ve basari metrigi tanimlandi",
        "[CurriculumDesigner] kazanım ve ders akis plani olusturuldu",
        "[ActivityPlanner] etkinlik adimi eklendi",
        "[AssessmentAgent] quiz ve rubrik eklendi",
        f"[QualityReviewer] sonuc: {qa_result['status']}",
    ]
    (output_dir / "pipeline_log.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run_pipeline()
