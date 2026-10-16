#!/usr/bin/env python3
"""
Coletor de dados da Câmara Municipal da Lapa-PR (SAPL / Interlegis).

Lê a API pública do SAPL (https://sapl.lapa.pr.leg.br/api/) e gera o data.json
no formato que o painel "Câmara da Lapa em Dados" usa. Não precisa de login.

Uso:
    pip install requests
    python coletar_dados.py          # legislatura atual
    python montar_pagina.py          # gera index.html e site/index.html

Dados sob licença Creative Commons BY-SA 4.0 (fonte: Câmara Municipal da Lapa / SAPL).
"""
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")

import requests

BASE = "https://sapl.lapa.pr.leg.br"
HTTP = requests.Session()
HTTP.headers["User-Agent"] = "camara-lapa-em-dados/0.1 (projeto cidadao de transparencia)"
SIGLAS_PROJETO = {"APL", "APLC", "PDL", "PRE", "PELOA", "MOC"}
VOTO = {"Sim": "S", "Não": "N", "Abstenção": "A", "Não Votou": "-"}


def get(path, **params):
    for tentativa in range(4):
        try:
            r = HTTP.get(BASE + path, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if tentativa == 3:
                raise
            time.sleep(2 * (tentativa + 1))


def todos(path, **params):
    """Percorre todas as páginas de um endpoint do SAPL."""
    page, out = 1, []
    while True:
        data = get(path, page_size=100, page=page, **params)
        out.extend(data["results"])
        if not data["pagination"].get("next_page"):
            return out
        page += 1
        time.sleep(0.15)  # gentileza com o servidor da Câmara


def cortar(txt, n):
    txt = re.sub(r"\s+", " ", txt or "").strip()
    if len(txt) <= n:
        return txt
    return re.sub(r"\s\S*$", "", txt[: n - 1]) + "…"


def main():
    hoje = datetime.now(FUSO).date().isoformat()
    legs = todos("/api/parlamentares/legislatura/")
    leg = next((l for l in legs if l["data_inicio"] <= hoje <= l["data_fim"]), max(legs, key=lambda l: l["numero"]))
    ano_ini = int(leg["data_inicio"][:4])
    print(f"Legislatura {leg['numero']}ª")

    # Vereadores (ativos primeiro, depois ordem alfabética)
    partidos, ver = {}, []
    for m in todos("/api/parlamentares/mandato/", legislatura=leg["id"]):
        p = get(f"/api/parlamentares/parlamentar/{m['parlamentar']}/")
        fil = todos("/api/parlamentares/filiacao/", parlamentar=p["id"])
        atual = [f for f in fil if not f.get("data_desfiliacao")] or fil
        sigla = ""
        if atual:
            pid = max(atual, key=lambda f: f["data"])["partido"]
            if pid not in partidos:
                partidos[pid] = get(f"/api/parlamentares/partido/{pid}/")["sigla"]
            sigla = partidos[pid]
        autores = [a["id"] for a in get("/api/base/autor/", object_id=p["id"], content_type=26)["results"]]
        ver.append({"id": p["id"], "nome": p["nome_parlamentar"], "partido": sigla, "ativo": 1 if p.get("ativo") else 0,
                    "votos": m.get("votos_recebidos"), "completo": p.get("nome_completo", ""),
                    "foto": p.get("fotografia") or "", "autores": autores})
    ver.sort(key=lambda v: (-v["ativo"], v["nome"]))
    vid = [v["id"] for v in ver]
    autor_idx = {a: i for i, v in enumerate(ver) for a in v["autores"]}

    def bits(ids):
        return "".join("1" if x in ids else "0" for x in vid)

    # Sessões, presença e justificativas
    sessoes = sorted(todos("/api/sessao/sessaoplenaria/", legislatura=leg["id"]), key=lambda s: s["data_inicio"])
    ids_sessao = {s["id"] for s in sessoes}
    just = defaultdict(set)
    for j in todos("/api/sessao/justificativaausencia/"):
        if j["sessao_plenaria"] in ids_sessao:
            just[j["sessao_plenaria"]].add(j["parlamentar"])
    sess = []
    for s in sessoes:
        pres = {p["parlamentar"] for p in todos("/api/sessao/sessaoplenariapresenca/", sessao_plenaria=s["id"])}
        sess.append([s["id"], s["data_inicio"], s["tipo"], s["numero"], bits(pres), bits(just[s["id"]])])
    print(f"  {len(sess)} sessões")

    # Matérias dos anos da legislatura
    tipos = {t["id"]: t for t in todos("/api/materia/tipomaterialegislativa/")}

    def sig(m):
        return tipos.get(m["tipo"], {}).get("sigla", "?")

    materias = {}
    for ano in range(ano_ini, int(hoje[:4]) + 1):
        for m in todos("/api/materia/materialegislativa/", ano=ano):
            materias[m["id"]] = m
    print(f"  {len(materias)} matérias")

    # Votações nominais (voto a voto)
    votos = defaultdict(dict)
    for v in todos("/api/sessao/votoparlamentar/"):
        votos[v["votacao"]][v["parlamentar"]] = v["voto"]
    itens = {}
    for s in sessoes:
        for o in todos("/api/sessao/ordemdia/", sessao_plenaria=s["id"]):
            itens[("o", o["id"])] = (o, s)
        for e in todos("/api/sessao/expedientemateria/", sessao_plenaria=s["id"]):
            itens[("e", e["id"])] = (e, s)
    nom = []
    for rv in todos("/api/sessao/registrovotacao/"):
        if rv["id"] not in votos:
            continue
        if rv.get("ordem"):
            chave = ("o", rv["ordem"])
        elif rv.get("expediente"):
            chave = ("e", rv["expediente"])
        else:
            continue
        if chave not in itens:
            continue
        item, s = itens[chave]
        m = materias.get(rv["materia"]) or get(f"/api/materia/materialegislativa/{rv['materia']}/")
        vv = votos[rv["id"]]
        nom.append([s["data_inicio"], s["id"], f"{sig(m)} {m['numero']}/{m['ano']}", cortar(m.get("ementa"), 170),
                    item.get("resultado", ""), "".join(VOTO.get(vv[x], ".") if x in vv else "." for x in vid), m["id"]])
    print(f"  {len(nom)} votações nominais")

    # Contagem de proposições por vereador e lista de projetos
    cnt = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    tot = defaultdict(lambda: defaultdict(int))
    proj = []
    for m in materias.values():
        s = sig(m)
        tot[str(m["ano"])][s] += 1
        autores = sorted({autor_idx[a] for a in m.get("autores", []) if a in autor_idx})
        for i in autores:
            cnt[str(i)][str(m["ano"])][s] += 1
        if s in SIGLAS_PROJETO:
            proj.append([m["id"], s, m["numero"], m["ano"], m.get("data_apresentacao") or f"{m['ano']}-01-01",
                         cortar(m.get("ementa"), 160), autores, 1 if m.get("em_tramitacao") else 0])

    usadas = {s for c in cnt.values() for a in c.values() for s in a} | SIGLAS_PROJETO | {"PLO", "PLC"}
    saida = {
        "ger": datetime.now(FUSO).strftime("%Y-%m-%dT%H:%M"),  # horário de Brasília
        "ver": [[v["nome"], v["partido"], v["ativo"], v["votos"], v["completo"], v["foto"]] for v in ver],
        "vid": vid,
        "sess": sess,
        "nom": nom,
        "cnt": cnt,
        "proj": proj,
        "tot": tot,
        "tdesc": {t["sigla"]: t["descricao"] for t in tipos.values() if t["sigla"] in usadas},
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, separators=(",", ":"))
    print("data.json gerado.")


if __name__ == "__main__":
    main()
