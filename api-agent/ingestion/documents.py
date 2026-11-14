"""Carga y fragmenta los documentos de origen con los loaders y splitters de LangChain.

- PDFs originales (fuentes 1, 2 y 3): PyPDFLoader, un Document por página (metadatos `page` y `page_label`).
- Página web de Redalyc (fuente 4): BSHTMLLoader.
- Documentos del proyecto (knowledge/docs/*.md): TextLoader + MarkdownHeaderTextSplitter.
- El blog de Radeco (fuente 5) NO se indexa: no es evidencia.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from langchain_community.document_loaders import BSHTMLLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

logging.getLogger("pypdf").setLevel(logging.ERROR)  # avisos de fuentes tipográficas: ruido

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


@dataclass(frozen=True)
class SourceDoc:
    path: Path
    source_id: int | None      # None = documento propio del proyecto
    doc_kind: str              # source | project_doc
    reliability_level: str     # high | medium | low
    title: str
    loader: str                # pdf | html | markdown
    encoding: str = "utf-8"    # solo para html y markdown


def default_sources(pdf_dir: Path, web_dir: Path, project_docs_dir: Path) -> list[SourceDoc]:
    docs = [
        SourceDoc(pdf_dir / "fao-produccion-organica-cultivos-andinos-ecuador.pdf", 1, "source", "high",
                  "FAO, Producción orgánica de cultivos andinos (Ecuador)", "pdf"),
        SourceDoc(pdf_dir / "fao-guia-de-campo-cultivos-andinos.pdf", 2, "source", "high",
                  "FAO y ANPE-Perú, Guía de campo de los cultivos andinos", "pdf"),
        SourceDoc(pdf_dir / "magap-politica-agropecuaria-ecuatoriana-2015-2025.pdf", 3, "source", "high",
                  "MAGAP, Política agropecuaria ecuatoriana 2015-2025", "pdf"),
        SourceDoc(web_dir / "redalyc-rentabilidad-cultivos-rotacion-tumbaco-2023.html", 4, "source", "high",
                  "Montesdeoca et al. (2023), Rentabilidad de cultivos en rotación, Tumbaco", "html",
                  encoding="iso-8859-1"),  # declarado en el <meta> de la página
    ]
    for md in sorted(project_docs_dir.glob("*.md")):
        docs.append(SourceDoc(md, None, "project_doc", "medium", f"Documento del proyecto: {md.stem}", "markdown"))
    return docs


# --- Cultivos mencionados (metadato para filtrar y para el agente) ---------------------------------

def norm(text: str) -> str:
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()


CROP_TERMS: dict[str, list[str]] = {
    "papa": ["papa", "papas"], "melloco": ["melloco"], "oca": ["oca", "ocas"], "mashua": ["mashua", "mashwa", "isano"],
    "olluco": ["olluco", "ulluco"], "lizas": ["lizas"], "achira": ["achira"], "jicama": ["jicama"],
    "arracacha": ["arracacha", "zanahoria blanca"], "cebada": ["cebada"], "trigo": ["trigo"], "avena": ["avena"],
    "maiz": ["maiz", "choclo"], "quinua": ["quinua", "quinoa"], "amaranto": ["amaranto", "ataco", "kiwicha"],
    "qaniwa": ["qaniwa", "canihua", "kaniwa"], "haba": ["haba", "habas"], "chocho": ["chocho", "tarwi", "lupino"],
    "arveja": ["arveja", "arvejas"], "lenteja": ["lenteja", "lentejas"], "frejol": ["frejol", "frijol"],
    "abono": ["abono verde", "abonos verdes", "vicia"], "pasto": ["pasto", "pastos", "alfalfa", "pradera"],
    "barbecho": ["barbecho"], "tomate": ["tomate"], "brocoli": ["brocoli"], "soya": ["soya", "soja"],
}
_CROP_RX = {cid: re.compile(r"\b(" + "|".join(map(re.escape, terms)) + r")\b") for cid, terms in CROP_TERMS.items()}


def detect_crops(text: str) -> list[str]:
    n = norm(text)
    return [cid for cid, rx in _CROP_RX.items() if rx.search(n)]


# --- Carga y fragmentación ---------------------------------------------------------------------------

_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
_md_headers = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")])


def _base_metadata(src: SourceDoc) -> dict:
    return {"doc_id": src.path.name, "source_id": src.source_id, "doc_kind": src.doc_kind,
            "reliability_level": src.reliability_level, "title": src.title}


def load_and_split(src: SourceDoc) -> list[Document]:
    if not src.path.exists():
        raise FileNotFoundError(f"No existe el documento de origen: {src.path}")
    base = _base_metadata(src)

    if src.loader == "pdf":
        pages = PyPDFLoader(str(src.path)).load()
        for p in pages:
            p.page_content = re.sub(r"[ \t]+", " ", p.page_content)
            p.metadata = {**base, "page": p.metadata.get("page", 0) + 1, "page_label": p.metadata.get("page_label")}
        chunks = _splitter.split_documents(pages)
    elif src.loader == "html":
        doc = BSHTMLLoader(str(src.path), open_encoding=src.encoding, bs_kwargs={"features": "html.parser"}).load()[0]
        doc.page_content = re.sub(r"\n\s*\n+", "\n\n", doc.page_content)
        doc.metadata = {**base}
        chunks = _splitter.split_documents([doc])
    else:  # markdown
        text = TextLoader(str(src.path), encoding=src.encoding).load()[0].page_content
        sections = _md_headers.split_text(text)
        for s in sections:
            s.metadata = {**base, "section": " > ".join(v for k, v in s.metadata.items() if k.startswith("h"))}
        chunks = _splitter.split_documents(sections)

    out = []
    for c in chunks:
        if sum(ch.isalpha() for ch in c.page_content) < 80:
            continue  # fragmentos casi vacíos (portadas, tablas de números)
        c.metadata["crops"] = detect_crops(c.page_content)
        out.append(c)
    return out


def load_all(sources: list[SourceDoc]) -> list[Document]:
    docs: list[Document] = []
    for src in sources:
        docs.extend(load_and_split(src))
    return docs
