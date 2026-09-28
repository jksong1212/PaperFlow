import os

import pymupdf

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from test_metadata import JATS_ABSTRACT

from paperflow import db
from paperflow.app import MainWindow, ScanWorker


def test_ai_prompt_before_paper_selection(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "paperflow.db")
    messages = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: messages.append(args[2]))
    _app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.ai_question.setPlainText("What are the findings?")

    assert window.make_ai_prompt() == ""
    assert messages == ["Select a paper first."]
    window.close()


def test_saved_notes_are_used_by_ai_and_references_keep_style_numbering(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "paperflow.db")
    db.upsert_paper(
        {
            "filepath": str(tmp_path / "example.pdf"),
            "filename": "example.pdf",
            "title": "Example title",
            "authors": "Jane Doe",
            "year": "2024",
        }
    )
    _app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.select_row(0, 1)
    window.notes.setPlainText("My saved observation")
    window.save_detail()
    window.ctx_pdf.setChecked(False)
    window.ctx_notes.setChecked(True)
    window.ai_question.setPlainText("What are the findings?")
    assert "My saved observation" in window.make_ai_prompt()

    window.table.item(0, 0).setCheckState(Qt.Checked)
    window.style.setCurrentText("Vancouver")
    window.generate_refs()
    assert window.refs.toPlainText().startswith("1. ")
    assert not window.refs.toPlainText().startswith("1. 1.")
    window.close()


def test_scan_worker_reports_failure_and_completes(tmp_path, monkeypatch):
    (tmp_path / "example.pdf").touch()

    def fail(_path):
        raise RuntimeError("Cannot read PDF")

    monkeypatch.setattr("paperflow.app.extract_pdf", fail)
    worker = ScanWorker(tmp_path)
    errors = []
    completed = []
    worker.error.connect(errors.append)
    worker.done.connect(lambda: completed.append(True))
    worker.run()

    assert errors == ["Cannot read PDF"]
    assert completed == [True]


def test_scan_worker_indexes_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "paperflow.db")
    pdf_path = tmp_path / "example.pdf"
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "A sample research paper")
    document.save(pdf_path)
    document.close()

    worker = ScanWorker(tmp_path)
    errors = []
    completed = []
    worker.error.connect(errors.append)
    worker.done.connect(lambda: completed.append(True))
    worker.run()

    assert errors == []
    assert completed == [True]
    papers = db.list_papers()
    assert len(papers) == 1
    assert papers[0]["filename"] == "example.pdf"


def test_existing_jats_abstract_is_readable_in_gui_and_ai(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "paperflow.db")
    db.upsert_paper(
        {
            "filepath": str(tmp_path / "existing.pdf"),
            "filename": "existing.pdf",
            "title": "Existing paper",
            "abstract": JATS_ABSTRACT,
        }
    )
    _app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.select_row(0, 1)
    assert window.abstract.toPlainText().startswith("Background\n\nEstimation")
    assert "<jats:" not in window.abstract.toPlainText()

    window.ai_question.setPlainText("What is the conclusion?")
    window.ctx_pdf.setChecked(False)
    prompt = window.make_ai_prompt()
    assert "Conclusions\n\nCarotid tonometry" in prompt
    assert "<jats:" not in prompt
    window.close()
