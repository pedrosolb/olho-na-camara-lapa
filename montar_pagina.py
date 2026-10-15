#!/usr/bin/env python3
"""Junta index.src.html + data.json em um único index.html (página pronta para publicar)."""
import json
from pathlib import Path

aqui = Path(__file__).parent
dados = json.loads((aqui / "data.json").read_text(encoding="utf-8"))
js = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
fonte = (aqui / "index.src.html").read_text(encoding="utf-8")
html = fonte.replace("/*DATA*/null", js)

(aqui / "index.html").write_text(html, encoding="utf-8")  # fragmento (para o Artifact do Claude)
completo = ("<!doctype html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            + html.replace("<div class=\"wrap\">", "</head>\n<body>\n<div class=\"wrap\">", 1)
            + "\n</body>\n</html>\n")
(aqui / "docs").mkdir(exist_ok=True)
(aqui / "docs" / "index.html").write_text(completo, encoding="utf-8")  # versão completa para GitHub Pages
print("index.html e docs/index.html gerados.")
