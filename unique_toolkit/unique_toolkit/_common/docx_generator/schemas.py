from typing import Optional

from docx.document import Document as DocumentObject
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docxtpl import DocxTemplate
from pydantic import BaseModel


class HeadingField(BaseModel):
    text: str
    level: int = 4
    alignment: WD_PARAGRAPH_ALIGNMENT = WD_PARAGRAPH_ALIGNMENT.LEFT

    def add(self, doc: DocumentObject):
        p = doc.add_heading(self.text, level=self.level)
        p.alignment = self.alignment
        return p

    def __str__(self):
        return f"HeadingField(text={self.text}, level={self.level}, alignment={self.alignment})"


class ParagraphField(BaseModel):
    text: str
    style: Optional[str] = None
    alignment: WD_PARAGRAPH_ALIGNMENT = WD_PARAGRAPH_ALIGNMENT.LEFT

    def add(self, doc: DocumentObject):
        p = doc.add_paragraph(self.text, style=self.style)
        p.alignment = self.alignment
        return p

    def __str__(self):
        return f"ParagraphField(text={self.text}, style={self.style}, alignment={self.alignment})"


class RunField(BaseModel):
    text: str
    italic: Optional[bool] = False
    bold: Optional[bool] = False
    alignment: WD_PARAGRAPH_ALIGNMENT = WD_PARAGRAPH_ALIGNMENT.LEFT

    def __str__(self):
        return f"RunField(text={self.text}, italic={self.italic}, alignment={self.alignment})"


class RunsField(BaseModel):
    runs: list[RunField]
    style: Optional[str] = None
    alignment: WD_PARAGRAPH_ALIGNMENT = WD_PARAGRAPH_ALIGNMENT.LEFT

    def add(self, doc: DocumentObject):
        if not self.runs:
            return None
        p = doc.add_paragraph(style=self.style)
        for run in self.runs:
            r = p.add_run(run.text)
            if run.italic:
                r.italic = True
            if run.bold:
                r.bold = True
        return p

    def __str__(self):
        return f"RunsField(runs={self.runs}, style={self.style}, alignment={self.alignment})"


class ContentField(BaseModel):
    contents: list[HeadingField | ParagraphField | RunsField]

    def add(self, doc: DocxTemplate):
        sd = doc.new_subdoc()
        for content in self.contents:
            # if isinstance(content, ImageField):
            #     content.download_image(self.download_path)
            #     content.add(sd) # type: ignore
            # else:
            content.add(sd)  # type: ignore
        return sd

    def __str__(self):
        return f"ContentField(contents={self.contents})"
