import os
import json
import logging
import httpx
import random
from datetime import time, datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv( )
TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")
API_HG = os.getenv("API_HG")
# --- ALTERE ESTA LINHA ---
ARQUIVO_DADOS = '/app/data/usuarios.json'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not TOKEN_TELEGRAM or not API_HG:
    logger.error("ERRO CRÍTICO: Variáveis de ambiente não definidas.")
    exit()

# ===================================================================
# === 🗣️ BANCO DE FRASES HUMANIZADAS (VERSÃO FINAL E COMPLETA) 🗣️ ===
# ===================================================================

FRASES = {
    "start": [
        (
            "Olá! Bem-vindo(a) ao *Cool Climate Bot*! 🌦️\n\n"
            "Eu sou seu assistente pessoal para o clima. Comigo, você nunca mais será pego de surpresa pelo tempo!\n\n"
            "Aqui estão os comandos que você pode usar:\n\n"
            "🔍 `/clima [cidade]`\n"
            "   Para uma consulta rápida do tempo.\n\n"
            "⚙️ `/setdaily [cidade]`\n"
            "   Para definir a cidade dos seus alertas.\n\n"
            "🔔 `/daily`\n"
            "   Para ativar/desativar os alertas diários (com sugestão de look!).\n\n"
            "☔️ `/alertachuva`\n"
            "   Para ativar/desativar o monitoramento de chuva.\n\n"
            "👕 `/lookdodia`\n"
            "   Para receber uma sugestão de roupa agora mesmo!"
        )
    ],
    "clima_sucesso": [
        "Feito! O tempo em *{cidade}* tá assim, ó:\n\n{previsao}",
        "Olha aí a previsão quentinha (ou fria hehe) pra *{cidade}*:\n\n{previsao}",
    ],
    "clima_erro": [
        "Hmm, não achei essa cidade no meu mapa. 🗺️ Será que o nome tá certinho?",
        "Puts, não rolou. 😕 Não encontrei essa cidade. Tenta mandar com o estado junto, tipo 'Campinas, SP'.",
    ],
    "setdaily_sucesso": [
        "Anotado! ✅ Sua cidade para os alertas diários agora é *{cidade}*. Agora é só usar /daily pra ativar as notificações!",
        "Show! Configurei *{cidade}* como sua cidade principal. Quando quiser receber os alertas, só mandar um /daily. 👍",
    ],
    "daily_ativado": [
        "Fechou! 🤝 Alertas diários ativados para *{cidade}*. Te dou um toque às 06:30 e às 20:30 (Horário de Brasília).",
        "Combinado! 🔔 Alertas programados para *{cidade}*. Fica de olho nas notificações de manhã e à noite.",
    ],
    "daily_desativado": [
        "Beleza, alertas em modo silencioso. 🔕 Você não vai mais receber as previsões automáticas.",
        "Ok, serviço de alertas pausado. Sem mais notificações diárias. Pra voltar, é só usar /daily.",
    ],
    "alerta_chuva_ativado": [
        "Beleza! ✅ Monitor de chuva ativado para *{cidade}*. Se a chance de chuva ficar alta, eu te dou um toque! 🌦️",
        "Pode deixar! Vou ficar de olho no céu de *{cidade}* pra você. Se eu vir nuvens carregadas, te aviso. 😉",
    ],
    "alerta_chuva_desativado": [
        "Ok, monitor de chuva desativado. ☀️ Sem mais alertas de temporal.",
        "Entendido. Desliguei meu radar de chuva. Você não receberá mais alertas sobre isso. 📡",
    ],
    "alerta_chuva_mensagem": [
        "☔️ *Alerta de Chuva para as Próximas Horas em {cidade}!*",
        "🌧️ *Atenção: Previsão de Chuva se Aproximando de {cidade}!*",
    ],
    "lookdodia": [
        "Pra hoje em *{cidade}*, a minha sugestão é:\n\n{look}",
        "Analisando o clima de *{cidade}*... 🧐 Acho que o look ideal é:\n\n{look}",
    ],
    "erro_generico": [
        "Eita, deu um bug aqui do meu lado. 😅 Já tô vendo o que rolou, mas tenta de novo daqui a pouco.",
        "Ops, parece que tropecei nos cabos aqui. 🔌 Foi mal! Tenta mandar o comando de novo.",
    ],
    "ajuda_cidade_faltando": [
        "Opa, segura aí! Pra esse comando, preciso que você me diga uma cidade. Tipo assim: `/{comando} São Paulo, SP`",
    ],
    "ajuda_setdaily_primeiro": [
        "Calma lá! Antes de ativar os alertas, você precisa me dizer pra qual cidade eles são. Use o comando `/setdaily Sua Cidade` primeiro.",
    ]
}

