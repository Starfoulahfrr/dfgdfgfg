import json
import pytz  
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class AdminFeatures:
    def __init__(self, users_file: str = 'data/users.json'):
        self.users_file = users_file
        self._users = self._load_users()

    def _load_users(self):
        """Charge les utilisateurs depuis le fichier"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _save_users(self):
        """Sauvegarde les utilisateurs"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self._users, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des utilisateurs : {e}")

    async def register_user(self, user):
        """Enregistre ou met à jour un utilisateur"""
        user_id = str(user.id)
        paris_tz = pytz.timezone('Europe/Paris')
        paris_time = datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(paris_tz)
        
        self._users[user_id] = {
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'last_seen': paris_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_users()

    async def handle_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Démarre le processus de diffusion"""
        try:
            # Nettoyage du contexte
            context.user_data.clear()
            
            # Stockage des IDs importants
            context.user_data['broadcast_chat_id'] = update.effective_chat.id
            
            # Message d'instruction
            message = await update.callback_query.edit_message_text(
                "📢 *Nouveau message de diffusion*\n\n"
                "Envoyez le message que vous souhaitez diffuser à tous les utilisateurs.\n"
                "Vous pouvez envoyer du texte, des photos ou des vidéos.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Annuler", callback_data="admin")
                ]])
            )
            
            # Stockage de l'ID du message pour suppression ultérieure
            context.user_data['instruction_message_id'] = message.message_id
            
            return "WAITING_BROADCAST_MESSAGE"
        except Exception as e:
            print(f"Erreur dans handle_broadcast : {e}")
            return "CHOOSING"

    async def send_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Envoie le message à tous les utilisateurs"""
        success = 0
        failed = 0
        chat_id = update.effective_chat.id
        original_message = None

        try:
            # Supprimer le message de l'utilisateur
            try:
                await update.message.delete()
                # Supprimer le message d'instruction
                if 'instruction_message_id' in context.user_data:
                    await context.bot.delete_message(
                        chat_id=chat_id,
                        message_id=context.user_data['instruction_message_id']
                    )
            except Exception as e:
                print(f"Erreur lors de la suppression du message: {e}")

            # Sauvegarder le contenu du message
            message_content = update.message.text if update.message.text else "Photo avec légende" if update.message.photo and update.message.caption else "Photo" if update.message.photo else "Message"

            # 3. Créer un nouveau message de progression
            original_message = await context.bot.send_message(
                chat_id=chat_id,
                text="📤 <b>Envoi du message en cours...</b>",
                parse_mode='HTML'
            )

            # 4. Envoi du broadcast aux utilisateurs
            admin_id = str(update.effective_user.id)
            total_users = len(self._users)
            current = 0

            for user_id in self._users.keys():
                if user_id == admin_id:
                    continue
                try:
                    if update.message.photo:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=update.message.photo[-1].file_id,
                            caption=update.message.caption,
                            caption_entities=update.message.caption_entities
                        )
                    elif update.message.text:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=update.message.text,
                            entities=update.message.entities
                        )
                    success += 1
                except Exception as e:
                    print(f"Erreur envoi à {user_id}: {e}")
                    failed += 1
    
                current += 1
                if current % 5 == 0:
                    try:
                        await original_message.edit_text(
                            f"📤 <b>Envoi en cours...</b>\n\n"
                            f"Progression : {current}/{total_users}",
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        print(f"Erreur mise à jour progression: {e}")

            # 6. Mettre à jour avec le rapport final
            report_text = (
                "✅ <b>Message diffusé avec succès !</b>\n\n"
                f"📊 <b>Rapport d'envoi :</b>\n"
                f"• Message : <i>{message_content}</i>\n"
                f"• Envois réussis : {success}\n"
                f"• Échecs : {failed}\n"
                f"• Total : {success + failed}"
            )

            await original_message.edit_text(
                text=report_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour au menu admin", callback_data="admin")
                ]])
            )

            return "CHOOSING"

        except Exception as e:
            print(f"Erreur dans send_broadcast_message: {e}")
            error_text = (
                "❌ <b>Une erreur est survenue lors de la diffusion.</b>\n\n"
                f"Messages envoyés avant l'erreur :\n"
                f"• Message : <i>{message_content if 'message_content' in locals() else 'Non disponible'}</i>\n"
                f"• Réussis : {success}\n"
                f"• Échecs : {failed}"
            )

            if original_message:
                try:
                    await original_message.edit_text(
                        text=error_text,
                        parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Retour au menu admin", callback_data="admin")
                        ]])
                    )
                except Exception as edit_error:
                    print(f"Erreur lors de l'édition du message d'erreur: {edit_error}")
            else:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=error_text,
                        parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Retour au menu admin", callback_data="admin")
                        ]])
                    )
                except Exception as send_error:
                    print(f"Erreur lors de l'envoi du message d'erreur: {send_error}")

    async def handle_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gère l'affichage des statistiques utilisateurs"""
        try:
            text = "👥 *Gestion des utilisateurs*\n\n"
            text += f"Utilisateurs enregistrés : {len(self._users)}\n\n"
    
            if self._users:
                text += "Derniers utilisateurs actifs :\n"
                for user_id, user_data in list(self._users.items())[:10]:
                    # Récupérer le username, first_name et last_name
                    username = user_data.get('username')
                    first_name = user_data.get('first_name')
                    last_name = user_data.get('last_name')
                
                    # Logique pour déterminer quel nom afficher
                    if username:
                        display_name = f"@{username}"
                    elif first_name and last_name:
                        display_name = f"{first_name} {last_name} `{user_id}`"
                    elif first_name:
                        display_name = f"{first_name} `{user_id}`"
                    elif last_name:
                        display_name = f"{last_name} `{user_id}`"
                    else:
                        display_name = f"Sans nom `{user_id}`"
                
                    # Échapper les caractères spéciaux Markdown
                    if display_name is not None:
                        display_name = display_name.replace('_', '\\_').replace('*', '\\*')
                
                    last_seen = user_data.get('last_seen', 'Jamais')
                    text += f"• {display_name} \\- Dernière activité : {last_seen}\n"
            else:
                text += "Aucun utilisateur enregistré."

            keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="admin")]]
    
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
            return "CHOOSING"
    
        except Exception as e:
            print(f"Erreur dans handle_user_management : {e}")
            try:
                text = "👥 Gestion des utilisateurs\n\n"
                text += f"Utilisateurs enregistrés : {len(self._users)}\n\n"
    
                if self._users:
                    text += "Derniers utilisateurs actifs :\n"
                    for user_id, user_data in list(self._users.items())[:10]:
                        username = user_data.get('username')
                        first_name = user_data.get('first_name')
                        last_name = user_data.get('last_name')
                    
                        if username:
                            display_name = f"@{username}"
                        elif first_name and last_name:
                            display_name = f"{first_name} {last_name} `{user_id}`"
                        elif first_name:
                            display_name = f"{first_name} `{user_id}`"
                        elif last_name:
                            display_name = f"{last_name} `{user_id}`"
                        else:
                            display_name = f"Sans nom `{user_id}`"
                        
                        last_seen = user_data.get('last_seen', 'Jamais')
                        text += f"• {display_name} - Dernière activité : {last_seen}\n"
                else:
                    text += "Aucun utilisateur enregistré."

                keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="admin")]]
    
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as e2:
                print(f"Deuxième erreur dans handle_user_management : {e2}")
                await update.callback_query.edit_message_text(
                    "Erreur lors de l'affichage des utilisateurs.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Retour", callback_data="admin")
                    ]])
                )
            return "CHOOSING"

    async def add_user_buttons(self, keyboard: list) -> list:
        """Ajoute les boutons de gestion utilisateurs au clavier admin existant"""
        try:
            keyboard.insert(-1, [InlineKeyboardButton("👥 Gérer utilisateurs", callback_data="manage_users")])
            keyboard.insert(-1, [InlineKeyboardButton("📢 Envoyer une annonce", callback_data="start_broadcast")])
        except Exception as e:
            print(f"Erreur lors de l'ajout des boutons admin : {e}")
        return keyboard