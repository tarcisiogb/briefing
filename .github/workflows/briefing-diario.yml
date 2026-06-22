"""
Daily News — Briefing de Mercado
Gerador Automático via GitHub Actions
Roda: Segunda, Quarta e Sexta às 05:00 (Brasília)
Modelo: claude-haiku-4-5-20251001
Busca: Google Custom Search API (gratuita)
"""

import os, json, re, urllib.request, urllib.parse
from datetime import date, timedelta
from anthropic import Anthropic

client = Anthropic()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID  = os.environ.get("GOOGLE_CSE_ID", "")

TEMAS = [
    ("cartoes",    "Cartões",                "cartões crédito débito adquirência maquininha Brasil"),
    ("pagamentos", "Meios de Pagamento",     "Pix pagamentos instantâneos Open Finance Brasil"),
    ("marketplace","Marketplace",            "marketplace e-commerce plataformas digitais Brasil"),
    ("varejo",     "Varejo",                 "varejo físico digital supermercados franquias Brasil"),
    ("tag",        "Tag Veicular",           "tag veicular pedágio Free Flow ANTT Brasil"),
    ("bancos",     "Bancos",                 "bancos digitais crédito regulação Brasil"),
    ("fintechs",   "Fintechs",              "fintechs startups financeiras crédito digital Brasil"),
    ("loyalty",    "Loyalty e Fidelização",  "programas fidelidade pontos milhas cashback Brasil"),
    ("ia",         "Inteligência Artificial","inteligência artificial IA mercado financeiro varejo Brasil"),
    ("socios",     "Sócios e Parceiros",     "Carrefour GPA Azul Latam JHSF Google Conectcar Casas Bahia Ponto Frio"),
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

def parse_date(s):
    months = {v:k for k,v in MESES_ABR.items()}
    m = re.match(r"(\d{1,2})/(\w{3})/(\d{4})", str(s))
    if not m: return None
    return date(int(m.group(3)), months.get(m.group(2).lower(), 1), int(m.group(1)))

def is_recente(data_pub, data_inicio):
    pub = parse_date(data_pub)
    ini = parse_date(data_inicio)
    if not pub or not ini: return False
    return pub >= ini

# ── Google Custom Search ──────────────────────────────────────────
def google_search(query, num=8):
    """Busca no Google e retorna lista de {title, url, snippet, source}"""
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("    ⚠ GOOGLE_API_KEY ou GOOGLE_CSE_ID não configurados")
        return []

    params = urllib.parse.urlencode({
        "key": GOOGLE_API_KEY,
        "cx":  GOOGLE_CSE_ID,
        "q":   query,
        "num": min(num, 10),
        "lr":  "lang_pt",
        "sort": "date",
    })
    url = f"https://www.googleapis.com/customsearch/v1?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        items = data.get("items", [])
        print(f"    Google retornou {len(items)} resultados")
        results = []
        for item in items:
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source":  item.get("displayLink", ""),
            })
        return results
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"    ⚠ Erro Google Search HTTP {e.code}: {body[:300]}")
        return []
    except Exception as e:
        print(f"    ⚠ Erro Google Search: {e}")
        return []

# ── Haiku: analisa e formata os resultados ────────────────────────
SYSTEM_HAIKU = """Você é um analista sênior de mercado financeiro e varejo brasileiro.
Receberá resultados de busca do Google sobre um tema específico.
Sua tarefa é analisar esses resultados e retornar APENAS um JSON válido, sem markdown."""

