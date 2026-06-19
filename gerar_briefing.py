"""
Briefing de Mercado — Gerador Automático
Roda via GitHub Actions todo dia às 05:00 (Brasília)
"""

import os, json, re
from datetime import date, timedelta
from anthropic import Anthropic

client = Anthropic()

TEMAS = [
    ("cartoes",    "Cartões",                   "cartões crédito débito fintechs adquirência Brasil"),
    ("pagamentos", "Meios de Pagamento",         "Pix pagamentos instantâneos Open Finance Brasil"),
    ("marketplace","Marketplace",                "marketplace e-commerce plataformas digitais Brasil"),
    ("varejo",     "Varejo",                     "varejo físico digital supermercados franquias Brasil"),
    ("tag",        "Tag Veicular",               "tag veicular pedágio Free Flow ANTT Brasil"),
    ("bancos",     "Bancos",                     "bancos digitais incumbentes crédito regulação Brasil"),
    ("fintechs",   "Fintechs",                   "fintechs startups financeiras crédito digital Brasil"),
    ("loyalty",    "Loyalty e Fidelização",      "programas fidelidade pontos milhas cashback Brasil"),
    ("ia",         "Inteligência Artificial",    "inteligência artificial IA mercado financeiro varejo pagamentos Brasil"),
    ("socios",     "Sócios e Parceiros",         "Carrefour GPA Azul Latam JHSF Google Conectcar Ponto Frio Casas Bahia notícias"),
]

TODOS_IDS = [t[0] for t in TEMAS]

SYSTEM = """Você é um analista sênior de mercado financeiro e varejo brasileiro.
Pesquise as notícias mais relevantes publicadas ONTEM sobre o tema solicitado.
Retorne SOMENTE um objeto JSON válido, sem markdown, sem texto fora do objeto."""

def build_prompt(tema_id, tema_label, tema_query, data_ontem, todos_temas):
    temas_str = ", ".join([f'"{t[0]}" ({t[1]})' for t in todos_temas])
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
      "destaque": "Dado ou frase mais relevante da notícia",
      "categoria": "Mercado",
      "impacto": "alto",
      "data_pub": "{data_ontem}",
      "tambem_em": []
    }}
  ]
}}

Regras OBRIGATÓRIAS:
- Inclua notícias com data de publicação de ontem ({data_ontem}) prioritariamente
- Para notícias dos últimos 7 dias sem cobertura de ontem, inclua com a data_pub correta
- categoria: Regulatório | Mercado | Tecnologia | Competição | Tendência
- impacto: alto | médio | baixo
- termometro: positivo | neutro | negativo
- Mínimo 3 notícias, máximo 8 por tema
- URL deve ser o link real do artigo, não da homepage
- tambem_em: lista com IDs dos outros agrupamentos onde esta notícia também se encaixa.
  IDs disponíveis: {temas_str}
  Deixe vazio [] se a notícia pertence apenas a este tema.
  Exemplo: uma notícia sobre IA no Pix em "pagamentos" pode ter tambem_em: ["ia", "fintechs"]
- APENAS JSON, zero texto fora do objeto"""


def buscar_tema(tema_id, tema_label, tema_query, data_ontem):
    print(f"  [{tema_id}] {tema_label}...", end=" ", flush=True)
    messages = [{"role": "user", "content": build_prompt(tema_id, tema_label, tema_query, data_ontem, TEMAS)}]

    for _ in range(10):
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

    # Garante que tambem_em só contém IDs válidos e não inclui o próprio tema
    for n in parsed.get("noticias", []):
        tambem = n.get("tambem_em", [])
        n["tambem_em"] = [t for t in tambem if t in TODOS_IDS and t != tema_id]

    n_ontem = len([n for n in parsed.get("noticias", []) if data_ontem in str(n.get("data_pub", ""))])
    n_cross  = sum(1 for n in parsed.get("noticias", []) if n.get("tambem_em"))
    print(f"OK ({len(parsed.get('noticias',[]))} notícias, {n_ontem} de ontem, {n_cross} com cross-tag)")
    return parsed


def main():
    hoje   = date.today()
    ontem  = hoje - timedelta(days=1)

    meses_pt = {"January":"janeiro","February":"fevereiro","March":"março","April":"abril",
                 "May":"maio","June":"junho","July":"julho","August":"agosto",
                 "September":"setembro","October":"outubro","November":"novembro","December":"dezembro"}
    meses_abr = {1:"jan",2:"fev",3:"mar",4:"abr",5:"mai",6:"jun",
                  7:"jul",8:"ago",9:"set",10:"out",11:"nov",12:"dez"}

    data_ontem_str = f"{ontem.day}/{meses_abr[ontem.month]}/{ontem.year}"
    data_edicao = f"{hoje.strftime('%A').capitalize()}, {hoje.day} de {meses_pt.get(hoje.strftime('%B'), hoje.strftime('%B'))} de {hoje.year}"

    print(f"\n{'='*55}")
    print(f"Briefing de Mercado — {data_edicao}")
    print(f"Buscando notícias de: {data_ontem_str}")
    print(f"Temas: {len(TEMAS)} | Cross-tags: ativado")
    print(f"{'='*55}")

    temas_data = {}
    for tid, tlabel, tquery in TEMAS:
        temas_data[tid] = buscar_tema(tid, tlabel, tquery, data_ontem_str)

    data = {
        "data_edicao":  data_edicao,
        "data_geracao": f"{hoje.strftime('%d/%m/%Y')} · 05:00",
        "janela":       f"{(hoje - timedelta(days=7)).day}/{meses_abr[(hoje-timedelta(days=7)).month]}–{ontem.day}/{meses_abr[ontem.month]}/{hoje.year}",
        "temas":        temas_data,
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
    dias_pt = {"Monday":"Segunda-feira","Tuesday":"Terça-feira","Wednesday":"Quarta-feira",
               "Thursday":"Quinta-feira","Friday":"Sexta-feira","Saturday":"Sábado","Sunday":"Domingo"}
    label = f"{dias_pt.get(hoje.strftime('%A'), hoje.strftime('%A'))}, {hoje.day} de {meses_pt.get(hoje.strftime('%B'),'?')} de {hoje.year}"
    idx["edicoes"].insert(0, {"label": label, "arquivo": fname})
    idx["edicoes"] = idx["edicoes"][:30]

    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    print(f"✅ index.json atualizado ({len(idx['edicoes'])} edições)")
    print(f"\n🎉 Briefing pronto!")


if __name__ == "__main__":
    main()
