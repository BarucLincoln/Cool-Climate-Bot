import os
import json
import logging
import random
import sys
from datetime import time
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                          ContextTypes )

# --- CONFIGURAÇÃO INICIAL ---

# Configura o logging para nos ajudar a ver o que está acontecendo
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Pega os tokens do ambiente. Essencial para a segurança.
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
API_HG = os.getenv("API_HG")

# Define o caminho do arquivo de dados. Usamos /app/data/ por causa do volume persistente na Fly.io
ARQUIVO_DADOS = '/app/data/usuarios.json'

# Define o fuso horário de Brasília para os alertas
TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")

# --- DICIONÁRIO DE FRASES ---
# Centraliza todas as respostas do bot para fácil customização.
FRASES = {
    "start": (
        "Olá! 👋 Sou o **Cool Climate Bot**, seu assistente de tempo pessoal.\n\n"
        "Comigo, você nunca mais será pego de surpresa por uma chuva ou por uma onda de calor! 🔥\n\n"
        "**O que eu posso fazer por você?**\n\n"
        "🌦️ **/clima `[cidade]`**: Consulta a previsão do tempo para qualquer cidade na hora. Ex: `/clima São Paulo, SP`\n\n"
        "📍 **/setdaily `[cidade]`**: Define ou atualiza sua cidade padrão para receber os alertas. Ex: `/setdaily Rio de Janeiro, RJ`\n\n"
        "⏰ **/daily**: Ativa ou desativa os alertas diários automáticos (às 06:30 e 20:30).\n\n"
        "☔ **/alertachuva**: Ativa ou desativa os alertas de chuva para as próximas horas.\n\n"
        "👕 **/lookdodia**: Sugere um look com base no clima da sua cidade salva.\n\n"
        "Comece definindo sua cidade com `/setdaily` e ativando os alertas com `/daily`!"
    ),
    "erro_api": [
        "Ops, meu serviço de meteorologia parece estar fora do ar. ⛈️ Tente novamente em alguns instantes.",
        "Não consegui contato com a central do tempo. Pode tentar de novo daqui a pouco?",
        "Parece que os satélites estão de folga. 🛰️ Por favor, tente mais tarde.",
    ],
    "cidade_nao_encontrada": [
        "Hmm, não encontrei essa cidade. 🧐 Será que o nome está certinho? Tente o formato `Cidade, UF`.",
        "Essa cidade não apareceu no meu mapa. Pode conferir se digitou corretamente?",
        "Não achei essa cidade. Tenta de novo, talvez com o nome do estado junto para me ajudar.",
    ],
    "cidade_nao_definida": [
        "Parece que você ainda não me disse qual é a sua cidade. 🤔",
        "Qual cidade você quer que eu monitore? Me diga usando o comando `/setdaily`.",
        "Primeiro, preciso saber sua cidade. Use `/setdaily Cidade, UF` para configurar.",
    ],
    "setdaily_sucesso": [
        "Show! Sua cidade foi definida como **{cidade}**. ✅\nAgora você já pode usar os comandos `/daily`, `/alertachuva` e `/lookdodia`!",
        "Anotado! Vou ficar de olho no tempo em **{cidade}**. 👀\nLembre-se de ativar os alertas com `/daily` se quiser.",
        "Tudo certo! **{cidade}** agora é sua cidade padrão. O que vamos fazer agora?",
    ],
    "daily_ativado": [
        "Pode deixar! Alertas diários ativados para **{cidade}**. 🌤️ Você receberá a previsão às 06:30 e 20:30 (Horário de Brasília). Para desativar, envie /daily de novo.",
        "Combinado! Vou te mandar a previsão para **{cidade}** todos os dias de manhã e à noite. Se mudar de ideia, é só usar /daily novamente.",
    ],
    "daily_desativado": [
        "Ok, alertas diários desativados. Sem mais mensagens automáticas. Se sentir saudades, já sabe o que fazer! 😉",
        "Tudo bem, desativei os alertas diários. Quando quiser reativar, é só me chamar com /daily.",
    ],
    "alertachuva_ativado": [
        "Beleza! Alertas de chuva ativados para **{cidade}**. ☔ Se uma chuva forte estiver a caminho, eu te aviso! Para cancelar, use /alertachuva de novo.",
        "Ativado! Vou monitorar o céu de **{cidade}** para você. Se precisar de guarda-chuva, eu te dou um toque. Para desativar, é só usar /alertachuva.",
    ],
    "alertachuva_desativado": [
        "Ok, alertas de chuva desativados. Você está por conta própria agora! 😉 Brincadeira, se precisar, é só reativar.",
        "Certo, parei de monitorar a chuva para você. Se mudar de ideia, o comando /alertachuva está aí.",
    ],
    "ajuda_setdaily_primeiro": [
        "Opa, para usar este comando, primeiro preciso saber sua cidade. Use `/setdaily Cidade, UF` para configurar. 👍",
        "Calma lá! Antes, me diga qual sua cidade padrão com o comando `/setdaily`.",
    ],
    "look_quente": [
        "Hoje o dia pede roupas leves! Pense em camisetas, regatas, shorts, saias e vestidos. E não esqueça o protetor solar! ☀️😎",
        "Calorão à vista! A dica é: tecidos leves e cores claras. Bermudas e sandálias são seus melhores amigos hoje. Hidrate-se! 💧",
    ],
    "look_frio": [
        "Brrr! Melhor tirar os casacos do armário. Uma boa blusa, calça comprida e talvez uma jaqueta ou moletom são essenciais. 🧥🧣",
        "O friozinho chegou! Hora de usar camadas: uma camiseta, um suéter por cima e, se precisar, um casaco mais pesado. Mantenha-se aquecido! ☕",
    ],
    "look_ameno": [
        "Hoje o tempo está perfeito! Uma calça jeans com uma camiseta ou camisa de manga comprida é uma ótima pedida. Um casaquinho leve pode ser útil à noite. 😉",
        "Clima super agradável! Vá com seu look casual favorito. Uma jaqueta jeans ou um cardigã são ótimos para ter à mão, só por garantia.",
    ],
    "saudacao_manha": [
        "Bom dia! ☀️ Que tal começar o dia com a previsão do tempo?",
        "Levanta e anda, que o dia já começou! ✨ Confira o clima de hoje:",
        "Bom dia, flor do dia! 🌸 Preparei a previsão para você:",
        "Aquele cheirinho de café no ar... ☕ Bom dia! Aqui está o seu resumo do tempo:",
        "Ei, bom dia! Espero que tenha dormido bem. 😊 Olha só como o tempo está hoje:",
    ],
    "saudacao_noite": [
        "Boa noite! 😴 Hora de descansar, mas antes, veja a previsão para amanhã:",
        "Chegou a hora de recarregar as energias! 🔋 Tenha uma ótima noite! Segue o clima para amanhã:",
        "As estrelas já estão no céu... ✨ Boa noite! Preparei a previsão para o seu descanso:",
        "Boa noite! Durma bem e sonhe com os anjinhos. 😇 Ah, e aqui está o tempo para amanhã:",
        "Missão cumprida por hoje! 💪 Tenha uma excelente noite de sono! A previsão de amanhã é:",
    ],
}