def haiku_analisa(tema_id, tema_label, data_inicio, data_fim, resultados, todos_temas):
    temas_str = ", ".join([f'"{t[0]}" ({t[1]})' for t in todos_temas])
    resultados_txt = "\n".join([
        f"{i+1}. TÍTULO: {r['title']}\n   URL: {r['url']}\n   FONTE: {r['source']}\n   TRECHO: {r['snippet']}"
        for i, r in enumerate(resultados)
    ])

    prompt = f"""Analise estes resultados de busca do Google sobre "{tema_label}" no Brasil (período: {data_inicio} a {data_fim}):

{resultados_txt}

Retorne APENAS este JSON (sem markdown):
{{
  "resumo": "2 frases sobre o cenário do período",
  "termometro": "positivo",
  "noticias": [
    {{
      "titulo": "Título da notícia conforme aparece no resultado",
      "fonte": "Nome do veículo (do campo FONTE)",
      "url": "URL exata do resultado — não modifique",
      "destaque": "Dado ou frase mais relevante extraído do trecho",
      "categoria": "Mercado",
      "impacto": "alto",
      "data_pub": "{data_fim}",
      "tambem_em": []
    }}
  ]
}}

Regras:
- Use APENAS as notícias dos resultados acima — não invente
- Use a URL EXATAMENTE como aparece no resultado — não modifique
- Selecione as mais relevantes: mínimo 4, máximo 8
- Priorize notícias mais recentes (data_pub entre {data_inicio} e {data_fim})
- Para notícias mais antigas dos resultados, coloque a data estimada em data_pub
- categoria: Regulatório | Mercado | Tecnologia | Competição | Tendência
- impacto: alto | médio | baixo
- termometro: positivo | neutro | negativo
- tambem_em: IDs de outros temas relacionados. Disponíveis: {temas_str}
- APENAS JSON, zero texto fora"""

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2500,
        system=SYSTEM_HAIKU,
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


def buscar_tema(tema_id, tema_label, tema_query, data_inicio, data_fim):
    print(f"  [{tema_id}] {tema_label}...", end=" ", flush=True)

    # Monta query com período
    query = f"{tema_query} after:{(date.today()-timedelta(days=7)).strftime('%Y-%m-%d')}"

    # Busca principal
    resultados = google_search(query, num=10)

    # Busca complementar se poucos resultados
    if len(resultados) < 4:
        query2 = f"{tema_label} Brasil notícias {data_fim}"
        resultados += google_search(query2, num=6)

    if not resultados:
        print("SEM RESULTADOS")
        return {"resumo": "Sem dados disponíveis", "termometro": "neutro", "noticias": []}

    # Remove duplicatas por URL
    seen = set()
    resultados_uniq = []
    for r in resultados:
        if r["url"] not in seen:
            seen.add(r["url"])
            resultados_uniq.append(r)

    print(f"{len(resultados_uniq)} resultados Google...", end=" ", flush=True)

    # Haiku analisa e formata
    parsed = haiku_analisa(tema_id, tema_label, data_inicio, data_fim, resultados_uniq, TEMAS)

    n_rec = len([n for n in parsed.get("noticias", []) if is_recente(n.get("data_pub",""), data_inicio)])
    print(f"OK ({len(parsed.get('noticias',[]))} notícias, {n_rec} recentes)")

    return parsed


def main():
    hoje      = date.today()
    dois_dias = hoje - timedelta(days=2)

    data_inicio_str = fmt_date(dois_dias)
    data_fim_str    = fmt_date(hoje - timedelta(days=1))
    data_edicao = (f"{DIAS_PT.get(hoje.strftime('%A'), hoje.strftime('%A'))}, "
                   f"{hoje.day} de {MESES_PT.get(hoje.strftime('%B'), hoje.strftime('%B'))} de {hoje.year}")

    print(f"\n{'='*58}")
    print(f"Daily News — {data_edicao}")
    print(f"Período: {data_inicio_str} a {data_fim_str}")
    print(f"Modelo: Haiku 4.5 | Busca: Google Custom Search")
    print(f"{'='*58}")

    temas_data = {}
    for tid, tlabel, tquery in TEMAS:
        temas_data[tid] = buscar_tema(tid, tlabel, tquery, data_inicio_str, data_fim_str)

    janela_ini = fmt_date(hoje - timedelta(days=7))
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
