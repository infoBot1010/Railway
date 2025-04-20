from telethon import TelegramClient, events
from telethon.tl.custom import Button
import asyncio
import os

# Webserver para manter o bot online
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot está online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Suas credenciais
api_id = 24410646
api_hash = '94f34e67625502bc30c3aa29cf49fab7'
phone_number = '5581995483906'

# Sessão
session_dir = '/home/runner/workspace/replit_session'
if not os.path.exists(session_dir):
    os.makedirs(session_dir)

client = TelegramClient(f'{session_dir}/session_name', api_id, api_hash)

# IDs dos grupos
grupo_consultas_vip = 1002640635480
grupo_adm = 1002344973122

# Armazena mensagens e comandos
comandos_pendentes = {}

# Iniciar cliente
async def main():
    await client.start(phone_number)
    print("Bot conectado com sucesso!")

# Instruções
async def enviar_instrucoes(event):
    texto_instrucoes = """
👋 Seja bem-vindo ao sistema de consultas!

@consultasvip_sertao

📘 COMO USAR OS COMANDOS

/cpf 00000000000  
/email exemplo@email.com  
/telefone 11988887777  
/nome JOAO DA SILVA  
/cnpj 00000000000000  
/placa ABC1D23  
/pix JOAO DA SILVA /123456

Exemplo de pix: /pix JOAO DA SILVA /123456  
(Use os 6 dígitos do meio do CPF do dono da chave Pix)

📞 Para consultas mais detalhadas, entre em contato com o nosso suporte: @sertao_vip
    """
    await client.send_message(
        event.chat_id,
        texto_instrucoes,
        buttons=[Button.inline("Como Usar", data="comousar")]
    )

# Comando manual: /comousar
@client.on(events.NewMessage(pattern='/comousar'))
async def manual_instrucoes(event):
    await enviar_instrucoes(event)

# Encaminha comandos para ADM e salva mapeamento
@client.on(events.NewMessage(chats=grupo_consultas_vip))
async def encaminhar_para_adm(event):
    try:
        message = event.message
        sent = None

        if message.text:
            sent = await client.send_message(grupo_adm, message.text)
        elif message.media:
            sent = await client.send_file(grupo_adm, file=message.media, caption=message.text or "")

        if sent:
            comandos_pendentes[sent.id] = {
                'msg_id': message.id,
                'texto': message.text or ""
            }
            print(f"Comando registrado: ADM({sent.id}) ↔ VIP({message.id})")

    except Exception as e:
        print(f"Erro ao encaminhar comando para ADM: {e}")

# Responde no grupo VIP à mensagem original
@client.on(events.NewMessage(chats=grupo_adm))
async def encaminhar_para_consultas_vip(event):
    try:
        message = event.message
        original_info = None
        original_msg_id = None
        comando_original = ""

        if message.reply_to and message.reply_to.reply_to_msg_id:
            reply_id = message.reply_to.reply_to_msg_id
            original_info = comandos_pendentes.get(reply_id)
            if original_info:
                original_msg_id = original_info['msg_id']
                comando_original = original_info['texto']

        # Filtra conteúdo
        linhas = message.text.splitlines() if message.text else []
        linhas_filtradas = [
            linha for linha in linhas
            if all(palavra.lower() not in linha.lower() for palavra in ["clique para ver", "usuário:", "by:", "canal:"])
        ]
        texto_final = "\n".join(linhas_filtradas).strip()
        if texto_final:
            texto_final += "\n\n@consultasvip_sertao"
        else:
            texto_final = "⚠️ Nenhum dado relevante encontrado.\n\n@consultasvip_sertao"

        # Enviar em partes se necessário
        async def enviar_mensagem_em_partes(chat_id, texto, reply_to=None):
            MAX = 4096
            partes = [texto[i:i+MAX] for i in range(0, len(texto), MAX)]
            for parte in partes:
                await client.send_message(chat_id, parte, reply_to=reply_to)
                reply_to = None  # apenas a primeira parte é resposta

        # Se a resposta tem mídia
        if message.media:
            if comando_original.lower().startswith("/placa"):
                print("🔒 Mídia bloqueada para consulta /placa.")
                await client.send_message(grupo_consultas_vip, texto_final, reply_to=original_msg_id)
            else:
                try:
                    file = await client.download_media(message)
                    await client.send_file(grupo_consultas_vip, file, caption=texto_final[:1024], reply_to=original_msg_id)
                    if len(texto_final) > 1024:
                        await enviar_mensagem_em_partes(grupo_consultas_vip, texto_final[1024:], reply_to=None)
                except Exception as e:
                    print(f"Erro ao enviar mídia: {e}")
                    await client.send_message(grupo_consultas_vip, "⚠️ A resposta contém uma mídia que não pôde ser enviada.")
        else:
            await enviar_mensagem_em_partes(grupo_consultas_vip, texto_final, reply_to=original_msg_id)

    except Exception as e:
        print(f"Erro ao encaminhar resposta para Consultas_vip: {e}")

# Botão "Como usar"
@client.on(events.CallbackQuery)
async def callback(event):
    if event.data == b"comousar":
        await enviar_instrucoes(event)

# Mensagem de boas-vindas para novos membros
@client.on(events.ChatAction)
async def novo_participante(event):
    if event.user_added or event.user_joined:
        try:
            await enviar_instrucoes(event)
        except Exception as e:
            print(f"Erro ao enviar mensagem inicial: {e}")

# Manter servidor vivo para UptimeRobot
keep_alive()

# Executar bot
try:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()
except Exception as e:
    print(f"Erro na execução do bot: {e}")