# --- FUNÇÕES DE DADOS ---

def carregar_dados():
    """Carrega os dados dos usuários do arquivo JSON."""
    if not os.path.exists(ARQUIVO_DADOS):
        # Se o arquivo não existe, cria um diretório e um arquivo vazio
        os.makedirs(os.path.dirname(ARQUIVO_DADOS), exist_ok=True)
        with open(ARQUIVO_DADOS, 'w') as f:
            json.dump({}, f)
        return {}
    try:
        with open(ARQUIVO_DADOS, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def salvar_dados(dados):
    """Salva os dados dos usuários no arquivo JSON."""
    with open(ARQUIVO_DADOS, 'w') as f:
        json.dump(dados, f, indent=4)

# --- FUNÇÕES DE LÓGICA PRINCIPAL ---

async def obter_clima_atual(cidade: str):
    """Busca os dados de clima na API da HG Brasil."""
    url = f"https://api.hgbrasil.com/weather?key={API_HG}&city_name={cidade}"
    try:
        async with httpx.AsyncClient( ) as client:
            resposta = await client.get(url, timeout=10.0)
            resposta.raise_for_status()
            return resposta.json()
    except httpx.RequestError as exc:
        logger.error(f"Erro de rede ao chamar a API: {exc}" )
        return {"error": "api_error"}
    except Exception as exc:
        logger.error(f"Erro inesperado ao processar a API: {exc}")
        return {"error": "unknown_error"}

def gerar_lookdodia(clima: dict):
    """Gera uma sugestão de look com base na temperatura."""
    temp = clima.get('temp')
    if temp >= 25:
        return random.choice(FRASES["look_quente"])
    elif temp <= 17:
        return random.choice(FRASES["look_frio"])
    else:
        return random.choice(FRASES["look_ameno"])

def formatar_previsao(dados_clima: dict, incluir_lookdodia: bool = False):
    """Formata a resposta da API em um texto amigável."""
    results = dados_clima.get('results', {})
    if not results:
        return None

    cidade = results.get('city_name', 'N/A')
    temp = results.get('temp', 'N/A')
    descricao = results.get('description', 'N/A')
    umidade = results.get('humidity', 'N/A')
    nascer_sol = results.get('sunrise', 'N/A')
    por_sol = results.get('sunset', 'N/A')
    velocidade_vento = results.get('wind_speedy', 'N/A')
    
    previsao_hoje = results.get('forecast', [{}])[0]
    max_temp = previsao_hoje.get('max', 'N/A')
    min_temp = previsao_hoje.get('min', 'N/A')
    prob_chuva = previsao_hoje.get('rain_probability', 0)

    texto = (
        f"📍 *{cidade}*\n"
        f"🌡️ Agora: *{temp}°C* - {descricao}\n"
        f"🔺 Máx: {max_temp}°C | 🔻 Mín: {min_temp}°C\n"
        f"💧 Umidade: {umidade}%\n"
        f"💨 Vento: {velocidade_vento}\n"
        f"🌅 Nascer do Sol: {nascer_sol} | 🌇 Pôr do Sol: {por_sol}"
    )

    if prob_chuva > 60:
        texto += f"\n\n⚠️ *Alerta de Chuva: {prob_chuva}% de chance.*\n_É bom levar o guarda-chuva! ☂️_"

    if incluir_lookdodia:
        look = gerar_lookdodia(results)
        texto += f"\n\n👕 *Look do Dia:* {look}"

    return texto

# --- FUNÇÕES DE COMANDOS DO TELEGRAM ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia a mensagem de boas-vindas."""
    await update.message.reply_text(FRASES["start"], parse_mode="Markdown")

async def clima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca e exibe o clima para uma cidade informada."""
    if not context.args:
        await update.message.reply_text("Uso: `/clima nome da cidade, uf`", parse_mode="Markdown")
        return

    cidade_usuario = " ".join(context.args)
    dados_clima = await obter_clima_atual(cidade_usuario)

    if dados_clima.get("error"):
        await update.message.reply_text(random.choice(FRASES["erro_api"]))
        return

    texto_previsao = formatar_previsao(dados_clima)
    if texto_previsao:
        await update.message.reply_text(texto_previsao, parse_mode="Markdown")
    else:
        await update.message.reply_text(random.choice(FRASES["cidade_nao_encontrada"]))

async def setdaily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define a cidade padrão do usuário."""
    chat_id = str(update.effective_chat.id)
    if not context.args:
        await update.message.reply_text("Uso: `/setdaily nome da cidade, uf`", parse_mode="Markdown")
        return

    cidade_usuario = " ".join(context.args)
    dados_clima = await obter_clima_atual(cidade_usuario)
    results = dados_clima.get('results')

    if not results:
        await update.message.reply_text(random.choice(FRASES["cidade_nao_encontrada"]))
        return

    cidade_correta = results['city_name']
    dados = carregar_dados()
    if chat_id not in dados:
        dados[chat_id] = {}
    
    dados[chat_id]["cidade"] = cidade_correta
    salvar_dados(dados)
    
    resposta = random.choice(FRASES["setdaily_sucesso"]).format(cidade=cidade_correta)
    await update.message.reply_text(resposta, parse_mode="Markdown")

async def lookdodia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia uma sugestão de look com base no clima da cidade salva."""
    chat_id = str(update.effective_chat.id)
    dados = carregar_dados()

    if chat_id not in dados or "cidade" not in dados[chat_id]:
        await update.message.reply_text(random.choice(FRASES["ajuda_setdaily_primeiro"]))
        return

    cidade = dados[chat_id]["cidade"]
    dados_clima = await obter_clima_atual(cidade)
    results = dados_clima.get('results')

    if results:
        look = gerar_lookdodia(results)
        await update.message.reply_text(f"👕 Para o clima de hoje em *{cidade}*, a sugestão é:\n\n_{look}_", parse_mode="Markdown")
    else:
        await update.message.reply_text(random.choice(FRASES["erro_api"]))

# --- FUNÇÕES DE TAREFAS AGENDADAS (JOBS) ---

async def enviar_previsao_diaria(context: ContextTypes.DEFAULT_TYPE):
    """Função executada pelo JobQueue para enviar os alertas diários."""
    job = context.job
    chat_id = str(job.chat_id)
    tipo_alerta = job.data.get("tipo", "manha")

    dados = carregar_dados()
    if chat_id not in dados or not dados[chat_id].get("daily_on", False):
        logger.warning(f"Job diário executado para usuário inativo ou sem dados: {chat_id}. Removendo job.")
        job.schedule_removal()
        return

    cidade = dados[chat_id]["cidade"]
    dados_clima = await obter_clima_atual(cidade)
    
    if dados_clima.get("error"):
        logger.error(f"Não foi possível obter clima para job diário do chat {chat_id}")
        return

    texto_previsao = formatar_previsao(dados_clima, incluir_lookdodia=True)
    if texto_previsao:
        if tipo_alerta == "manha":
            saudacao = random.choice(FRASES["saudacao_manha"])
        else:  # noite
            saudacao = random.choice(FRASES["saudacao_noite"])
        
        mensagem_final = f"{saudacao}\n\n{texto_previsao}"
        
        await context.bot.send_message(chat_id=job.chat_id, text=mensagem_final, parse_mode="Markdown")

async def verificar_chuva(context: ContextTypes.DEFAULT_TYPE):
    """Verifica periodicamente se há previsão de chuva."""
    job = context.job
    chat_id = str(job.chat_id)

    dados = carregar_dados()
    if chat_id not in dados or not dados[chat_id].get("rain_on", False):
        logger.warning(f"Job de chuva executado para usuário inativo: {chat_id}. Removendo job.")
        job.schedule_removal()
        return

    cidade = dados[chat_id]["cidade"]
    dados_clima = await obter_clima_atual(cidade)
    results = dados_clima.get('results', {})
    previsao_hoje = results.get('forecast', [{}])[0]
    prob_chuva = previsao_hoje.get('rain_probability', 0)

    if prob_chuva > 70:
        # Para evitar spam, só enviamos o alerta uma vez
        if not dados[chat_id].get("rain_alert_sent", False):
            await context.bot.send_message(
                chat_id=job.chat_id,
                text=f"☔ *Alerta de Chuva para as Próximas Horas em {cidade}!* ({prob_chuva}%)\n\nÉ melhor se preparar!"
            )
            dados[chat_id]["rain_alert_sent"] = True
            salvar_dados(dados)
    else:
        # Reseta o status do alerta se a chance de chuva diminuir
        if dados[chat_id].get("rain_alert_sent", False):
            dados[chat_id]["rain_alert_sent"] = False
            salvar_dados(dados)

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa ou desativa os alertas diários."""
    chat_id = str(update.effective_chat.id)
    dados = carregar_dados()

    if chat_id not in dados or "cidade" not in dados[chat_id]:
        await update.message.reply_text(random.choice(FRASES["ajuda_setdaily_primeiro"]))
        return

    cidade = dados[chat_id]["cidade"]
    jobs_existentes = context.job_queue.get_jobs_by_name(chat_id)
    
    if jobs_existentes:
        for job in jobs_existentes:
            if job.data.get("type") == "daily":
                job.schedule_removal()
        dados[chat_id]["daily_on"] = False
        await update.message.reply_text(random.choice(FRASES["daily_desativado"]))
    else:
        context.job_queue.run_daily(enviar_previsao_diaria, time(hour=6, minute=30, tzinfo=TZ_BRASILIA), name=chat_id, chat_id=update.effective_chat.id, data={"type": "daily", "tipo": "manha"})
        context.job_queue.run_daily(enviar_previsao_diaria, time(hour=20, minute=30, tzinfo=TZ_BRASILIA), name=chat_id, chat_id=update.effective_chat.id, data={"type": "daily", "tipo": "noite"})
        dados[chat_id]["daily_on"] = True
        resposta = random.choice(FRASES["daily_ativado"]).format(cidade=cidade)
        await update.message.reply_text(resposta)
    
    salvar_dados(dados)

async def alertachuva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa ou desativa os alertas de chuva."""
    chat_id = str(update.effective_chat.id)
    dados = carregar_dados()

    if chat_id not in dados or "cidade" not in dados[chat_id]:
        await update.message.reply_text(random.choice(FRASES["ajuda_setdaily_primeiro"]))
        return

    cidade = dados[chat_id]["cidade"]
    jobs_existentes = context.job_queue.get_jobs_by_name(chat_id)

    job_encontrado = None
    for job in jobs_existentes:
        if job.data.get("type") == "rain":
            job_encontrado = job
            break

    if job_encontrado:
        job_encontrado.schedule_removal()
        dados[chat_id]["rain_on"] = False
        await update.message.reply_text(random.choice(FRASES["alertachuva_desativado"]))
    else:
        context.job_queue.run_repeating(verificar_chuva, interval=3600, first=10, name=chat_id, chat_id=update.effective_chat.id, data={"type": "rain"})
        dados[chat_id]["rain_on"] = True
        resposta = random.choice(FRASES["alertachuva_ativado"]).format(cidade=cidade)
        await update.message.reply_text(resposta)

    salvar_dados(dados)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Loga os erros causados pelos updates."""
    logger.error(f"Exceção ao processar um update: {context.error}", exc_info=context.error)

# --- FUNÇÃO PRINCIPAL ---

def main():
    """Função principal que inicia e roda o bot."""
    logger.info("Iniciando o bot...")

    # Verificação de segurança para garantir que os tokens foram carregados
    if not TOKEN_TELEGRAM or not API_HG:
        logger.critical("ERRO: Variáveis de ambiente TOKEN_TELEGRAM e API_HG não definidas.")
        sys.exit("Tokens não encontrados. Encerrando.")

    # Constrói a aplicação do bot
    app = ApplicationBuilder().token(TOKEN_TELEGRAM).build()

    # Registra os handlers dos comandos
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clima", clima))
    app.add_handler(CommandHandler("setdaily", setdaily))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("alertachuva", alertachuva))
    app.add_handler(CommandHandler("lookdodia", lookdodia))

    logger.info("✅ Bot rodando. Pressione Ctrl+C para parar.")
    
    # Inicia o bot para receber atualizações
    app.run_polling()

if __name__ == '__main__':
    main()