# ===================================================================
# === FUNÇÕES AUXILIARES ===
# ===================================================================

def gerar_lookdodia(clima: dict) -> str:
    """Gera uma sugestão de roupa com base na temperatura e chuva."""
    try:
        temperatura = clima['temp']
        prob_chuva = clima['forecast'][0].get('rain_probability', 0)
        sugestao = ""

        if temperatura < 15:
            sugestao = "❄️ *Frio intenso!* Pense em casaco pesado, gorro e talvez até luvas. O importante é ficar bem aquecido!"
        elif 15 <= temperatura < 20:
            sugestao = "🧥 *Clima friozinho.* Um bom moletom ou uma jaqueta resolvem. Não saia desagasalhado(a)!"
        elif 20 <= temperatura < 24:
            sugestao = "👕 *Temperatura amena.* Uma blusa de manga comprida ou uma camiseta com uma jaqueta leve por cima é perfeito."
        else:
            sugestao = "☀️ *Calor!* Hora de usar roupas leves, como camiseta, regata e bermuda. Não esqueça o protetor solar!"

        if prob_chuva >= 60:
            sugestao += "\n\n*E atenção:* ☂️ Parece que vem chuva por aí, então um calçado impermeável e um guarda-chuva são essenciais!"
        
        return sugestao
    except (KeyError, IndexError):
        return "Não consegui gerar uma sugestão de look, os dados do clima vieram incompletos."

def formatar_previsao(clima: dict, com_alerta_chuva=True) -> str:
    """Formata os dados do clima, adicionando um aviso especial para chuva."""
    try:
        dia = clima['forecast'][0]
        aviso_chuva = ""

        if com_alerta_chuva:
            probabilidade_chuva = dia.get('rain_probability', 0)
            if probabilidade_chuva >= 60:
                frase_chuva = random.choice([
                    "É bom levar o guarda-chuva! ☂️",
                    "Parece que vem água por aí! 🌧️",
                    "Dia de maratonar séries? Talvez! 📺",
                ])
                aviso_chuva = f"\n\n⚠️ *Alerta de Chuva: {probabilidade_chuva}% de chance.*\n_{frase_chuva}_"

        texto = f"📍 Cidade: {clima['city_name']}"
        texto += f"\n🌡️ Temp. Máx/Mín: {dia['max']}°C / {dia['min']}°C"
        texto += f"\n📝 Condição: {dia['description']}"
        texto += f"\n💨 Umidade: {clima['humidity']}%"
        texto += f"\n💡 Agora: {clima['description']} ({clima['temp']}°C)"
        texto += aviso_chuva
        
        return texto
        
    except (KeyError, IndexError) as e:
        logger.error(f"Erro ao formatar previsão: Faltando dados da API. Detalhes: {e}")
        return "Não foi possível formatar a previsão do tempo devido a dados incompletos."

async def obter_clima_atual(cidade_usuario: str) -> dict | None:
    """Busca os dados de clima da API de forma assíncrona."""
    url = f"https://api.hgbrasil.com/weather?key={API_HG}&city_name={cidade_usuario}"
    try:
        async with httpx.AsyncClient( ) as client:
            resposta = await client.get(url, timeout=10)
            resposta.raise_for_status()
            dados = resposta.json()
        if dados.get('results'):
            return dados['results']
        return None
    except (httpx.RequestError, json.JSONDecodeError ) as e:
        logger.error(f"ERRO ao acessar API com httpx: {e}" )
        return None

