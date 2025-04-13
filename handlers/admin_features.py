import json
import pytz  
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class AdminFeatures:
    def __init__(self, users_file: str = 'data/users.json', access_codes_file: str = 'data/access_codes.json', broadcasts_file: str = 'data/broadcasts.json'):
        self.users_file = users_file
        self.access_codes_file = access_codes_file
        self.broadcasts_file = broadcasts_file
        self._users = self._load_users()
        self._access_codes = self._load_access_codes()
        self.broadcasts = self._load_broadcasts()

    def _load_access_codes(self):
        """Charge les codes d'accès depuis le fichier"""
        try:
            with open(self.access_codes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except FileNotFoundError:
            print(f"Access codes file not found: {self.access_codes_file}")
            return {"authorized_users": []}
        except json.JSONDecodeError as e:
            print(f"Error decoding access codes file: {e}")
            return {"authorized_users": []}
        except Exception as e:
            print(f"Unexpected error loading access codes: {e}")
            return {"authorized_users": []}

    def is_user_authorized(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur est autorisé"""
        # Recharger les codes d'accès à chaque vérification
        self._access_codes = self._load_access_codes()
        
        # Convertir l'ID en nombre et vérifier sa présence
        return int(user_id) in self._access_codes.get("authorized_users", [])

    def is_user_banned(self, user_id: int) -> bool:
        """Vérifie si l'utilisateur est banni"""
        self._access_codes = self._load_access_codes()
        return int(user_id) in self._access_codes.get("banned_users", [])

    def reload_access_codes(self):
        """Recharge les codes d'accès depuis le fichier"""
        self._access_codes = self._load_access_codes()
        return self._access_codes.get("authorized_users", [])

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

    def _create_message_keyboard(self):
        """Crée le clavier standard pour les messages"""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Menu Principal", callback_data="start_cmd")
        ]])

    def _load_broadcasts(self):
        """Charge les broadcasts depuis le fichier"""
        try:
            with open(self.broadcasts_file, 'r', encoding='utf-8') as f:
                broadcasts = json.load(f)
                # Vérifier et corriger la structure de chaque broadcast
                for broadcast_id, broadcast in broadcasts.items():
                    if 'message_ids' not in broadcast:
                        broadcast['message_ids'] = {}
                    # Assurer que les user_ids sont des strings
                    if 'message_ids' in broadcast:
                        broadcast['message_ids'] = {
                            str(user_id): msg_id 
                            for user_id, msg_id in broadcast['message_ids'].items()
                        }
                return broadcasts
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            print("Erreur de décodage JSON, création d'un nouveau fichier broadcasts")
            return {}

    def _save_broadcasts(self):
        """Sauvegarde les broadcasts"""
        try:
            with open(self.broadcasts_file, 'w', encoding='utf-8') as f:
                json.dump(self.broadcasts, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des broadcasts : {e}")

    def _save_access_codes(self):
        """Sauvegarde les codes d'accès"""
        try:
            with open(self.access_codes_file, 'w', encoding='utf-8') as f:
                json.dump(self._access_codes, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des codes d'accès : {e}")

    async def ban_user(self, user_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
        """Banni un utilisateur"""
        try:
            # Convertir en int si c'est un string
            user_id = int(user_id)
        
            # Retirer l'utilisateur des codes d'accès s'il y est
            if user_id in self._access_codes.get("authorized_users", []):
                self._access_codes["authorized_users"].remove(user_id)
                self._save_access_codes()

            # Ajouter l'utilisateur à la liste des bannis si elle existe, sinon la créer
            if "banned_users" not in self._access_codes:
                self._access_codes["banned_users"] = []
        
            if user_id not in self._access_codes["banned_users"]:
                self._access_codes["banned_users"].append(user_id)
                self._save_access_codes()
        
            # Si on a le context, on supprime les messages précédents
            if context and hasattr(context, 'user_data'):
                chat_id = user_id  # Le chat_id est le même que le user_id dans un chat privé
            
                # Liste des clés des messages à supprimer
                messages_to_delete = [
                    'menu_message_id',
                    'banner_message_id',
                    'category_message_id',
                    'last_product_message_id',
                    'initial_welcome_message_id'
                ]
            
                # Supprimer les messages un par un
                for message_key in messages_to_delete:
                    if message_key in context.user_data:
                        try:
                            await context.bot.delete_message(
                                chat_id=chat_id,
                                message_id=context.user_data[message_key]
                            )
                            del context.user_data[message_key]
                        except Exception as e:
                            print(f"Erreur lors de la suppression du message {message_key}: {e}")
            
                # Vider toutes les données utilisateur
                context.user_data.clear()
        
            return True
        except Exception as e:
            print(f"Erreur lors du bannissement de l'utilisateur : {e}")
            return False

    async def unban_user(self, user_id: int) -> bool:
        """Débanni un utilisateur"""
        try:
            user_id = int(user_id)
            if "banned_users" in self._access_codes and user_id in self._access_codes["banned_users"]:
                self._access_codes["banned_users"].remove(user_id)
                self._save_access_codes()
            return True
        except Exception as e:
            print(f"Erreur lors du débannissement de l'utilisateur : {e}")
            return False

    async def show_banned_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Affiche la liste des utilisateurs bannis"""
        try:
            banned_users = self._access_codes.get("banned_users", [])
        
            text = "🚫 *Utilisateurs bannis*\n\n"
        
            if not banned_users:
                text += "Aucun utilisateur banni."
                keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="manage_users")]]
            else:
                text += "Sélectionnez un utilisateur pour le débannir :\n\n"
                keyboard = []
            
                for user_id in banned_users:
                    user_data = self._users.get(str(user_id), {})
                    username = user_data.get('username')
                    first_name = user_data.get('first_name')
                    last_name = user_data.get('last_name')
                
                    if username:
                        display_name = f"@{username}"
                    elif first_name and last_name:
                        display_name = f"{first_name} {last_name}"
                    elif first_name:
                        display_name = first_name
                    elif last_name:
                        display_name = last_name
                    else:
                        display_name = f"Utilisateur {user_id}"
                
                    text += f"• {display_name} (`{user_id}`)\n"
                    keyboard.append([InlineKeyboardButton(
                        f"🔓 Débannir {display_name}",
                        callback_data=f"unban_{user_id}"
                    )])
            
                keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="manage_users")])
        
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
            return "CHOOSING"
        
        except Exception as e:
            print(f"Erreur dans show_banned_users : {e}")
            return "CHOOSING"

    async def handle_ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gère la commande /ban"""
        try:
            # Vérifier si l'utilisateur est admin
            if not self.is_user_authorized(update.effective_user.id):
                return

            # Vérifier les arguments
            args = update.message.text.split()
            if len(args) < 2:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Usage : /ban <user_id>"
                )
                await asyncio.sleep(3)
                await message.delete()
                return

            # Récupérer l'ID de l'utilisateur à bannir
            try:
                target_user_id = int(args[1])
                target_chat_id = target_user_id  # Dans Telegram, user_id = chat_id pour les conversations privées
            except ValueError:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ L'ID utilisateur doit être un nombre"
                )
                await asyncio.sleep(3)
                await message.delete()
                return

            # Supprimer tous les messages du bot pour l'utilisateur banni
            try:
                # Essayer de supprimer les derniers messages dans le chat avec l'utilisateur
                for i in range(50):  # Essayer de supprimer les 50 derniers messages
                    try:
                        await context.bot.delete_message(
                            chat_id=target_chat_id,
                            message_id=update.message.message_id - i
                        )
                    except Exception:
                        continue
            except Exception as e:
                print(f"Erreur lors de la suppression des messages: {e}")

            # Bannir l'utilisateur
            if await self.ban_user(target_user_id, context):
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"✅ Utilisateur {target_user_id} banni avec succès"
                )
            else:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Erreur lors du bannissement de l'utilisateur"
                )

            # Supprimer la commande /ban
            try:
                await update.message.delete()
            except Exception:
                pass

            await asyncio.sleep(3)
            await message.delete()

        except Exception as e:
            print(f"Erreur dans handle_ban_command: {e}")
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Une erreur est survenue"
            )
            await asyncio.sleep(3)
            await message.delete()

    async def handle_unban_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gère le débannissement depuis le callback"""
        try:
            query = update.callback_query
            user_id = int(query.data.replace("unban_", ""))
        
            if await self.unban_user(user_id):
                # Message temporaire
                confirmation = await query.edit_message_text(
                    f"✅ Utilisateur {user_id} débanni avec succès.",
                    parse_mode='Markdown'
                )
            
                # Attendre 2 secondes
                await asyncio.sleep(2)
            
                # Retourner à la liste des bannis
                await self.show_banned_users(update, context)
            else:
                await query.answer("❌ Erreur lors du débannissement.")
            
        except Exception as e:
            print(f"Erreur dans handle_unban_callback : {e}")
            await query.answer("❌ Une erreur est survenue.")

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
            context.user_data.clear()
            context.user_data['broadcast_chat_id'] = update.effective_chat.id
            
            keyboard = [
                [InlineKeyboardButton("❌ Annuler", callback_data="admin")]
            ]
            
            message = await update.callback_query.edit_message_text(
                "📢 *Nouveau message de diffusion*\n\n"
                "Envoyez le message que vous souhaitez diffuser aux utilisateurs autorisés.\n"
                "Vous pouvez envoyer du texte, des photos ou des vidéos.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data['instruction_message_id'] = message.message_id
            return "WAITING_BROADCAST_MESSAGE"
        except Exception as e:
            print(f"Erreur dans handle_broadcast : {e}")
            return "CHOOSING"

    async def manage_broadcasts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gère les annonces existantes"""
        keyboard = []
        if self.broadcasts:
            for broadcast_id, broadcast in self.broadcasts.items():
                keyboard.append([InlineKeyboardButton(
                    f"📢 {broadcast['content'][:30]}...",
                    callback_data=f"edit_broadcast_{broadcast_id}"
                )])
        
        keyboard.append([InlineKeyboardButton("➕ Nouvelle annonce", callback_data="start_broadcast")])
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="admin")])
        
        await update.callback_query.edit_message_text(
            "📢 *Gestion des annonces*\n\n"
            "Sélectionnez une annonce à modifier ou créez-en une nouvelle.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return "CHOOSING"

    async def edit_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Permet de modifier une annonce existante"""
        query = update.callback_query
        broadcast_id = query.data.replace("edit_broadcast_", "")
    
        if broadcast_id in self.broadcasts:
            broadcast = self.broadcasts[broadcast_id]
            keyboard = [
                [InlineKeyboardButton("✏️ Modifier l'annonce", callback_data=f"edit_broadcast_content_{broadcast_id}")],
                [InlineKeyboardButton("❌ Supprimer", callback_data=f"delete_broadcast_{broadcast_id}")],
                [InlineKeyboardButton("🔙 Retour", callback_data="manage_broadcasts")]
            ]
        
            await query.edit_message_text(
                f"📢 *Gestion de l'annonce*\n\n"
                f"Message actuel :\n{broadcast['content'][:200]}...",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                "❌ Cette annonce n'existe plus.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data="manage_broadcasts")
                ]])
            )
    
        return "CHOOSING"

    async def edit_broadcast_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Démarre l'édition d'une annonce"""
        query = update.callback_query
        broadcast_id = query.data.replace("edit_broadcast_content_", "")

        context.user_data['editing_broadcast_id'] = broadcast_id

        # Envoyer le message d'instruction et stocker son ID
        message = await query.edit_message_text(
            "✏️ *Modification de l'annonce*\n\n"
            "Envoyez un nouveau message (texte et/ou média) pour remplacer cette annonce.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Annuler", callback_data=f"edit_broadcast_{broadcast_id}")
            ]])
        )
    
        # Stocker l'ID du message d'instruction
        context.user_data['instruction_message_id'] = message.message_id

        return "WAITING_BROADCAST_EDIT"

    async def handle_broadcast_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Traite la modification d'une annonce"""
        try:
            broadcast_id = context.user_data.get('editing_broadcast_id')
            if not broadcast_id or broadcast_id not in self.broadcasts:
                return "CHOOSING"

            # Supprimer les messages intermédiaires
            try:
                await update.message.delete()
                if 'instruction_message_id' in context.user_data:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=context.user_data['instruction_message_id']
                    )
            except Exception as e:
                print(f"Error deleting messages: {e}")

            admin_id = update.effective_user.id
            new_content = update.message.text if update.message.text else update.message.caption if update.message.caption else "Media sans texte"
        
            # Convertir les nouvelles entités
            new_entities = None
            if update.message.entities:
                new_entities = [{'type': entity.type, 
                               'offset': entity.offset,
                               'length': entity.length} 
                              for entity in update.message.entities]
            elif update.message.caption_entities:
                new_entities = [{'type': entity.type, 
                               'offset': entity.offset,
                               'length': entity.length} 
                              for entity in update.message.caption_entities]

            broadcast = self.broadcasts[broadcast_id]
            broadcast['content'] = new_content
            broadcast['entities'] = new_entities

            success = 0
            failed = 0
            messages_updated = []
        
            # Tenter de modifier les messages existants
            for user_id, msg_id in broadcast['message_ids'].items():
                if int(user_id) == admin_id:  # Skip l'admin
                    continue
                try:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=msg_id,
                        text=new_content,
                        entities=update.message.entities,
                        reply_markup=self._create_message_keyboard()
                    )
                    success += 1
                    messages_updated.append(user_id)
                except Exception as e:
                    print(f"Error updating message for user {user_id}: {e}")
                    failed += 1

            # Pour les utilisateurs qui n'ont pas reçu le message
            for user_id in self._users.keys():
                if (str(user_id) not in messages_updated and 
                    self.is_user_authorized(int(user_id)) and 
                    int(user_id) != admin_id):  # Skip l'admin
                    try:
                        sent_msg = await context.bot.send_message(
                            chat_id=user_id,
                            text=new_content,
                            entities=update.message.entities,
                            reply_markup=self._create_message_keyboard()
                        )
                        broadcast['message_ids'][str(user_id)] = sent_msg.message_id
                        success += 1
                    except Exception as e:
                        print(f"Error sending new message to user {user_id}: {e}")
                        failed += 1

            self._save_broadcasts()

            # Créer la bannière de gestion des annonces
            keyboard = []
            if self.broadcasts:
                for b_id, broadcast in self.broadcasts.items():
                    keyboard.append([InlineKeyboardButton(
                        f"📢 {broadcast['content'][:30]}...",
                        callback_data=f"edit_broadcast_{b_id}"
                    )])
        
            keyboard.append([InlineKeyboardButton("➕ Nouvelle annonce", callback_data="start_broadcast")])
            keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="admin")])
        
            # Envoyer la nouvelle bannière avec le contenu de l'annonce
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📢 *Gestion des annonces*\n\n"
                     "Sélectionnez une annonce à modifier ou créez-en une nouvelle.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            # Message de confirmation avec le contenu
            confirmation_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Message modifié ({success} succès, {failed} échecs)\n\n"
                     f"📝 *Contenu de l'annonce :*\n{new_content}",
                parse_mode='Markdown'
            )

            # Programmer la suppression du message après 3 secondes
            async def delete_message():
                await asyncio.sleep(3)
                try:
                    await confirmation_message.delete()
                except Exception as e:
                    print(f"Error deleting confirmation message: {e}")

            asyncio.create_task(delete_message())

            return "CHOOSING"

        except Exception as e:
            print(f"Error in handle_broadcast_edit: {e}")
            return "CHOOSING"

    async def resend_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Renvoie une annonce existante"""
        query = update.callback_query
        broadcast_id = query.data.replace("resend_broadcast_", "")

        if broadcast_id not in self.broadcasts:
            await query.edit_message_text(
                "❌ Cette annonce n'existe plus.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Retour", callback_data="manage_broadcasts")
                ]])
            )
            return "CHOOSING"

        broadcast = self.broadcasts[broadcast_id]
        success = 0
        failed = 0

        progress_message = await query.edit_message_text(
            "📤 *Renvoi de l'annonce en cours...*",
            parse_mode='Markdown'
        )

        for user_id in self._users.keys():
            user_id_int = int(user_id)
            if not self.is_user_authorized(user_id_int):
                print(f"User {user_id_int} not authorized")
                continue
        
            try:
                if broadcast['type'] == 'photo' and broadcast['file_id']:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=broadcast['file_id'],
                        caption=broadcast['caption'] if broadcast['caption'] else '',
                        parse_mode='Markdown',  # Ajout du parse_mode
                        reply_markup=self._create_message_keyboard()
                    )
                else:
                    message_text = broadcast.get('content', '')
                    if not message_text:
                        print(f"No content found for broadcast {broadcast_id}")
                        continue
        
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message_text,
                        parse_mode='Markdown',  # Ajout du parse_mode
                        reply_markup=self._create_message_keyboard()
                    )
                success += 1
                print(f"Successfully sent to user {user_id}")
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")
                failed += 1

        keyboard = [
            [InlineKeyboardButton("📢 Retour aux annonces", callback_data="manage_broadcasts")],
            [InlineKeyboardButton("🔙 Menu admin", callback_data="admin")]
        ]

        await progress_message.edit_text(
            f"✅ *Annonce renvoyée !*\n\n"
            f"📊 *Rapport d'envoi :*\n"
            f"• Envois réussis : {success}\n"
            f"• Échecs : {failed}\n"
            f"• Total : {success + failed}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return "CHOOSING"

    async def delete_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Supprime une annonce"""
        query = update.callback_query
        broadcast_id = query.data.replace("delete_broadcast_", "")
        
        if broadcast_id in self.broadcasts:
            del self.broadcasts[broadcast_id]
            self._save_broadcasts()  # Sauvegarder après suppression
        await query.edit_message_text(
            "✅ *L'annonce a été supprimée avec succès !*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Retour aux annonces", callback_data="manage_broadcasts")
            ]])
        )
        
        return "CHOOSING"

    async def send_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Envoie le message aux utilisateurs autorisés"""
        success = 0
        failed = 0
        chat_id = update.effective_chat.id
        message_ids = {}  # Pour stocker les IDs des messages envoyés

        try:
            # Supprimer les messages précédents
            try:
                await update.message.delete()
                if 'instruction_message_id' in context.user_data:
                    await context.bot.delete_message(
                        chat_id=chat_id,
                        message_id=context.user_data['instruction_message_id']
                    )
            except Exception as e:
                print(f"Erreur lors de la suppression du message: {e}")

            # Enregistrer le broadcast
            broadcast_id = str(datetime.now().timestamp())
            message_content = update.message.text if update.message.text else update.message.caption if update.message.caption else "Media sans texte"
        
            # Convertir les entités en format sérialisable
            entities = None
            if update.message.entities:
                entities = [{'type': entity.type, 
                            'offset': entity.offset,
                            'length': entity.length} 
                           for entity in update.message.entities]
            elif update.message.caption_entities:
                entities = [{'type': entity.type, 
                            'offset': entity.offset,
                            'length': entity.length} 
                           for entity in update.message.caption_entities]
    
            self.broadcasts[broadcast_id] = {
                'content': message_content,
                'type': 'photo' if update.message.photo else 'text',
                'file_id': update.message.photo[-1].file_id if update.message.photo else None,
                'caption': update.message.caption if update.message.photo else None,
                'entities': entities,  # Stocker les entités converties
                'message_ids': {},
                'parse_mode': None  # On n'utilise plus parse_mode car on utilise les entités
            }

            # Message de progression
            progress_message = await context.bot.send_message(
                chat_id=chat_id,
                text="📤 <b>Envoi du message en cours...</b>",
                parse_mode='HTML'
            )

            # Envoi aux utilisateurs autorisés
            for user_id in self._users.keys():
                user_id_int = int(user_id)
                if not self.is_user_authorized(user_id_int) or user_id_int == update.effective_user.id:  # Skip non-autorisés et admin
                    print(f"User {user_id_int} skipped")
                    continue
            
                try:
                    if update.message.photo:
                        sent_msg = await context.bot.send_photo(
                            chat_id=user_id,
                            photo=update.message.photo[-1].file_id,
                            caption=update.message.caption if update.message.caption else '',
                            caption_entities=update.message.caption_entities,
                            reply_markup=self._create_message_keyboard()
                        )
                    else:
                        sent_msg = await context.bot.send_message(
                            chat_id=user_id,
                            text=message_content,
                            entities=update.message.entities,
                            reply_markup=self._create_message_keyboard()
                        )
                    self.broadcasts[broadcast_id]['message_ids'][str(user_id)] = sent_msg.message_id  # Assurer que user_id est un string
                    success += 1
                except Exception as e:
                    print(f"Error sending to user {user_id}: {e}")
                    failed += 1

            # Sauvegarder les broadcasts
            self._save_broadcasts()

            # Rapport final
            keyboard = [
                [InlineKeyboardButton("📢 Gérer les annonces", callback_data="manage_broadcasts")],
                [InlineKeyboardButton("🔙 Menu admin", callback_data="admin")]
            ]

            await progress_message.edit_text(
                f"✅ *Message envoyé avec succès !*\n\n"
                f"📊 *Rapport d'envoi :*\n"
                f"• Envois réussis : {success}\n"
                f"• Échecs : {failed}\n"
                f"• Total : {success + failed}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return "CHOOSING"

        except Exception as e:
            print(f"Erreur lors de l'envoi du broadcast : {e}")
            return "CHOOSING"

    async def handle_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gère l'affichage des statistiques utilisateurs"""
        try:
            # Récupérer la page actuelle depuis le callback_data ou initialiser à 0
            query = update.callback_query
            current_page = 0
            if query and query.data.startswith("user_page_"):
                current_page = int(query.data.replace("user_page_", ""))

            # Nombre d'utilisateurs par page
            users_per_page = 10
        
            # Récupérer les listes d'utilisateurs autorisés et bannis
            authorized_users = set(self._access_codes.get("authorized_users", []))
            banned_users = set(self._access_codes.get("banned_users", []))
        
            # Créer des listes séparées pour chaque catégorie
            authorized_list = []
            banned_list = []
            pending_list = []

            for user_id, user_data in self._users.items():
                user_id_int = int(user_id)
                if user_id_int in authorized_users:
                    authorized_list.append((user_id, user_data))
                elif user_id_int in banned_users:
                    banned_list.append((user_id, user_data))
                else:
                    pending_list.append((user_id, user_data))

            # Combiner les listes dans l'ordre : autorisés, en attente, bannis
            relevant_users = authorized_list + pending_list + banned_list

            total_pages = (len(relevant_users) + users_per_page - 1) // users_per_page

            # Calculer les indices de début et de fin pour la page actuelle
            start_idx = current_page * users_per_page
            end_idx = min(start_idx + users_per_page, len(relevant_users))

            # Construire le texte
            text = "👥 *Gestion des utilisateurs*\n\n"
            text += f"✅ Utilisateurs autorisés : {len(authorized_users)}\n"
            text += f"⏳ Utilisateurs en attente : {len(pending_list)}\n"
            text += f"🚫 Utilisateurs bannis : {len(banned_users)}\n"
            if total_pages > 1:
                text += f"Page {current_page + 1}/{total_pages}\n"
            text += "\n"

            if relevant_users:
                for user_id, user_data in relevant_users[start_idx:end_idx]:
                    user_id_int = int(user_id)
                    # Format de la date
                    last_seen = user_data.get('last_seen', 'Jamais')
                    try:
                        dt = datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S")
                        last_seen = dt.strftime("%d/%m/%Y %H:%M")
                    except:
                        pass

                    # Construire le nom d'affichage
                    username = user_data.get('username')
                    first_name = user_data.get('first_name')
                    last_name = user_data.get('last_name')
                
                    if username:
                        display_name = f"@{username}"
                    elif first_name and last_name:
                        display_name = f"{first_name} {last_name}"
                    elif first_name:
                        display_name = first_name
                    elif last_name:
                        display_name = last_name
                    else:
                        display_name = "Sans nom"

                    # Échapper les caractères spéciaux Markdown
                    display_name = display_name.replace('_', '\\_').replace('*', '\\*')
                
                    # Déterminer le statut
                    if user_id_int in banned_users:
                        status = "🚫"
                    elif user_id_int in authorized_users:
                        status = "✅"
                    else:
                        status = "⏳"
                
                    text += f"{status} {display_name} (`{user_id}`)\n"
                    text += f"  └ Dernière activité : {last_seen}\n"
            else:
                text += "Aucun utilisateur enregistré."

            # Construire le clavier avec la pagination
            keyboard = []
        
            # Boutons de pagination
            if total_pages > 1:
                nav_buttons = []
            
                # Bouton page précédente
                if current_page > 0:
                    nav_buttons.append(InlineKeyboardButton(
                        "◀️", callback_data=f"user_page_{current_page - 1}"))
            
                # Bouton page actuelle
                nav_buttons.append(InlineKeyboardButton(
                    f"{current_page + 1}/{total_pages}", callback_data="current_page"))
            
                # Bouton page suivante
                if current_page < total_pages - 1:
                    nav_buttons.append(InlineKeyboardButton(
                        "▶️", callback_data=f"user_page_{current_page + 1}"))
            
                keyboard.append(nav_buttons)

            # Autres boutons
            keyboard.extend([
                [InlineKeyboardButton("🚫 Utilisateurs bannis", callback_data="show_banned")],
                [InlineKeyboardButton("🔙 Retour", callback_data="admin")]
            ])

            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

            return "CHOOSING"

        except Exception as e:
            print(f"Erreur dans handle_user_management : {e}")
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
        except Exception as e:
            print(f"Erreur lors de l'ajout des boutons admin : {e}")
        return keyboard