"""
Daily News — Briefing de Mercado
Gerador Automático via GitHub Actions
Roda: Segunda, Quarta e Sexta às 05:00 (Brasília)
Arquitetura híbrida:
  - Sonnet 4.6: busca notícias via web_search (qualidade alta)
  - Haiku 4.5: formata o JSON (custo baixo)
"""

import os, json, re
from datetime import date, timedelta
from anthropic import Anthropic

client = Anthropic()

TEMAS = [
    ("cartoes",    "Cartões",                "cartões crédito débito adquirência maquininha fidelização bancos digitais rotativo parcelado Brasil"),
    ("pagamentos", "Meios de Pagamento",     "Pix Open Finance pagamentos stablecoin OUSD Mercosul hub seguros pagamento instantâneo Brasil"),
    ("marketplace","Marketplace",            "marketplace e-commerce plataformas digitais Amazon Mercado Livre Shopee omnichannel Brasil"),
    ("varejo",     "Varejo",                 "varejo físico digital supermercados franquias inadimplência consumo Copa Brasil"),
    ("tag",        "Tag Veicular",           "tag veicular pedágio Free Flow ANTT mobilidade frota gestão Brasil"),
    ("bancos",     "Bancos",                 "bancos crédito inadimplência regulação Morgan McKinsey estresse financeiro Brasil"),
    ("fintechs",   "Fintechs",              "fintechs startups crédito digital blockchain BaaS capital investimento Brasil"),
    ("loyalty",    "Loyalty e Fidelização",  "programas fidelidade pontos milhas cashback bônus transferência parceiros Brasil"),
    ("ia",         "Inteligência Artificial","inteligência artificial IA fraude pagamento banco varejo agente automação Brasil"),
    ("socios",     "Sócios e Parceiros",     "Carrefour GPA Azul Latam JHSF Google Conectcar Casas Bahia Ponto Frio parceria novidades"),
]

TODOS_IDS = [t[0] for t in TEMAS]

MESES_ABR = {1:"jan",2:"fev",3:"mar",4:"abr",5:"mai",6:"jun",
             7:"jul",8:"ago",9:"set",10:"out",11:"nov",12:"dez"}
MESES_PT  = {"January":"janeiro","February":"fevereiro","March":"março",
             "April":"abril","May":"maio","June":"junho","July":"julho",
             "August":"agosto","September":"setembro","October":"outubro",
             "November":"novembro","December":"dezembro"}
DIAS_PT   = {"Monday":"Segunda-feira","Tuesday":"Terça-feira","Wednesday":"Quarta-feira",
             "Thursday":"Quinta-feira","Friday":"Sexta-feira","Saturday":"Sábado","Sunday":"Domingo"}

def fmt_date(d):
    return f"{d.day}/{MESES_ABR[d.month]}/{d.year}"


# ── ETAPA 1: Sonnet busca as notícias ────────────────────────────
SYSTEM_BUSCA = """Você é um pesquisador especializado em mercado financeiro e varejo brasileiro.
Sua tarefa é buscar notícias reais e recentes sobre o tema solicitado.
Busque ativamente usando a ferramenta de busca — faça múltiplas buscas se necessário.
Retorne APENAS um JSON válido com as notícias encontradas, sem markdown."""

