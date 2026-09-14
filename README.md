<div align="center">

# Buscador de Token

### Scanner de novos ativos em Binance Futures com alertas, monitoramento de posições e histórico

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Binance](https://img.shields.io/badge/Binance-Futures-F0B90B?style=for-the-badge&logo=binance&logoColor=black)](https://www.binance.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Alerts-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org/)
[![CCXT](https://img.shields.io/badge/CCXT-Market_Data-111827?style=for-the-badge)](https://github.com/ccxt/ccxt)

**Python · Automação · Mercado Cripto · Monitoramento**

[Miranda Stack](https://mirandastack.com/) · [Perfil GitHub](https://github.com/EduMiranda78)

</div>

---

## Sobre o projeto

O **Buscador de Token** é uma aplicação Python criada para monitorar pares USDT em **Binance Futures**, identificar ativos recém-listados com sinais de aceleração de preço e enviar alertas automaticamente pelo Telegram.

Além do scanner, o projeto acompanha posições abertas na Binance, calcula alvo de preço, detecta encerramentos e mantém um histórico local das operações monitoradas.

O objetivo é concentrar em um único processo tarefas que normalmente exigiriam acompanhamento manual de listagens, candles, volume, momentum e posições.

---

## Fluxo principal

```text
Binance Futures
      │
      ▼
Carregamento dos pares USDT
      │
      ▼
Filtro de tokens novos
      │
      ├── quantidade de candles
      ├── preço mínimo
      ├── volume mínimo
      └── momentum de 1 hora
      │
      ▼
Candidato encontrado
      │
      ├── alerta no Telegram
      └── link para TradingView

Posições abertas na Binance
      │
      ▼
Monitoramento de entrada e alvo
      │
      ▼
Registro do resultado em histórico
```

---

## Recursos

- leitura de mercados Binance Futures por meio do `ccxt`;
- seleção de contratos lineares USDT ativos;
- identificação de tokens com histórico recente de candles;
- filtro por preço mínimo;
- filtro por volume negociado;
- cálculo de momentum de 1 hora;
- alertas automáticos pelo Telegram;
- geração de link direto para o TradingView;
- detecção de posições abertas na conta Binance;
- monitoramento do preço de entrada e alvo;
- detecção de fechamento manual ou saída por stop;
- registro de trades em JSON;
- persistência de tokens já alertados;
- logging operacional no terminal.

---

## Critérios padrão do scanner

Os parâmetros principais estão definidos no início de `app.py` e podem ser ajustados conforme o ambiente de uso.

| Parâmetro | Valor atual | Função |
|---|---:|---|
| Timeframe de token novo | `15m` | Base para verificar histórico recente |
| Máximo de candles | `64` | Define o limite para considerar um ativo novo |
| Timeframe de momentum | `1h` | Base para medir aceleração recente |
| Volume mínimo | `50.000 USDT` | Remove ativos com pouco volume |
| Preço mínimo | `1.50` | Filtro de preço configurado no scanner |
| Momentum mínimo | `5%` | Exige movimento mínimo em 1 hora |
| Alvo monitorado | `50%` | Alvo padrão aplicado às posições acompanhadas |
| Intervalo de checagem | `60 s` | Frequência do loop principal |

> Esses valores fazem parte da configuração atual do projeto e não constituem recomendação de investimento.

---

## Estrutura de dados

O projeto utiliza arquivos JSON simples para persistir o estado entre execuções.

```text
Buscadordetoken/
├── app.py                  # scanner e monitor principal
├── dashboard.py            # interface complementar
├── app_novalista.py        # rotina alternativa de listagens
├── alertados.json          # ativos que já geraram alerta
├── posicoes.json           # posições acompanhadas
├── historico.json          # histórico das operações registradas
├── novos_listados.json     # dados de novas listagens
└── templates/              # templates da interface
```

---

## Requisitos

- Python 3
- conta Binance com acesso compatível com a API utilizada
- bot do Telegram
- bibliotecas Python:
  - `ccxt`
  - `requests`
  - `python-dotenv`

Instalação básica:

```bash
git clone https://github.com/EduMiranda78/Buscadordetoken.git
cd Buscadordetoken

python3 -m venv .venv
source .venv/bin/activate

pip install ccxt requests python-dotenv
```

---

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
BINANCE_API_KEY=sua_chave
BINANCE_SECRET_KEY=seu_segredo
TELEGRAM_BOT_TOKEN=token_do_bot
TELEGRAM_CHAT_ID=id_do_chat
```

O `app.py` exige as quatro variáveis para iniciar.

### Segurança

Nunca publique chaves reais da Binance ou tokens do Telegram no repositório.

Para uma chave utilizada somente na coleta e monitoramento, mantenha as permissões da API no menor nível necessário para a finalidade pretendida.

---

## Execução

Com o ambiente configurado:

```bash
python app.py
```

O processo carrega os mercados da Binance e entra em um loop de monitoramento.

Exemplo de fluxo de alerta:

```text
🔥 PUMP EM TOKEN NOVO
Par: TOKEN/USDT
Preço: $...
Volume: $...
Momentum 1h: +...%
Gráfico: TradingView
```

---

## Monitoramento de posições

Além de procurar novos ativos, o processo consulta posições abertas na Binance.

Quando encontra uma nova posição, registra informações como:

```text
par
preço de entrada
lado
quantidade
alvo de preço
horário de inclusão
```

Quando a posição deixa de existir na corretora ou alcança o alvo monitorado, o sistema registra a operação em `historico.json`.

---

## Histórico

Cada operação registrada pode conter:

- par;
- lado;
- preço de entrada;
- preço de saída;
- quantidade;
- horário de entrada;
- horário de saída;
- duração;
- lucro percentual;
- resultado estimado em USDT;
- motivo de encerramento;
- indicação de alvo atingido.

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| Python | aplicação principal |
| CCXT | integração com mercados e posições da Binance |
| Binance Futures | fonte de mercados e posições |
| Telegram Bot API | entrega de alertas |
| Requests | chamadas HTTP |
| python-dotenv | variáveis de ambiente |
| JSON | persistência local |

---

## Observações

Este projeto é uma ferramenta técnica e experimental para coleta, filtragem e monitoramento de dados de mercado.

Ele não garante desempenho financeiro, não substitui análise de risco e não deve ser interpretado como recomendação de compra, venda ou operação de ativos.

---

## Autor

Desenvolvido por **Eduardo Miranda**.

[GitHub](https://github.com/EduMiranda78) · [Miranda Stack](https://mirandastack.com/)
