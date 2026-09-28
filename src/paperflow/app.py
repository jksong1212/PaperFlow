import os, sys, subprocess
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
 QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLineEdit,
 QFileDialog,QTableWidget,QTableWidgetItem,QSplitter,QLabel,QTextEdit,QTabWidget,
 QComboBox,QMessageBox,QHeaderView,QProgressBar,QCheckBox
)
from .db import list_papers, upsert_paper, update_text
from .pdf import extract_pdf
from .metadata import crossref_by_doi
from .citation import format_references, available_styles
from .ai import build_prompt, open_ai

class ScanWorker(QThread):
    progress = Signal(int,int,str)
    done = Signal()
    def __init__(self, folder):
        super().__init__(); self.folder=folder
    def run(self):
        paths=list(Path(self.folder).rglob("*.pdf"))
        for i,p in enumerate(paths,1):
            data=extract_pdf(p)
            if data.get("doi"):
                remote=crossref_by_doi(data["doi"])
                for k,v in remote.items():
                    if v: data[k]=v
            upsert_paper(data)
            self.progress.emit(i,len(paths),p.name)
        self.done.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PaperFlow v0.1")
        self.resize(1400,850)
        self.rows=[]
        self.current_id=None
        self._build()
        self.reload()

    def _build(self):
        root=QWidget(); self.setCentralWidget(root)
        outer=QVBoxLayout(root)
        top=QHBoxLayout()
        self.folder_btn=QPushButton("📁 Index paper folder")
        self.search=QLineEdit(); self.search.setPlaceholderText("Search title, author, journal, DOI…")
        self.search.textChanged.connect(lambda _: self.reload())
        self.folder_btn.clicked.connect(self.choose_folder)
        top.addWidget(self.folder_btn); top.addWidget(self.search,1)
        outer.addLayout(top)

        split=QSplitter()
        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels(["✓","Title","Authors","Year","Journal","DOI","File"])
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellClicked.connect(self.select_row)
        split.addWidget(self.table)

        detail=QWidget(); dl=QVBoxLayout(detail)
        self.title=QLabel("Select a paper")
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size:18px;font-weight:600;")
        self.meta=QLabel(""); self.meta.setWordWrap(True)
        dl.addWidget(self.title); dl.addWidget(self.meta)

        tabs=QTabWidget()
        self.abstract=QTextEdit(); self.abstract.setReadOnly(True)
        self.summary=QTextEdit(); self.summary.setPlaceholderText("Saved summary. AI generation will be added next.")
        self.notes=QTextEdit(); self.notes.setPlaceholderText("Why did you save this paper? Key finding, quote/page, usage…")
        tabs.addTab(self.abstract,"Abstract")
        tabs.addTab(self.summary,"Summary")
        tabs.addTab(self.notes,"My Notes")

        ai_tab=QWidget(); ail=QVBoxLayout(ai_tab)
        self.ai_question=QTextEdit()
        self.ai_question.setPlaceholderText("Ask about this paper, e.g. What are the main findings and limitations?")
        self.ai_question.setMaximumHeight(100)
        ail.addWidget(QLabel("Question")); ail.addWidget(self.ai_question)

        ctx=QHBoxLayout()
        self.ctx_meta=QCheckBox("Metadata"); self.ctx_meta.setChecked(True)
        self.ctx_abs=QCheckBox("Abstract"); self.ctx_abs.setChecked(True)
        self.ctx_pdf=QCheckBox("Relevant PDF text"); self.ctx_pdf.setChecked(True)
        self.ctx_notes=QCheckBox("My notes")
        for w in (self.ctx_meta,self.ctx_abs,self.ctx_pdf,self.ctx_notes): ctx.addWidget(w)
        ctx.addStretch(); ail.addLayout(ctx)

        air=QHBoxLayout()
        self.ai_provider=QComboBox()
        self.ai_provider.addItems(["ChatGPT","Claude","Gemini","Copy prompt only"])
        preview=QPushButton("Preview prompt"); preview.clicked.connect(self.preview_ai_prompt)
        ask=QPushButton("Ask AI →"); ask.clicked.connect(self.ask_ai)
        air.addWidget(QLabel("Open with:")); air.addWidget(self.ai_provider)
        air.addWidget(preview); air.addWidget(ask); air.addStretch()
        ail.addLayout(air)

        self.ai_preview=QTextEdit(); self.ai_preview.setReadOnly(True)
        self.ai_preview.setPlaceholderText("Generated prompt preview appears here.")
        ail.addWidget(self.ai_preview,1)
        tabs.addTab(ai_tab,"Ask AI")
        dl.addWidget(tabs,1)

        actions=QHBoxLayout()
        save=QPushButton("Save summary/notes"); save.clicked.connect(self.save_detail)
        openpdf=QPushButton("Open PDF"); openpdf.clicked.connect(self.open_pdf)
        actions.addWidget(save); actions.addWidget(openpdf); actions.addStretch()
        dl.addLayout(actions)

        refrow=QHBoxLayout()
        self.style=QComboBox(); self.style.addItems(available_styles())
        gen=QPushButton("Generate checked references"); gen.clicked.connect(self.generate_refs)
        refrow.addWidget(QLabel("Reference style:")); refrow.addWidget(self.style); refrow.addWidget(gen); refrow.addStretch()
        dl.addLayout(refrow)
        self.refs=QTextEdit(); self.refs.setPlaceholderText("Checked-paper references appear here.")
        dl.addWidget(self.refs,1)
        copy=QPushButton("Copy references"); copy.clicked.connect(lambda: QApplication.clipboard().setText(self.refs.toPlainText()))
        dl.addWidget(copy)

        split.addWidget(detail); split.setSizes([820,580])
        outer.addWidget(split,1)
        self.progress=QProgressBar(); self.progress.hide(); outer.addWidget(self.progress)

    def reload(self):
        checked=set()
        for r in range(self.table.rowCount()):
            it=self.table.item(r,0)
            if it and it.checkState()==Qt.Checked:
                checked.add(it.data(Qt.UserRole))
        self.rows=list(list_papers(self.search.text().strip()))
        self.table.setRowCount(len(self.rows))
        for r,p in enumerate(self.rows):
            c=QTableWidgetItem(); c.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable|Qt.ItemIsSelectable)
            c.setCheckState(Qt.Checked if p["id"] in checked else Qt.Unchecked); c.setData(Qt.UserRole,p["id"])
            self.table.setItem(r,0,c)
            vals=[p["title"],p["authors"],p["year"],p["journal"],p["doi"],p["filename"]]
            for j,v in enumerate(vals,1): self.table.setItem(r,j,QTableWidgetItem(v or ""))

    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,"Choose paper folder")
        if not folder:return
        self.folder_btn.setEnabled(False); self.progress.show(); self.progress.setValue(0)
        self.worker=ScanWorker(folder)
        self.worker.progress.connect(self.scan_progress)
        self.worker.done.connect(self.scan_done)
        self.worker.start()

    def scan_progress(self,i,n,name):
        self.progress.setMaximum(max(n,1)); self.progress.setValue(i)
        self.progress.setFormat(f"{i}/{n}  {name}")

    def scan_done(self):
        self.folder_btn.setEnabled(True); self.progress.hide(); self.reload()
        QMessageBox.information(self,"PaperFlow","Folder indexing finished.")

    def select_row(self,r,c):
        p=self.rows[r]; self.current_paper=p; self.current_id=p["id"]; self.current_path=p["filepath"]
        self.title.setText(p["title"] or p["filename"])
        self.meta.setText(f'{p["authors"]}\n{p["journal"]} · {p["year"]} · DOI: {p["doi"]}')
        self.abstract.setPlainText(p["abstract"] or "")
        self.summary.setPlainText(p["summary"] or "")
        self.notes.setPlainText(p["notes"] or "")

    def save_detail(self):
        if not self.current_id:return
        update_text(self.current_id,"summary",self.summary.toPlainText())
        update_text(self.current_id,"notes",self.notes.toPlainText())
        self.reload()

    def open_pdf(self):
        if getattr(self,"current_path",None):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_path))

    def make_ai_prompt(self):
        if not self.current_paper:
            QMessageBox.information(self,"PaperFlow","Select a paper first.")
            return ""
        q=self.ai_question.toPlainText().strip()
        if not q:
            QMessageBox.information(self,"PaperFlow","Enter a question first.")
            return ""
        return build_prompt(
            self.current_paper, q,
            metadata=self.ctx_meta.isChecked(),
            abstract=self.ctx_abs.isChecked(),
            pdf=self.ctx_pdf.isChecked(),
            notes=self.ctx_notes.isChecked()
        )

    def preview_ai_prompt(self):
        prompt=self.make_ai_prompt()
        if prompt: self.ai_preview.setPlainText(prompt)

    def ask_ai(self):
        prompt=self.make_ai_prompt()
        if not prompt: return
        self.ai_preview.setPlainText(prompt)
        QApplication.clipboard().setText(prompt)
        provider=self.ai_provider.currentText()
        if provider != "Copy prompt only":
            open_ai(provider)
            QMessageBox.information(
                self,"PaperFlow",
                f"Prompt copied to clipboard. {provider} was opened in your browser.\nPaste the prompt into the chat."
            )
        else:
            QMessageBox.information(self,"PaperFlow","Prompt copied to clipboard.")

    def generate_refs(self):
        ids=[]
        for r in range(self.table.rowCount()):
            it=self.table.item(r,0)
            if it.checkState()==Qt.Checked: ids.append(it.data(Qt.UserRole))
        chosen=[p for p in self.rows if p["id"] in ids]
        try:
            rendered=format_references(chosen,self.style.currentText())
            self.refs.setPlainText("\n\n".join(f"{i}. {ref}" for i,ref in enumerate(rendered,1)))
        except Exception as e:
            QMessageBox.critical(self,"Citation error",f"Could not render CSL references:\n{e}")

def run():
    app=QApplication(sys.argv)
    app.setStyle("Fusion")
    w=MainWindow(); w.show()
    sys.exit(app.exec())