def carregar_dados() -> dict:
    if os.path.exists(ARQUIVO_USUARIOS):
        with open(ARQUIVO_USUARIOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def salvar_dados(dados: dict):
    with open(ARQUIVO_USUARIOS, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4)

# ===================================================================
# === TAREFAS AGENDADAS ===
# ===================================================================

async def enviar_previsao_diaria(context: ContextTypes.DEFAULT_TYPE):
    """Função do /daily, agora com a sugestão de look."""
    chat_id = context.job.data["chat_id"]
    periodo = context.job.data["periodo"]
    logger.info(f"JOB: Executando /daily '{periodo}' para o chat_id: {chat_id}")
    
    dados = carregar_dados()
    usuario_info = dados.get(str(chat_id))

    if usuario_info and usuario_info.get("daily_ativo") and "cidade" in usuario_info:
        cidade = usuario_info["cidade"]
        clima = await obter_clima_atual(cidade)
        if clima:
            saudacao = f"☀️ *Bom dia em {cidade}!* ☀️\n\n" if periodo == "manha" else f"🌙 *Boa noite em {cidade}!* 🌙\n\n"
            previsao_formatada = formatar_previsao(clima)
            look_do_dia = gerar_lookdodia(clima)
            
            mensagem_final = f"{saudacao}{previsao_formatada}\n\n---\n\n👕 *Sugestão de Look:*\n_{look_do_dia}_"
            
            await context.bot.send_message(chat_id=chat_id, text=mensagem_final, parse_mode="Markdown")

async def verificar_chuva_para_usuarios(context: ContextTypes.DEFAULT_TYPE):
    """Verifica a previsão de chuva para todos os usuários com o alerta ativo."""
    logger.info("JOB: Iniciando verificação de chuva para todos os usuários.")
    dados = carregar_dados()
    
    for chat_id, info in dados.items():
        if info.get("alerta_chuva_ativo") and "cidade" in info:
            agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
            ultimo_alerta_str = info.get("ultimo_alerta_chuva_ts")
            if ultimo_alerta_str:
                ultimo_alerta_ts = datetime.fromisoformat(ultimo_alerta_str)
                if agora - ultimo_alerta_ts < timedelta(hours=6):
                    continue

            clima = await obter_clima_atual(info["cidade"])
            if clima and clima.get('forecast'):
                previsao_hoje = clima['forecast'][0]
                if previsao_hoje.get('rain_probability', 0) >= 70:
                    saudacao = random.choice(FRASES["alerta_chuva_mensagem"]).format(cidade=info["cidade"])
                    previsao_formatada = formatar_previsao(clima, com_alerta_chuva=False)
                    await context.bot.send_message(chat_id=chat_id, text=f"{saudacao}\n\n{previsao_formatada}", parse_mode="Markdown")
                    dados[chat_id]["ultimo_alerta_chuva_ts"] = agora.isoformat()
                    logger.info(f"Alerta de chuva enviado para {chat_id} para a cidade {info['cidade']}")

    salvar_dados(dados)

# ===================================================================
# === COMANDOS DO BOT ===
# ===================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia uma mensagem de boas-vindas detalhada com a lista de comandos."""
    resposta = FRASES["start"][0] 
    await update.message.reply_text(resposta, parse_mode="Markdown")

async def clima(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca e exibe a previsão para a cidade informada."""
    if not context.args:
        resposta = random.choice(FRASES["ajuda_cidade_faltando"]).format(comando="clima")
        await update.message.reply_text(resposta, parse_mode="Markdown")
        return

    cidade_buscada = " ".join(context.args)
    clima_info = await obter_clima_atual(cidade_buscada)

    if clima_info:
        texto_previsao = formatar_previsao(clima_info)
        resposta = random.choice(FRASES["clima_sucesso"]).format(cidade=clima_info['city_name'], previsao=texto_previsao)
        await update.message.reply_text(resposta, parse_mode="Markdown")
    else:
        resposta = random.choice(FRASES["clima_erro"])
        await update.message.reply_text(resposta, parse_mode="Markdown")

async def setdaily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Define ou atualiza a cidade para os alertas diários."""
    chat_id = str(update.effective_chat.id)
    
    if not context.args:
        resposta = random.choice(FRASES["ajuda_cidade_faltando"]).format(comando="setdaily")
        await update.message.reply_text(resposta, parse_mode="Markdown")
        return

    cidade_buscada = " ".join(context.args)
    clima_info = await obter_clima_atual(cidade_buscada)

    if clima_info:
        dados = carregar_dados()
        if chat_id not in dados or not isinstance(dados.get(chat_id), dict):
            dados[chat_id] = {}

        cidade_correta = clima_info.get('city_name', cidade_buscada)
        dados[chat_id]['cidade'] = cidade_correta
        salvar_dados(dados)
        
        logger.info(f"Cidade para /daily definida como '{cidade_correta}' para o usuário {chat_id}")
        resposta = random.choice(FRASES["setdaily_sucesso"]).format(cidade=cidade_correta)
        await update.message.reply_text(resposta, parse_mode="Markdown")
    else:
        resposta = random.choice(FRASES["clima_erro"])
        await update.message.reply_text(resposta, parse_mode="Markdown")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa ou desativa os alertas diários."""
    chat_id = str(update.effective_chat.id)
    dados = carregar_dados()

    if chat_id not in dados or "cidade" not in dados.get(chat_id, {}):
        resposta = random.choice(FRASES["ajuda_setdaily_primeiro"])
        await update.message.reply_text(resposta, parse_mode="Markdown")
        return

    daily_ativo = dados[chat_id].get("daily_ativo", False)
    cidade_salva = dados[chat_id]['cidade']

    if daily_ativo:
        dados[chat_id]["daily_ativo"] = False
        for job in context.job_queue.get_jobs_by_name(chat_id):
            job.schedule_removal()
        salvar_dados(dados)
        resposta = random.choice(FRASES["daily_desativado"])
        await update.message.reply_text(resposta, parse_mode="Markdown")
    else:
        dados[chat_id]["daily_ativo"] = True
        fuso_horario_brasil = ZoneInfo("America/Sao_Paulo")
        horario_manha = time(hour=6, minute=30, tzinfo=fuso_horario_brasil)
        horario_noite = time(hour=20, minute=30, tzinfo=fuso_horario_brasil)
        
        context.job_queue.run_daily(enviar_previsao_diaria, time=horario_manha, name=chat_id, data={"chat_id": chat_id, "periodo": "manha"})
        context.job_queue.run_daily(enviar_previsao_diaria, time=horario_noite, name=chat_id, data={"chat_id": chat_id, "periodo": "noite"})
        salvar_dados(dados)
        resposta = random.choice(FRASES["daily_ativado"]).format(cidade=cidade_salva)
        await update.message.reply_text(resposta, parse_mode="Markdown")

async def alertachuva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa ou desativa o monitoramento de chuva para o usuário."""
    chat_id = str(update.effective_chat.id)
    dados = carregar_dados()

    if chat_id not in dados or "cidade" not in dados.get(chat_id, {}):
        await update.message.reply_text("⚠️ Você precisa definir uma cidade primeiro com o comando `/setdaily Sua Cidade`.")
        return

    alerta_ativo = dados[chat_id].get("alerta_chuva_ativo", False)
    cidade_salva = dados[chat_id]['cidade']

    if alerta_ativo:
        dados[chat_id]["alerta_chuva_ativo"] = False
        salvar_dados(dados)
        resposta = random.choice(FRASES["alerta_chuva_desativado"])
        await update.message.reply_text(resposta, parse_mode="Markdown")
    else:
        dados[chat_id]["alerta_chuva_ativo"] = True
        salvar_dados(dados)
        resposta = random.choice(FRASES["alerta_chuva_ativado"]).format(cidade=cidade_salva)
        await update.message.reply_text(resposta, parse_mode="Markdown")

async def lookdodia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia a previsão atual e uma sugestão de look."""
    chat_id = str(update.effective_chat.id)
    dados = carregar_dados()

    if chat_id not in dados or "cidade" not in dados.get(chat_id, {}):
        await update.message.reply_text("⚠️ Primeiro, preciso saber sua cidade! Use o comando `/setdaily Sua Cidade`.")
        return

    cidade_salva = dados[chat_id]['cidade']
    clima_info = await obter_clima_atual(cidade_salva)

    if clima_info:
        look_sugerido = gerar_lookdodia(clima_info)
        resposta = random.choice(FRASES["lookdodia"]).format(cidade=cidade_salva, look=look_sugerido)
        await update.message.reply_text(resposta, parse_mode="Markdown")
    else:
        await update.message.reply_text("😕 Puts, não consegui pegar os dados do clima agora pra gerar o look. Tenta de novo daqui a pouco.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Envia uma mensagem de erro genérica e humana."""
    logger.error(f"Exceção ao processar um update: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        resposta = random.choice(FRASES["erro_generico"])
        await update.effective_chat.send_message(resposta)

# ===================================================================
# === INICIALIZAÇÃO DO BOT ===
# ===================================================================

def main():
    """Inicia e executa o bot do Telegram."""
    logger.info("Iniciando o bot...")
    
    app = ApplicationBuilder().token(TOKEN_TELEGRAM).build()

    app.job_queue.run_repeating(verificar_chuva_para_usuarios, interval=timedelta(hours=3), first=10)
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clima", clima))
    app.add_handler(CommandHandler("setdaily", setdaily))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("alertachuva", alertachuva))
    app.add_handler(CommandHandler("lookdodia", lookdodia))

    logger.info("✅ Bot rodando. Pressione Ctrl+C para parar.")
    app.run_polling()

if __name__ == '__main__':
    main()
