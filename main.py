import telebot
import re
import os
import threading
from datetime import datetime
import time

# === CONFIG ===
TOKEN = '7606174520:AAEir7Zw-ohhdHJO1nkketC9MC3EEahZtdA'
bot = telebot.TeleBot(TOKEN)
DOSSIER = "."
LOG_FILE = "historique_recherches.log"
chat_id_global = None

# === EXTRACTION FICHE ===
def extraire_infos_none(fiche):
    fiche_texte = fiche.upper()
    infos = {}
    phones = re.findall(r"\b0?[67]\d{8}\b", fiche_texte)
    infos['Téléphone'] = phones[0] if phones else "NONE"
    emails = re.findall(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", fiche, re.IGNORECASE)
    infos['Email'] = emails[0] if emails else "NONE"
    ibans = re.findall(r"\bFR\d{2}\d{23}\b", fiche_texte)
    infos['IBAN'] = ibans[0] if ibans else "NONE"

    date = re.search(r"\b\d{4}-\d{2}-\d{2}", fiche)
    infos["Date de naissance"] = date.group() if date else "NONE"

    adresse_match = re.search(r"\d+\s+[^,]+", fiche)
    cp_match = re.search(r"\b\d{5}\b", fiche)
    infos["Adresse"] = adresse_match.group().title() if adresse_match else "NONE"
    infos["Code postal"] = cp_match.group() if cp_match else "NONE"

    nom_prenom = fiche.split(",")
    if len(nom_prenom) >= 2:
        infos["Nom"] = nom_prenom[1].strip().title()
        infos["Prénom"] = nom_prenom[0].strip().title()
    else:
        infos["Nom"] = "NONE"
        infos["Prénom"] = "NONE"
    return infos if infos['Téléphone'] != "NONE" else None

# === RECHERCHE FICHE ===
def chercher_fiche(numero):
    numero = numero.replace(" ", "").replace("+33", "0").strip()
    variantes = {numero, numero[1:], "+33" + numero[1:]} if numero.startswith("0") else {numero}
    for fichier in os.listdir(DOSSIER):
        if fichier.endswith(".txt"):
            try:
                with open(os.path.join(DOSSIER, fichier), "r", encoding="utf-8") as f:
                    for ligne in f:
                        if any(variant in ligne for variant in variantes):
                            infos = extraire_infos_none(ligne)
                            return (infos or ligne.strip()), fichier
            except: pass
    return None, None

# === LOG HISTO ===
def log_recherche(username, numero, infos):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nom = infos.get("Nom", "NONE")
    prenom = infos.get("Prénom", "NONE")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{numero} | {now} | @{username} | {nom} {prenom}\n")

def historique_recherches(numero):
    if not os.path.exists(LOG_FILE):
        return None
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lignes = f.readlines()
    recherches = []
    for ligne in lignes:
        if ligne.startswith(numero):
            _, date, utilisateur, personne = ligne.strip().split(" | ")
            recherches.append(f"• {date} par {utilisateur} ({personne})")
    return "\n".join(recherches) if recherches else None

# === COMMANDES ===
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "👋 Bienvenue ! Utilise /num <numéro> pour rechercher une fiche.")

@bot.message_handler(commands=['num'])
def handle_num(message):
    args = message.text.split()
    if len(args) != 2:
        return bot.reply_to(message, "Utilisation : /num 06XXXXXXXX")
    numero = args[1]
    user = message.from_user.username or f"id_{message.from_user.id}"
    loading_msg = bot.send_message(message.chat.id, "🔍 Recherche en cours...")
    time.sleep(1)
    bot.edit_message_text("🔍 Recherche en cours...\n▌", message.chat.id, loading_msg.message_id)
    time.sleep(1)
    bot.edit_message_text("🔍 Recherche en cours...\n██", message.chat.id, loading_msg.message_id)
    time.sleep(1)
    bot.edit_message_text("🔍 Recherche en cours...\n█████", message.chat.id, loading_msg.message_id)
    fiche, fichier = chercher_fiche(numero)
    if fiche:
        bot.delete_message(message.chat.id, loading_msg.message_id)
        if isinstance(fiche, dict):
            log_recherche(user, numero, fiche)
        caption = f"📂 <b>Fichier :</b> {fichier}\n\n"
        champs = {"Nom": "🧑‍🦱", "Prénom": "🧑‍🦰", "Téléphone": "📞", "Email": "📧", "Adresse": "🏡", "Code postal": "📮", "Date de naissance": "🎂", "IBAN": "💳"}
        for k, v in fiche.items():
            if k in champs:
                caption += f"{champs[k]} <b>{k}</b> : {v}\n"
        caption += "\n🔐 <i>Powered by Monsieur Fiche 💼</i>"
        historique = historique_recherches(numero)
        if historique:
            caption += f"\n\n📜 <b>Historique des recherches :</b>\n{historique}"
        with open("found.jpeg", "rb") as photo:
            bot.send_photo(message.chat.id, photo, caption=caption, parse_mode="HTML")
        msg = bot.send_message(message.chat.id, "😏 Ah oui, j'allais oublier... vous êtes surveillés 😉")
        time.sleep(3)
        bot.delete_message(message.chat.id, msg.message_id)
    else:
        bot.edit_message_text("❌ Aucune fiche trouvée pour ce numéro.", message.chat.id, loading_msg.message_id)
        with open("notfound.jpeg", "rb") as photo:
            bot.send_photo(message.chat.id, photo)

# === SURVEILLANCE CHAT ID ===
@bot.message_handler(func=lambda m: True)
def set_chat_id(m):
    global chat_id_global
    if chat_id_global is None:
        chat_id_global = m.chat.id

print("Bot lancé. En attente de commandes...")
bot.infinity_polling()
