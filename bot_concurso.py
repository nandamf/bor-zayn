#!/usr/bin/env python3
"""
Bot monitor do concurso cultural (Zayn SP meet and greet - Hugo Gloss).

O que faz:
  - Baixa a página a cada X minutos
  - Procura as HASHTAGS (#NomeDaMusica) e os nomes de músicas do Zayn
  - Avisa quando aparecer hashtag nova ou quando a página mudar
  - Guarda tudo em historico/ (texto da página + hashtags.txt)

Como usar:
  1) pip install requests
  2) python bot_concurso.py              -> roda em loop
     python bot_concurso.py --uma-vez    -> checa uma vez
     python bot_concurso.py --hashtags   -> só mostra as hashtags atuais
     python bot_concurso.py --teste      -> envia uma mensagem de teste ao Telegram

Telegram (opcional):
  export TELEGRAM_TOKEN="token_do_BotFather"
  export TELEGRAM_CHAT_ID="seu_chat_id"
"""

import argparse
import html
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import requests

URL = "https://hugogloss.uol.com.br/concurso-cultural/zayn-sp-meet-and-greet/"
INTERVALO_MINUTOS = 10
PASTA = Path("historico")
ARQ_HASHTAGS = PASTA / "hashtags.txt"

# Edite à vontade: nomes das músicas do Zayn que você quer reconhecer.
MUSICAS = [
    # Mind of Mine (2016)
    "MiNd Of MiNdd", "Intro", "PILLOWTALK", "iT's YoU", "BeFoUr", "sHe", "dRuNk",
    "INTERMISSION: fLoWer", "Flower", "rEaR vIeW", "wRoNg", "fOoL fOr YoU",
    "BoRdErSz", "tRuTh", "lUcOzAdE", "TiO", "BLUE", "BRIGHT", "LIKE I WOULD",
    "SHE DON'T LOVE ME", "Do Something Good", "Golden",
    # Icarus Falls (2018)
    "Let Me", "Natural", "Back To Life", "Common", "Imprint", "Stand Still",
    "Tonight", "Flight Of The Stars", "If I Got You", "Talk To Me",
    "There You Are", "I Don't Mind", "Icarus Interlude", "Good Guy",
    "You Wish You Knew", "Sour Diesel", "Satisfaction", "Scripted",
    "Entertainer", "All That", "Good Years", "Fresh Air", "Rainberry",
    "Insomnia", "No Candle No Light", "Fingers", "Too Much",
    "Still Got Time", "Dusk Till Dawn",
    # Nobody Is Listening (2021)
    "Calamity", "Better", "Outside", "Vibez", "When Love's Around",
    "Connexion", "Sweat", "Unfuckwitable", "Unfuckwithable", "Windowsill",
    "Tightrope", "River Road",
    # Room Under the Stairs (2024)
    "Dreamin", "What I Am", "Grateful", "Alienated", "My Woman",
    "How It Feels", "Stardust", "Gates Of Hell", "Birds On A Cloud",
    "Concrete Kisses", "False Starts", "The Time", "Something In The Water",
    "Shoot At Will", "Fuchsia Sea", "Ignorance Ain't Bliss", "Lied To",
    "In The Bag", "Gave",
    # Singles e colaboracoes
    "I Don't Wanna Live Forever", "A Whole New World", "EYES CLOSED",
    "Heaven Baby", "Die For Me",
    # Albuns
    "Mind of Mine", "Icarus Falls", "Nobody Is Listening",
    "Room Under the Stairs",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MonitorConcurso/1.0; uso pessoal)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def normalizar(s: str) -> str:
    """minúsculas, sem acento, sem espaço/símbolo: 'Dusk Till Dawn' -> 'dusktilldawn'"""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


MUSICAS_NORM = {normalizar(m): m for m in MUSICAS}


def texto_visivel(html_bruto: str) -> str:
    t = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html_bruto)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def baixar() -> str:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return texto_visivel(r.text)


def extrair_hashtags(texto: str) -> list[str]:
    """Todas as #hashtags da página, na ordem em que aparecem, sem repetir."""
    achadas = re.findall(r"#[^\W_][\w]*", texto, flags=re.UNICODE)
    vistas, resultado = set(), []
    for h in achadas:
        chave = h.lower()
        if chave not in vistas:
            vistas.add(chave)
            resultado.append(h)
    return resultado