def sonnet_busca(tema_id, tema_label, tema_query, data_inicio, data_fim):
    """Sonnet faz buscas reais e retorna lista de notícias encontradas."""

    hoje_str = date.today().strftime('%Y-%m-%d')
    prompt = f"""Busque notícias publicadas nos últimos 14 dias sobre "{tema_label}" no Brasil.
Data de hoje: {hoje_str}. Inclua SOMENTE notícias de {data_inicio} até {data_fim}.

Faça PELO MENOS 4 buscas com queries diferentes, priorizando as mais recentes:
1. "{tema_query} after:{(date.today()-timedelta(days=14)).strftime('%Y-%m-%d')}"
2. "{tema_label} Brasil junho 2026"
3. "{tema_query} notícias semana"
4. Uma query sobre subtema específico mais relevante

Retorne APENAS este JSON (sem markdown):
{{
  "noticias_encontradas": [
    {{
      "titulo": "Título exato da notícia",
      "url": "https://url-exata-encontrada",
      "fonte": "Nome do veículo",
      "data_pub": "DD/mmm/YYYY",
      "trecho": "Trecho relevante da notícia"
    }}
  ]
}}

Regras OBRIGATÓRIAS:
- SOMENTE notícias publicadas entre {data_inicio} e {data_fim} — verifique a data
- Se a notícia for de antes de {data_inicio}, DESCARTE
- DEDUPLICAÇÃO: quando múltiplas fontes cobrem o MESMO evento/assunto, inclua APENAS UMA — a de fonte mais relevante
- Prioridade de fontes (ordem decrescente): Banco Central, Valor Econômico, Folha, Globo, InfoMoney, Finsiders Brasil, Let's Money, Exame, TIInside, Money Times, E-Commerce Brasil, Blocknews, Reuters, Bloomberg, McKinsey, Oliver Wyman
- Busque cobrir ASSUNTOS DIFERENTES — diversidade é mais importante que volume
- Mínimo 3, máximo 6 notícias únicas por tema
- URL EXATA encontrada na busca — não invente
- APENAS JSON, zero texto fora"""

    messages = [{"role": "user", "content": prompt}]

    for _ in range(15):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            system=SYSTEM_BUSCA,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "end_turn":
            break
        if resp.stop_reason == "tool_use":
            tool_results = [
                {"type": "tool_result", "tool_use_id": b.id, "content": "ok"}
                for b in resp.content if b.type == "tool_use"
            ]
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

    text = "".join(b.text for b in resp.content if b.type == "text").strip()

    try:
        parsed = json.loads(text)
        return parsed.get("noticias_encontradas", [])
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                parsed = json.loads(m.group(0))
                return parsed.get("noticias_encontradas", [])
            except:
                pass
    return []


# ── ETAPA 2: Haiku formata o JSON final ──────────────────────────
SYSTEM_FORMATO = """Você é um analista sênior de mercado financeiro e varejo brasileiro.
Receberá notícias já pesquisadas e deve classificá-las e formatá-las.
Retorne APENAS um JSON válido, sem markdown."""

def haiku_formata(tema_id, tema_label, data_inicio, data_fim, noticias_raw):
    """Haiku classifica e formata as notícias encontradas pelo Sonnet."""

    temas_str = ", ".join([f'"{t[0]}" ({t[1]})' for t in TEMAS])

    noticias_txt = "\n".join([
        f"{i+1}. TÍTULO: {n.get('titulo','')}\n   URL: {n.get('url','')}\n   FONTE: {n.get('fonte','')}\n   DATA: {n.get('data_pub','')}\n   TRECHO: {n.get('trecho','')}"
        for i, n in enumerate(noticias_raw)
    ])

    prompt = f"""Classifique e formate estas notícias sobre "{tema_label}" (período: {data_inicio} a {data_fim}):

{noticias_txt}

Retorne APENAS este JSON (sem markdown):
{{
  "resumo": "2 frases sobre o cenário do período",
  "termometro": "positivo",
  "noticias": [
    {{
      "titulo": "Título da notícia",
      "fonte": "Nome do veículo",
      "url": "URL exata — não modifique",
      "destaque": "Dado ou frase mais relevante extraído do trecho",
      "categoria": "Mercado",
      "impacto": "alto",
      "data_pub": "DD/mmm/YYYY",
      "tambem_em": []
    }}
  ]
}}

Regras:
- DEDUPLICAÇÃO: se duas ou mais notícias tratam do MESMO evento/assunto, mantenha APENAS a de fonte mais confiável (Valor, Folha, Globo, InfoMoney, Finsiders, Let's Money, TIInside, Money Times, BC)
- Após deduplicar, inclua no máximo 6 notícias
- Use a URL EXATAMENTE como fornecida — não modifique
- categoria: Regulatório | Mercado | Tecnologia | Competição | Tendência
- impacto: alto | médio | baixo
- termometro: positivo | neutro | negativo
- tambem_em: IDs de outros temas relacionados. Disponíveis: {temas_str}
- APENAS JSON, zero texto fora"""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=3000,
        system=SYSTEM_FORMATO,
        messages=[{"role": "user", "content": prompt}]
    )

    text = "".join(b.text for b in resp.content if b.type == "text").strip()

    try:
        parsed = json.loads(text)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return {"resumo": "Sem dados", "termometro": "neutro", "noticias": []}
        try:
            parsed = json.loads(m.group(0))
        except Exception:
            return {"resumo": "Erro ao processar", "termometro": "neutro", "noticias": []}

    # Sanitiza tambem_em
    for n in parsed.get("noticias", []):
        n["tambem_em"] = [t for t in n.get("tambem_em", []) if t in TODOS_IDS and t != tema_id]

    return parsed


