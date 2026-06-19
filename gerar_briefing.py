"""
Briefing de Mercado — Gerador Automático
Roda via GitHub Actions todo dia às 05:00 (Brasília)
Também pode ser rodado manualmente: python gerar_briefing.py
"""

import os, json, re
from datetime import date, timedelta
from anthropic import Anthropic

client = Anthropic()  # usa ANTHROPIC_API_KEY do ambiente

# ── Configuração ──────────────────────────────────────────────────
TEMAS = [
    ("cartoes",       "Cartões",              "cartões crédito débito fintechs adquirência Brasil"),
    ("pagamentos",    "Meios de Pagamento",   "Pix pagamentos instantâneos Open Finance Brasil"),
    ("marketplace",   "Marketplace",          "marketplace e-commerce varejo digital Brasil"),
    ("varejo",        "Varejo",               "varejo físico digital supermercados franquias Brasil"),
    ("tag",           "Tag Veicular",         "tag veicular pedágio Free Flow ANTT Brasil"),
    ("bancos",        "Bancos",               "bancos digitais incumbentes crédito regulação Brasil"),
    ("fintechs",      "Fintechs",             "fintechs startups financeiras crédito digital Brasil"),
    ("loyalty",       "Loyalty e Fidelização","programas fidelidade pontos milhas cashback Brasil"),
]

SYSTEM = """Você é um analista sênior de mercado financeiro e varejo brasileiro.
Sua tarefa é pesquisar e compilar as notícias mais relevantes publicadas ONTEM sobre o tema solicitado.
Retorne SOMENTE um objeto JSON válido, sem markdown, sem texto antes ou depois."""

def build_prompt(tema_label, tema_query, data_ontem):
    return f"""Pesquise as notícias publicadas ONTEM ({data_ontem}) sobre "{tema_label}" no Brasil.
Query sugerida: "{tema_query} {data_ontem}"

Retorne APENAS este JSON (sem markdown):
{{
  "resumo": "2 frases sobre o cenário do dia",
  "termometro": "positivo",
  "noticias": [
    {{
      "titulo": "Título real da notícia",
      "fonte": "Nome do veículo",
      "url": "https://url-real-da-noticia.com.br",
      "destaque": "Dado ou frase mais relevante",
      "categoria": "Mercado",
      "impacto": "alto",
      "data_pub": "{data_ontem}"
    }}
  ]
}}

Regras OBRIGATÓRIAS:
- Inclua APENAS notícias com data de publicação de {data_ontem} (ontem)
- Se não houver notícias de ontem, retorne lista vazia em "noticias"
- Para notícias da semana (até 7 dias atrás), inclua também com a data_pub correta
- categoria: Regulatório | Mercado | Tecnologia | Competição | Tendência
- impacto: alto | médio | baixo
- termometro: positivo | neutro | negativo
- Mínimo 3 notícias, máximo 8 por tema
- URL deve ser o link real do artigo, não da homepage
- APENAS JSON, zero texto fora do objeto"""


def buscar_tema(tema_id, tema_label, tema_query, data_ontem):
    print(f"  Buscando: {tema_label}...", end=" ", flush=True)
    messages = [{"role": "user", "content": build_prompt(tema_label, tema_query, data_ontem)}]

    for turno in range(8):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
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

    # extrai texto
    text = "".join(b.text for b in resp.content if b.type == "text").strip()

    # parse JSON
    try:
        parsed = json.loads(text)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            print(f"ERRO: JSON não encontrado")
            return {"resumo": "Sem dados", "termometro": "neutro", "noticias": []}
        try:
            parsed = json.loads(m.group(0))
        except Exception as e:
            print(f"ERRO parse: {e}")
            return {"resumo": "Erro ao processar", "termometro": "neutro", "noticias": []}

    n_ontem = len([n for n in parsed.get("noticias", []) if data_ontem in str(n.get("data_pub", ""))])
    print(f"OK ({len(parsed.get('noticias',[]))} notícias, {n_ontem} de ontem)")
    return parsed


def main():
    hoje = date.today()
    ontem = hoje - timedelta(days=1)

    # formatos
    data_ontem_br  = ontem.strftime("%d/%b/%Y").lower().replace(
        "jan","jan").replace("feb","fev").replace("mar","mar").replace(
        "apr","abr").replace("may","mai").replace("jun","jun").replace(
        "jul","jul").replace("aug","ago").replace("sep","set").replace(
        "oct","out").replace("nov","nov").replace("dec","dez")
    # ex: "18/jun/2026"
    data_ontem_str = ontem.strftime("%-d") + "/" + data_ontem_br.split("/")[1] + "/" + str(ontem.year)

    data_edicao = hoje.strftime("%A, %d de %B de %Y").lower()
    # capitaliza primeiro char
    data_edicao = data_edicao[0].upper() + data_edicao[1:]

    janela_inicio = (hoje - timedelta(days=7)).strftime("%d/%b").lower()
    janela_fim    = ontem.strftime("%d/%b").lower()

    print(f"\n{'='*50}")
    print(f"Briefing de Mercado — {data_edicao}")
    print(f"Buscando notícias de: {data_ontem_str}")
    print(f"{'='*50}")

    temas_data = {}
    for tid, tlabel, tquery in TEMAS:
        temas_data[tid] = buscar_tema(tid, tlabel, tquery, data_ontem_str)

    data = {
        "data_edicao":  data_edicao,
        "data_geracao": hoje.strftime("%d/%m/%Y") + " · 05:00",
        "janela":       f"{janela_inicio}–{janela_fim}/{hoje.year}",
        "temas":        temas_data,
    }

    # garante pasta dados/
    os.makedirs("dados", exist_ok=True)

    # salva JSON
    fname = hoje.strftime("%Y-%m-%d") + ".json"
    fpath = os.path.join("dados", fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON salvo: {fpath}")

    # atualiza index.json
    idx_path = os.path.join("dados", "index.json")
    try:
        with open(idx_path, encoding="utf-8") as f:
            idx = json.load(f)
    except Exception:
        idx = {"edicoes": []}

    # remove entrada duplicada se existir
    idx["edicoes"] = [e for e in idx["edicoes"] if e.get("arquivo") != fname]

    # adiciona no topo
    dia_semana = hoje.strftime("%A").capitalize()
    meses = {"January":"janeiro","February":"fevereiro","March":"março","April":"abril",
             "May":"maio","June":"junho","July":"julho","August":"agosto",
             "September":"setembro","October":"outubro","November":"novembro","December":"dezembro"}
    mes_pt = meses.get(hoje.strftime("%B"), hoje.strftime("%B"))
    label = f"{dia_semana}, {hoje.day} de {mes_pt} de {hoje.year}"

    idx["edicoes"].insert(0, {"label": label, "arquivo": fname})

    # mantém só os últimos 30 dias
    idx["edicoes"] = idx["edicoes"][:30]

    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    print(f"✅ index.json atualizado ({len(idx['edicoes'])} edições)")
    print(f"\nBriefing pronto! 🎉")


if __name__ == "__main__":
    main()