def musicas_citadas(texto: str) -> list[str]:
    """Músicas do Zayn que aparecem como #hashtag na página.
    (Só hashtags: nomes como 'Better' ou 'She' dariam falso positivo no texto corrido.)"""
    achadas = []
    for h in extrair_hashtags(texto):
        nome = MUSICAS_NORM.get(normalizar(h))
        if nome and nome not in achadas:
            achadas.append(nome)
    return achadas


def hashtag_e_musica(h: str) -> bool:
    return normalizar(h) in MUSICAS_NORM


def enviar_telegram(msg: str) -> tuple[bool, str]:
    """Envia ao Telegram. Retorna (deu_certo, detalhe)."""
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False, "TELEGRAM_TOKEN e/ou TELEGRAM_CHAT_ID não configurados"
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat, "text": msg[:4000]},
            timeout=15,
        )
        dados = r.json()
        if dados.get("ok"):
            return True, "mensagem enviada"
        return False, f"Telegram recusou: {dados.get('description')}"
    except (requests.RequestException, ValueError) as e:
        return False, f"falha de rede: {e}"


def avisar(msg: str) -> None:
    print(f"\n[{datetime.now():%d/%m %H:%M}] {msg}\n")
    ok, detalhe = enviar_telegram(msg)
    if not ok:
        print(f"(Telegram: {detalhe})")


def ler_hashtags_salvas() -> list[str] | None:
    if not ARQ_HASHTAGS.exists():
        return None
    return [l for l in ARQ_HASHTAGS.read_text(encoding="utf-8").splitlines() if l]


def salvar(texto: str, hashtags: list[str]) -> None:
    PASTA.mkdir(exist_ok=True)
    if not os.getenv("GITHUB_ACTIONS"):  # no GitHub, evita encher o repositório
        (PASTA / f"{datetime.now():%Y%m%d_%H%M%S}.txt").write_text(texto, encoding="utf-8")
    ARQ_HASHTAGS.write_text("\n".join(hashtags), encoding="utf-8")


def formatar(hashtags: list[str]) -> str:
    if not hashtags:
        return "nenhuma hashtag encontrada"
    return "  ".join(
        f"{h}{' (música)' if hashtag_e_musica(h) else ''}" for h in hashtags
    )


def checar() -> bool:
    try:
        texto = baixar()
    except requests.RequestException as e:
        print(f"[{datetime.now():%H:%M}] Erro ao acessar a página: {e}")
        return False

    hashtags = extrair_hashtags(texto)
    antigas = ler_hashtags_salvas()

    if antigas is None:
        salvar(texto, hashtags)
        avisar(
            "Monitoramento iniciado.\n"
            f"Hashtags na página: {formatar(hashtags)}\n"
            f"Músicas citadas: {', '.join(musicas_citadas(texto)) or 'nenhuma'}"
        )
        return True

    novas = [h for h in hashtags if h.lower() not in {a.lower() for a in antigas}]
    if novas:
        salvar(texto, hashtags)
        avisar(f"NOVAS HASHTAGS NO CONCURSO!\n{formatar(novas)}\n{URL}")
    else:
        print(f"[{datetime.now():%H:%M}] Sem hashtags novas "
              f"({len(hashtags)} no total).")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uma-vez", action="store_true")
    ap.add_argument("--teste", action="store_true",
                    help="envia uma mensagem de teste ao Telegram e sai")
    ap.add_argument("--hashtags", action="store_true",
                    help="mostra as hashtags atuais e sai")
    args = ap.parse_args()

    if args.teste:
        ok, detalhe = enviar_telegram(
            "✅ Teste do monitor do concurso: o Telegram está funcionando!")
        print("OK:" if ok else "ERRO:", detalhe)
        sys.exit(0 if ok else 1)

    if args.hashtags:
        try:
            texto = baixar()
        except requests.RequestException as e:
            sys.exit(f"Erro ao acessar a página: {e}")
        print("Hashtags:", formatar(extrair_hashtags(texto)))
        print("Músicas citadas:", ", ".join(musicas_citadas(texto)) or "nenhuma")
        return

    if args.uma_vez:
        sys.exit(0 if checar() else 1)

    print(f"Monitorando {URL}\nA cada {INTERVALO_MINUTOS} min. Ctrl+C para parar.")
    try:
        while True:
            checar()
            time.sleep(INTERVALO_MINUTOS * 60)
    except KeyboardInterrupt:
        print("\nBot encerrado.")


if __name__ == "__main__":
    main()
