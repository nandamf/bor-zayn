# Monitor do concurso Zayn (Hugo Gloss)

Checa a página do concurso e avisa no Telegram quando aparecer hashtag nova.

## Colocar para rodar no GitHub (sem seu notebook ligado)

1. Crie um repositório **privado** no GitHub e envie todos estes arquivos,
   **incluindo a pasta `.github/workflows/`**.
2. No repositório: **Settings → Secrets and variables → Actions → New repository secret**.
   Crie dois segredos:
   - `TELEGRAM_TOKEN` = token do BotFather
   - `TELEGRAM_CHAT_ID` = seu número de chat
3. **Settings → Actions → General → Workflow permissions** → marque
   **Read and write permissions** e salve.

## Testar

- Aba **Actions → Monitor concurso → Run workflow** (deixe "Enviar mensagem de teste" marcado).
  - Você deve receber no Telegram: a mensagem de teste e depois "Monitoramento iniciado".
  - Se a execução ficar vermelha, abra-a e veja o erro (ex.: site bloqueando o acesso).
- Segundo teste: apague o arquivo `historico/hashtags.txt` no GitHub e rode de novo.
  O bot trata como primeira execução e manda "Monitoramento iniciado" outra vez.
- Terceiro teste: edite `historico/hashtags.txt`, apague uma linha e rode de novo.
  O bot acha que aquela hashtag é nova e avisa.

## Rodar no seu computador

    pip install -r requirements.txt
    python bot_concurso.py --teste      # testa o Telegram
    python bot_concurso.py --hashtags   # mostra as hashtags da página agora
    python bot_concurso.py              # fica em loop (a cada 10 min)

## Observações

- No plano grátis, repositório privado tem 2.000 min/mês de Actions. Checar a cada
  30 min usa cerca de 1.440. Menos que isso, não passa do limite.
- O agendamento do GitHub pode atrasar alguns minutos.
- Se a execução falhar, o GitHub manda e-mail avisando.
