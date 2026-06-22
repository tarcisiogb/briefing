"""
Daily News — Briefing de Mercado
Gerador Automático via GitHub Actions
Roda: Segunda, Quarta e Sexta às 05:00 (Brasília)
Modelo: claude-haiku-4-5-20251001
Busca: web_search da Anthropic
"""

import os, json, re
from datetime import date, timedelta
from anthropic import Anthropic

client = Anthropic()

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

SYSTEM = """Você é um analista sênior de mercado financeiro e varejo brasileiro.
Pesquise as notícias mais relevantes dos últimos 2 dias sobre o tema solicitado.
Retorne SOMENTE um objeto JSON válido, sem markdown, sem texto fora do objeto."""

def build_prompt(tema_id, tema_label, tema_query, data_inicio, data_fim):
    temas_str = ", ".join([f'"{t[0]}" ({t[1]})' for t in TEMAS])
    return f"""Pesquise notícias publicadas entre {data_inicio} e {data_fim} sobre "{tema_label}" no Brasil.
Query sugerida: "{tema_query}"

Retorne APENAS este JSON (sem markdown):
{{
  "resumo": "2 frases sobre o cenário do período",
  "termometro": "positivo",
  "noticias": [
    {{
      "titulo": "Título exato da notícia conforme publicado",
      "fonte": "Nome do veículo",
      "url": "https://url-exata-do-artigo.com.br",
      "destaque": "Dado ou frase mais relevante da notícia",
      "categoria": "Mercado",
      "impacto": "alto",
      "data_pub": "DD/mmm/YYYY",
      "tambem_em": []
    }}
  ]
}}

Regras:
- Priorize notícias entre {data_inicio} e {data_fim} (recentes)
- Inclua também notícias relevantes dos últimos 7 dias como complemento
- Mínimo 4, máximo 8 notícias
- URL deve ser o link exato do artigo encontrado na busca
- categoria: Regulatório | Mercado | Tecnologia | Competição | Tendência
- impacto: alto | médio | baixo
- termometro: positivo | neutro | negativo
- tambem_em: IDs de outros temas relacionados. Disponíveis: {temas_str}
- APENAS JSON, zero texto fora"""


def buscar_tema(tema_id, tema_label, tema_query, data_inicio, data_fim):
    print(f"  [{tema_id}] {tema_label}...", end=" ", flush=True)

    messages = [{"role": "user", "content": build_prompt(tema_id, tema_label, tema_query, data_inicio, data_fim)}]

    for _ in range(10):
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
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

    text = "".join(b.text for b in resp.content if b.type == "text").strip()

    try:
        parsed = json.loads(text)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            print("ERRO: JSON não encontrado")
            return {"resumo": "Sem dados", "termometro": "neutro", "noticias": []}
        try:
            parsed = json.loads(m.group(0))
        except Exception as e:
            print(f"ERRO parse: {e}")
            return {"resumo": "Erro ao processar", "termometro": "neutro", "noticias": []}

    # Sanitiza tambem_em
    for n in parsed.get("noticias", []):
        n["tambem_em"] = [t for t in n.get("tambem_em", []) if t in TODOS_IDS and t != tema_id]

    n_not = len(parsed.get("noticias", []))
    print(f"OK ({n_not} notícias)")
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
    print(f"Modelo: Haiku 4.5 | Busca: Anthropic web_search")
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