# ── Pipeline principal ────────────────────────────────────────────
def buscar_tema(tema_id, tema_label, tema_query, data_inicio, data_fim):
    print(f"  [{tema_id}] {tema_label}...", end=" ", flush=True)

    # Etapa 1: Sonnet busca
    noticias_raw = sonnet_busca(tema_id, tema_label, tema_query, data_inicio, data_fim)
    print(f"Sonnet: {len(noticias_raw)} notícias encontradas...", end=" ", flush=True)

    if not noticias_raw:
        print("SEM RESULTADOS")
        return {"resumo": "Sem dados disponíveis", "termometro": "neutro", "noticias": []}

    # Etapa 2: Haiku formata
    parsed = haiku_formata(tema_id, tema_label, data_inicio, data_fim, noticias_raw)
    print(f"OK ({len(parsed.get('noticias', []))} notícias formatadas)")

    return parsed


def main():
    hoje         = date.today()
    quatorze_dias = hoje - timedelta(days=14)

    data_inicio_str = fmt_date(quatorze_dias)
    data_fim_str    = fmt_date(hoje - timedelta(days=1))
    data_edicao = (f"{DIAS_PT.get(hoje.strftime('%A'), hoje.strftime('%A'))}, "
                   f"{hoje.day} de {MESES_PT.get(hoje.strftime('%B'), hoje.strftime('%B'))} de {hoje.year}")

    print(f"\n{'='*60}")
    print(f"Daily News — {data_edicao}")
    print(f"Período: {data_inicio_str} a {data_fim_str}")
    print(f"Busca: Sonnet 4.6 | Formatação: Haiku 4.5")
    print(f"{'='*60}")

    temas_data = {}
    for tid, tlabel, tquery in TEMAS:
        temas_data[tid] = buscar_tema(tid, tlabel, tquery, data_inicio_str, data_fim_str)

    janela_ini = fmt_date(hoje - timedelta(days=14))
    data = {
        "data_edicao":     data_edicao,
        "data_geracao":    f"{hoje.strftime('%d/%m/%Y')} · 05:00",
        "janela":          f"{janela_ini}–{data_fim_str}",
        "periodo_recente": f"{data_inicio_str} a {data_fim_str}",
        "temas":           temas_data,
    }

    os.makedirs("dados", exist_ok=True)
    fname = f"{hoje.strftime('%Y-%m-%d')}.json"
    fpath = os.path.join("dados", fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON salvo: {fpath}")

    # Atualiza index.json
    idx_path = os.path.join("dados", "index.json")
    try:
        with open(idx_path, encoding="utf-8") as f:
            idx = json.load(f)
    except Exception:
        idx = {"edicoes": []}

    idx["edicoes"] = [e for e in idx["edicoes"] if e.get("arquivo") != fname]
    mes_pt = MESES_PT.get(hoje.strftime("%B"), hoje.strftime("%B"))
    label  = f"{DIAS_PT.get(hoje.strftime('%A'), hoje.strftime('%A'))}, {hoje.day} de {mes_pt} de {hoje.year}"
    idx["edicoes"].insert(0, {"label": label, "arquivo": fname})
    idx["edicoes"] = idx["edicoes"][:30]

    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    print(f"✅ index.json atualizado ({len(idx['edicoes'])} edições)")
    print(f"\n🎉 Daily News pronto!")


if __name__ == "__main__":
    main()
