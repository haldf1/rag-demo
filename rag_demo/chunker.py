"""按标题分节、按段落切块，长段落按句子打包，保留重叠。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .documents import Document

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])\s*")


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    heading: str
    text: str
    char_count: int


def _split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = HEADING_RE.match(line)
        if match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line
            current_lines = []
        elif line:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))
    return sections


def _split_paragraphs(section_text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", section_text) if part.strip()]


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size or not current:
            current = current + sentence
        else:
            pieces.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            current = tail + sentence
    if current:
        pieces.append(current)
    return pieces or [text]


def chunk_documents(
    documents: list[Document], chunk_size: int = 400, overlap: int = 60
) -> list[Chunk]:
    chunks: list[Chunk] = []
    counter = 0
    for document in documents:
        for heading, body in _split_sections(document.text):
            if not body:
                continue
            for paragraph in _split_paragraphs(body):
                prefix = f"{heading}\n" if heading else ""
                if len(paragraph) <= chunk_size:
                    text = prefix + paragraph
                    counter += 1
                    chunks.append(
                        Chunk(
                            chunk_id=f"{document.id}#{counter}",
                            doc_id=document.id,
                            doc_title=document.title,
                            heading=heading.lstrip("#").strip() if heading else "",
                            text=text,
                            char_count=len(text),
                        )
                    )
                else:
                    for piece in _split_long_text(paragraph, chunk_size, overlap):
                        text = prefix + piece
                        counter += 1
                        chunks.append(
                            Chunk(
                                chunk_id=f"{document.id}#{counter}",
                                doc_id=document.id,
                                doc_title=document.title,
                                heading=heading.lstrip("#").strip() if heading else "",
                                text=text,
                                char_count=len(text),
                            )
                        )
    return chunks
