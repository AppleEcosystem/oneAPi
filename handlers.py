import re
import base64
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaDocument
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from api_client import OneBotAPIClient
from keyboards import (
    get_main_menu_keyboard, 
    get_plans_keyboard, 
    get_back_keyboard,
    get_settings_keyboard,
    get_certificate_keyboard,
    get_udid_input_keyboard,
    get_key_plans_keyboard,
    get_ipa_management_keyboard,
    get_ipa_actions_keyboard
)
from languages import lang_manager
from config import PLANS, is_admin
from ipa_manager import IPAManager
from r2_storage import R2Storage
from url_shortener import URLShortener

router = Router()

class BotStates(StatesGroup):
    waiting_for_udid = State()
    waiting_for_api_key = State()
    waiting_for_search = State()
    waiting_for_p12_thumbnail = State()
    waiting_for_mp_thumbnail = State()
    waiting_for_key_quantity = State()
    waiting_for_key_code = State()
    waiting_for_key_udid = State()
    waiting_for_ipa_file = State()

def get_text(key: str, **kwargs) -> str:
    """Get localized text"""
    return lang_manager.get_text(key, **kwargs)

def format_date(date_string: str) -> str:
    """Format date to DD/MM/YYYY"""
    try:
        # Try to parse different date formats
        if 'T' in date_string:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%d/%m/%Y')
    except:
        return date_string

def determine_status(api_response: dict) -> str:
    """Determine status based on API response - improved logic"""
    # Get mobileprovision and p12 data
    mobileprovision = api_response.get('mobileprovision', '')
    p12 = api_response.get('p12', '')
    
    # Check if mobileprovision has actual data
    has_mobileprovision = (
        mobileprovision and 
        mobileprovision.strip() and 
        mobileprovision != 'null' and 
        mobileprovision != '' and
        len(mobileprovision.strip()) > 10  # Base64 data should be longer
    )
    
    # Check if p12 has actual data
    has_p12 = (
        p12 and 
        p12.strip() and 
        p12 != 'null' and 
        p12 != '' and
        len(p12.strip()) > 10  # Base64 data should be longer
    )
    
    # If both exist with actual data, it's active
    if has_p12 and has_mobileprovision:
        return 'active'
    # If only p12 exists or mobileprovision is missing/empty, it's processing
    elif has_p12 and not has_mobileprovision:
        return 'processing'
    # Default to processing for safety
    else:
        return 'processing'

@router.message(Command("start"))
async def start_command(message: Message, db, config):
    """Handle /start command"""
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await db.save_user(message.from_user.id, message.from_user.username)
        user = {"api_key": None}
    
    registrations = await db.get_user_registrations(message.from_user.id)
    
    # Only show balance and device info to admin
    if is_admin(message.from_user.id):
        if user.get("api_key"):
            try:
                api_client = OneBotAPIClient(config.API_BASE_URL)
                balance = await api_client.get_balance(user["api_key"])
                # No need to close since we're using context managers now
                
                text = get_text("welcome", balance=balance, devices=len(registrations))
            except:
                text = get_text("welcome_no_balance", devices=len(registrations))
        else:
            text = get_text("welcome_no_api", devices=len(registrations))
    else:
        # Normal users get simple welcome message without sensitive info
        text = get_text("welcome_normal_user")
    
    await message.answer(text, reply_markup=get_main_menu_keyboard(message.from_user.id))

@router.callback_query(F.data == "register")
async def start_registration(callback: CallbackQuery, state: FSMContext, db):
    """Start UDID registration - show plans first (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    user = await db.get_user(callback.from_user.id)
    
    if not user or not user.get("api_key"):
        await callback.answer(get_text("api_key_required"), show_alert=True)
        return
    
    await callback.message.edit_text(
        get_text("select_plan_first"),
        reply_markup=get_plans_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("plan_"))
async def process_plan_selection_first(callback: CallbackQuery, state: FSMContext):
    """Process plan selection and ask for UDID (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    plan = callback.data.replace("plan_", "")
    await state.update_data(plan=plan)
    
    await callback.message.edit_text(
        get_text("register_udid_after_plan", plan=plan),
        reply_markup=get_udid_input_keyboard()
    )
    await state.set_state(BotStates.waiting_for_udid)
    await callback.answer()

@router.message(StateFilter(BotStates.waiting_for_udid))
async def process_udid(message: Message, state: FSMContext, db, config):
    """Process UDID input and register (admin only)"""
    if not is_admin(message.from_user.id):
        await message.answer("Access denied!")
        return
        
    udid = message.text.strip().upper()
    
    if not re.match(r'^[0-9A-F]{8}-[0-9A-F]{16}$', udid):
        await message.answer(
            get_text("invalid_udid"),
            reply_markup=get_back_keyboard()
        )
        return
    
    data = await state.get_data()
    plan = data.get("plan")
    user = await db.get_user(message.from_user.id)
    
    # Add electric reaction to the UDID message
    await message.react([{"type": "emoji", "emoji": "⚡"}])
    
    try:
        api_client = OneBotAPIClient(config.API_BASE_URL)
        result = await api_client.register_udid(user["api_key"], udid, plan)
        
        # Always fetch the latest certificate data for accurate status
        try:
            certificates = await api_client.get_certificate(user["api_key"], udid=udid)
            if certificates:
                cert_data = certificates[0]
                # Use certificate data for status determination (most accurate)
                status = determine_status(cert_data)
                # Save complete certificate data
                await db.save_certificate(
                    message.from_user.id,
                    udid,
                    cert_data.get("id", ""),
                    cert_data
                )
                # Use name from certificate data if available
                name = cert_data.get('name', result.get('name', 'N/A'))
            else:
                # Fallback to registration response
                status = determine_status(result)
                name = result.get('name', 'N/A')
        except:
            # Fallback to registration response
            status = determine_status(result)
            name = result.get('name', 'N/A')
        
        await db.save_registration(
            message.from_user.id,
            udid,
            result.get("certificate_id", ""),
            plan,
            result,
            status
        )
        
        # No need to close since we're using context managers now
        
        status_emoji = "🟡" if status == "processing" else "🟢"
        
        # Format registration success with clean info
        current_date = datetime.now().strftime('%d/%m/%Y')
        success_text = get_text("registration_success", 
            udid=udid, 
            date=current_date, 
            status=get_text(f"status_{status.lower()}"), 
            emoji=status_emoji, 
            name=name
        )
        
        await message.answer(
            success_text,
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await message.answer(
            get_text("registration_failed", error=str(e)),
            reply_markup=get_back_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "search")
async def start_search(callback: CallbackQuery, state: FSMContext, db):
    """Start search"""
    user = await db.get_user(callback.from_user.id)
    
    if not user or not user.get("api_key"):
        await callback.answer(get_text("api_key_required"), show_alert=True)
        return
    
    await callback.message.edit_text(
        get_text("search"),
        reply_markup=get_back_keyboard()
    )
    await state.set_state(BotStates.waiting_for_search)
    await callback.answer()

@router.message(StateFilter(BotStates.waiting_for_search))
async def process_search(message: Message, state: FSMContext, db, config):
    """Process search query"""
    query = message.text.strip()
    user = await db.get_user(message.from_user.id)
    
    try:
        api_client = OneBotAPIClient(config.API_BASE_URL)
        
        # Try search by UDID first, then by certificate ID
        results = []
        try:
            certs = await api_client.get_certificate(user["api_key"], udid=query)
            results.extend(certs)
        except:
            pass
        
        if not results:
            try:
                certs = await api_client.get_certificate(user["api_key"], certificate_id=query)
                results.extend(certs)
            except:
                pass
        
        # No need to close since we're using context managers now
        
        if results:
            cert_data = results[0]
            udid = cert_data.get('udid', 'N/A')
            
            # Save certificate data to database
            await db.save_certificate(
                message.from_user.id,
                udid,
                cert_data.get("id", ""),
                cert_data
            )
            
            # Check if this UDID is already registered in our database
            registration = await db.get_registration_by_udid(message.from_user.id, udid)
            
            # If not registered, create a registration entry from the search result
            if not registration:
                # Determine the plan from certificate data (fallback to 'unknown' if not available)
                plan = cert_data.get('plan', 'unknown')
                
                # Determine status from current API response
                current_status = determine_status(cert_data)
                
                # Save as registration so user can download certificates
                await db.save_registration(
                    message.from_user.id,
                    udid,
                    cert_data.get("id", ""),
                    plan,
                    cert_data,  # Use cert_data as api_response
                    current_status
                )
                
                enabled = True  # New registrations are enabled by default
            else:
                enabled = registration['enabled']
                # Determine status from current API response (most accurate)
                current_status = determine_status(cert_data)
                
                # Update database status if it exists and has changed
                if registration['status'] != current_status:
                    await db.update_registration_status(udid, current_status)
            
            status_emoji = "🟡" if current_status == "processing" else "🟢"
            
            # Format clean search results
            added_date = format_date(cert_data.get('created_at', cert_data.get('date', datetime.now().isoformat())))
            
            search_result = get_text("search_result",
                udid=udid,
                date=added_date,
                status=get_text(f"status_{current_status.lower()}"),
                emoji=status_emoji,
                name=cert_data.get('name', 'N/A')
            )
            
            await message.answer(
                search_result,
                reply_markup=get_certificate_keyboard(udid, enabled, current_status, message.from_user.id)
            )
        else:
            await message.answer(
                get_text("no_search_results", query=query),
                reply_markup=get_back_keyboard()
            )
    
    except Exception as e:
        await message.answer(
            get_text("registration_failed", error=str(e)),
            reply_markup=get_back_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_certificate(callback: CallbackQuery, db, config):
    """Toggle certificate enabled/disabled status (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    udid = callback.data.replace("toggle_", "")
    user = await db.get_user(callback.from_user.id)
    
    # Toggle the status
    new_enabled = await db.toggle_registration_enabled(callback.from_user.id, udid)
    
    # Get updated certificate data
    try:
        api_client = OneBotAPIClient(config.API_BASE_URL)
        certificates = await api_client.get_certificate(user["api_key"], udid=udid)
        # No need to close since we're using context managers now
        
        if certificates:
            cert_data = certificates[0]
            current_status = determine_status(cert_data)
            status_emoji = "🟡" if current_status == "processing" else "🟢"
            status_text = "Processing" if current_status == "processing" else "Active"
            
            # Format search results
            added_date = format_date(cert_data.get('created_at', cert_data.get('date', datetime.now().isoformat())))
            
            search_result = f"""UDID : {udid}
Added on : {added_date}
Status: {status_text} {status_emoji}
Name : {cert_data.get('name', 'N/A')}"""
            
            await callback.message.edit_text(
                search_result,
                reply_markup=get_certificate_keyboard(udid, new_enabled, current_status, callback.from_user.id)
            )
    except Exception as e:
        await callback.answer(get_text("error_updating_status", error=str(e)), show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data.startswith("download_cert_"))
async def download_certificate(callback: CallbackQuery, db, config):
    """Download certificate files"""
    udid = callback.data.replace("download_cert_", "")
    user = await db.get_user(callback.from_user.id)
    
    # Check if certificate is enabled
    registration = await db.get_registration_by_udid(callback.from_user.id, udid)
    if not registration or not registration['enabled']:
        await callback.answer(get_text("certificate_disabled"), show_alert=True)
        return
    
    try:
        api_client = OneBotAPIClient(config.API_BASE_URL)
        certificates = await api_client.get_certificate(user["api_key"], udid=udid)
        # No need to close since we're using context managers now
        
        if not certificates:
            await callback.answer(get_text("certificate_not_found"), show_alert=True)
            return
        
        cert_data = certificates[0]
        
        # Double check status before allowing download
        current_status = determine_status(cert_data)
        if current_status == "processing":
            await callback.answer(get_text("certificate_processing"), show_alert=True)
            return
        
        # Get global thumbnails (now base64 data)
        thumbnails = await db.get_global_thumbnails()
        
        # Prepare files to send together as media group
        media_group = []
        
        # Add P12 file (no caption, with thumbnail if available)
        if cert_data.get('p12'):
            try:
                p12_data = base64.b64decode(cert_data['p12'])
                p12_file = BufferedInputFile(p12_data, filename=f"{udid}.p12")
                
                # Use base64 thumbnail data directly
                if thumbnails and thumbnails.get('p12_thumbnail'):
                    thumbnail_data = base64.b64decode(thumbnails['p12_thumbnail'])
                    thumbnail_input = BufferedInputFile(thumbnail_data, filename="thumb.jpg")
                    media_group.append(InputMediaDocument(media=p12_file, thumbnail=thumbnail_input))
                else:
                    media_group.append(InputMediaDocument(media=p12_file))
            except Exception as e:
                await callback.message.answer(get_text("error_preparing_p12", error=str(e)))

        # Add mobileprovision file (password caption, with thumbnail if available)
        if cert_data.get('mobileprovision') and cert_data.get('mobileprovision').strip():
            try:
                mp_data = base64.b64decode(cert_data['mobileprovision'])
                mp_file = BufferedInputFile(mp_data, filename=f"{udid}.mobileprovision")
                
                # Fix HTML parsing error - escape the password properly
                password = cert_data.get('p12_password', '1')
                caption = f"{get_text('certificate_password', password=password)}"
                
                # Use base64 thumbnail data directly
                if thumbnails and thumbnails.get('mobileprovision_thumbnail'):
                    thumbnail_data = base64.b64decode(thumbnails['mobileprovision_thumbnail'])
                    thumbnail_input = BufferedInputFile(thumbnail_data, filename="thumb.jpg")
                    media_group.append(InputMediaDocument(
                        media=mp_file,
                        caption=caption,
                        thumbnail=thumbnail_input
                    ))
                else:
                    media_group.append(InputMediaDocument(
                        media=mp_file,
                        caption=caption
                    ))
            except Exception as e:
                await callback.message.answer(get_text("certificate_file_error", file_type="mobileprovision", error=str(e)))

        # Send both files together as media group
        if media_group:
            try:
                await callback.message.answer_media_group(media_group)
            except Exception as e:
                # Fallback: send files separately if media group fails
                await callback.message.answer(get_text("certificate_group_error", error=str(e)))
                
                # Send P12 file individually
                if cert_data.get('p12'):
                    try:
                        p12_data = base64.b64decode(cert_data['p12'])
                        p12_file = BufferedInputFile(p12_data, filename=f"{udid}.p12")
                        await callback.message.answer_document(p12_file)
                    except Exception as e:
                        await callback.message.answer(get_text("certificate_file_error", file_type="P12", error=str(e)))
                
                # Send mobileprovision file individually
                if cert_data.get('mobileprovision') and cert_data.get('mobileprovision').strip():
                    try:
                        mp_data = base64.b64decode(cert_data['mobileprovision'])
                        mp_file = BufferedInputFile(mp_data, filename=f"{udid}.mobileprovision")
                        password = cert_data.get('p12_password', '1')
                        await callback.message.answer_document(
                            mp_file, 
                            caption=get_text("certificate_password", password=password)
                        )
                    except Exception as e:
                        await callback.message.answer(get_text("certificate_file_error", file_type="mobileprovision", error=str(e)))
        else:
            await callback.answer(get_text("certificate_no_files"), show_alert=True)
            
    except Exception as e:
        await callback.answer(get_text("certificate_download_error", error=str(e)), show_alert=True)
    
    # Sign all unsigned IPAs for this user and show install buttons
    try:
        unsigned_ipas = await db.get_unsigned_ipas(callback.from_user.id)
        if unsigned_ipas:
            ipa_manager = IPAManager()
            
            # Get certificate data for signing
            p12_data = base64.b64decode(cert_data['p12'])
            mobileprovision_data = base64.b64decode(cert_data['mobileprovision'])
            
            signed_count = await ipa_manager.sign_all_user_ipas(
                unsigned_ipas, p12_data, mobileprovision_data, db
            )
        
        # Show install buttons for all signed IPAs
        signed_ipas = await db.get_signed_ipas(callback.from_user.id)
        if signed_ipas:
            # Create install buttons with pre-shortened URLs
            builder = InlineKeyboardBuilder()
            url_shortener = URLShortener()
            
            # Add install buttons in rows of 2
            for i in range(0, len(signed_ipas), 2):
                row_ipas = signed_ipas[i:i+2]
                row_buttons = []
                
                for ipa in row_ipas:
                    app_name = ipa['app_name'] if ipa['app_name'] != 'Unknown' else ipa['original_filename'].replace('.ipa', '')
                    
                    # Pre-shorten the URL in the backend
                    short_url = await url_shortener.shorten_install_url(ipa['install_url'])
                    
                    row_buttons.append(
                        InlineKeyboardButton(
                            text=f"📱 {app_name}",
                            url=short_url  # Use pre-shortened URL directly
                        )
                    )
                
                builder.row(*row_buttons)
            
            # No back button as requested
            install_text = get_text("certificate_signed_message", udid=udid)
            
            await callback.message.answer(
                install_text,
                reply_markup=builder.as_markup()
            )

    except Exception as e:
        pass
    
    await callback.answer()

@router.callback_query(F.data.startswith("install_ipa_"))
async def get_install_link(callback: CallbackQuery, db):
    """Get install link for specific IPA - This handler is now unused since buttons go directly to URLs"""
    ipa_id = int(callback.data.replace("install_ipa_", ""))
    ipa = await db.get_ipa_by_id(ipa_id)
    
    if not ipa or ipa['user_id'] != callback.from_user.id:
        await callback.answer(get_text("ipa_not_found"), show_alert=True)
        return
    
    if not ipa['install_url']:
        await callback.answer(get_text("ipa_not_signed"), show_alert=True)
        return
    
    app_name = ipa['app_name'] if ipa['app_name'] != 'Unknown' else ipa['original_filename'].replace('.ipa', '')
    
    # Show processing message
    processing_msg = await callback.message.edit_text(get_text("ipa_preparing_link"))
    
    try:
        # Shorten the install URL
        url_shortener = URLShortener()
        short_install_url = await url_shortener.shorten_install_url(ipa['install_url'])
        
        # Create inline keyboard with only install button (no back button)
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=get_text("ipa_install_button", app_name=app_name),
                url=short_install_url
            )
        )
        
        # Simple message with just the app name
        text = get_text("ipa_install_message", app_name=app_name)
        
        await processing_msg.edit_text(text, reply_markup=builder.as_markup())
        
    except Exception as e:
        # Fallback to original URL if shortening fails
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=get_text("ipa_install_button", app_name=app_name),
                url=ipa['install_url']
            )
        )
        
        text = get_text("ipa_install_message", app_name=app_name)
        
        await processing_msg.edit_text(text, reply_markup=builder.as_markup())
    
    await callback.answer()

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, db):
    """Show settings (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    user = await db.get_user(callback.from_user.id)
    
    # Get thumbnail status
    thumbnails = await db.get_thumbnails(callback.from_user.id)
    
    settings_text = get_text("settings",
        api_status=get_text("status_set") if user and user.get("api_key") else get_text("status_not_set"),
        p12_status=get_text("status_set") if thumbnails and thumbnails.get('p12_thumbnail') else get_text("status_not_set"),
        mp_status=get_text("status_set") if thumbnails and thumbnails.get('mobileprovision_thumbnail') else get_text("status_not_set")
    )
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "set_api_key")
async def set_api_key(callback: CallbackQuery, state: FSMContext):
    """Start API key setting (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    await callback.message.edit_text(
        get_text("set_api_key"),
        reply_markup=get_back_keyboard()
    )
    await state.set_state(BotStates.waiting_for_api_key)
    await callback.answer()

@router.message(StateFilter(BotStates.waiting_for_api_key))
async def process_api_key(message: Message, state: FSMContext, db, config):
    """Process API key (admin only)"""
    if not is_admin(message.from_user.id):
        await message.answer("Access denied!")
        return
        
    api_key = message.text.strip()
    
    try:
        api_client = OneBotAPIClient(config.API_BASE_URL)
        balance = await api_client.get_balance(api_key)
        # No need to close since we're using context managers now
        
        await db.save_user(message.from_user.id, message.from_user.username, api_key)
        
        await message.answer(
            get_text("api_key_success", balance=balance),
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await message.answer(
            get_text("api_key_invalid", error=str(e)),
            reply_markup=get_back_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "set_thumbnails")
async def set_thumbnails_start(callback: CallbackQuery, state: FSMContext):
    """Start thumbnail setting process (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    await callback.message.edit_text(
        get_text("set_thumbnails_start"),
        reply_markup=get_back_keyboard()
    )
    await state.set_state(BotStates.waiting_for_p12_thumbnail)
    await callback.answer()

@router.message(StateFilter(BotStates.waiting_for_p12_thumbnail))
async def process_p12_thumbnail(message: Message, state: FSMContext, db):
    """Process P12 thumbnail image (admin only)"""
    if not is_admin(message.from_user.id):
        await message.answer("Access denied!")
        return
        
    if not message.photo:
        await message.answer(
            get_text("thumbnail_error"),
            reply_markup=get_back_keyboard()
        )
        return
    
    try:
        # Get the largest photo size and download it
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_data = await message.bot.download_file(file.file_path)
        
        # Convert to base64
        thumbnail_base64 = base64.b64encode(file_data.read()).decode('utf-8')
        
        # Save P12 thumbnail as base64
        await db.save_thumbnails(message.from_user.id, p12_thumbnail_data=thumbnail_base64)
        
        # Now ask for mobileprovision thumbnail
        await message.answer(
            get_text("p12_thumbnail_success"),
            reply_markup=get_back_keyboard()
        )
        await state.set_state(BotStates.waiting_for_mp_thumbnail)
        
    except Exception as e:
        await message.answer(
            get_text("thumbnail_save_error", type="P12", error=str(e)),
            reply_markup=get_back_keyboard()
        )
        await state.clear()

@router.message(StateFilter(BotStates.waiting_for_mp_thumbnail))
async def process_mp_thumbnail(message: Message, state: FSMContext, db):
    """Process mobileprovision thumbnail image (admin only)"""
    if not is_admin(message.from_user.id):
        await message.answer("Access denied!")
        return
        
    if not message.photo:
        await message.answer(
            get_text("thumbnail_error"),
            reply_markup=get_back_keyboard()
        )
        return
    
    try:
        # Get the largest photo size and download it
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_data = await message.bot.download_file(file.file_path)
        
        # Convert to base64
        thumbnail_base64 = base64.b64encode(file_data.read()).decode('utf-8')
        
        # Save mobileprovision thumbnail as base64
        await db.save_thumbnails(message.from_user.id, mobileprovision_thumbnail_data=thumbnail_base64)
        
        await message.answer(
            get_text("thumbnails_success"),
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await message.answer(
            get_text("thumbnail_save_error", type="mobileprovision", error=str(e)),
            reply_markup=get_back_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext, db, config):
    """Go back to main menu"""
    await state.clear()
    
    user = await db.get_user(callback.from_user.id)
    registrations = await db.get_user_registrations(callback.from_user.id)
    
    # Only show balance and device info to admin
    if is_admin(callback.from_user.id):
        if user and user.get("api_key"):
            try:
                api_client = OneBotAPIClient(config.API_BASE_URL)
                balance = await api_client.get_balance(user["api_key"])
                # No need to close since we're using context managers now
                
                text = get_text("welcome", balance=balance, devices=len(registrations))
            except:
                text = get_text("welcome_no_balance", devices=len(registrations))
        else:
            text = get_text("welcome_no_api", devices=len(registrations))
    else:
        # Normal users get simple welcome message without sensitive info
        text = get_text("welcome_normal_user")
    
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(callback.from_user.id))
    await callback.answer()

@router.callback_query(F.data == "create_keys")
async def start_key_creation(callback: CallbackQuery, state: FSMContext, db):
    """Start key creation process (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    user = await db.get_user(callback.from_user.id)
    
    if not user or not user.get("api_key"):
        await callback.answer(get_text("error_api_key_first"), show_alert=True)
        return
    
    # Show key statistics
    key_stats = await db.get_key_stats(callback.from_user.id)
    stats_text = get_text("create_keys_start", stats="")
    
    if key_stats:
        stats_lines = []
        for plan, stats in key_stats.items():
            plan_name = PLANS.get(plan, plan)
            stats_lines.append(get_text("stats_unused_keys", plan=plan_name, unused=stats['unused'], total=stats['total']))
        stats_text = get_text("create_keys_start", stats="\n".join(stats_lines))
    else:
        stats_text = get_text("create_keys_start", stats=get_text("no_keys_yet"))
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_key_plans_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("key_plan_"))
async def process_key_plan_selection(callback: CallbackQuery, state: FSMContext):
    """Process plan selection for key creation (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    plan = callback.data.replace("key_plan_", "")
    await state.update_data(key_plan=plan)
    
    plan_name = PLANS.get(plan, plan)
    await callback.message.edit_text(
        get_text("key_plan_selected", plan=plan_name),
        reply_markup=get_back_keyboard()
    )
    await state.set_state(BotStates.waiting_for_key_quantity)
    await callback.answer()

@router.message(StateFilter(BotStates.waiting_for_key_quantity))
async def process_key_quantity(message: Message, state: FSMContext, db):
    """Process key quantity input (admin only)"""
    if not is_admin(message.from_user.id):
        await message.answer("Access denied!")
        return
        
    try:
        quantity = int(message.text.strip())
        if quantity < 1 or quantity > 100:
            await message.answer(
                get_text("key_quantity_invalid"),
                reply_markup=get_back_keyboard()
            )
            return
        
        data = await state.get_data()
        plan = data.get("key_plan")
        
        # Create keys and get the key codes
        key_codes = await db.create_keys(message.from_user.id, plan, quantity)
        
        plan_name = PLANS.get(plan, plan)
        
        # Format the key codes nicely
        keys_text = "\n".join([f"🔑 {code}" for code in key_codes])
        
        success_message = get_text("keys_created", quantity=quantity, plan=plan_name, keys=keys_text)
        
        await message.answer(
            success_message,
            reply_markup=get_back_keyboard()
        )
        
    except ValueError:
        await message.answer(
            get_text("key_quantity_error"),
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.clear()

@router.callback_query(F.data == "use_key")
async def start_key_usage(callback: CallbackQuery, state: FSMContext, db):
    """Start key usage process"""
    user = await db.get_user(callback.from_user.id)
    
    if not user or not user.get("api_key"):
        await callback.answer(get_text("error_api_key_first"), show_alert=True)
        return
    
    await callback.message.edit_text(
        get_text("use_key_start"),
        reply_markup=get_back_keyboard()
    )
    await state.set_state(BotStates.waiting_for_key_code)
    await callback.answer()

@router.message(StateFilter(BotStates.waiting_for_key_code))
async def process_key_code(message: Message, state: FSMContext, db):
    """Process key code input"""
    key_code = message.text.strip().upper()
    
    # Validate key format (10 characters, alphanumeric)
    if not re.match(r'^[A-Z0-9]{10}$', key_code):
        await message.answer(
            get_text("key_format_invalid"),
            reply_markup=get_back_keyboard()
        )
        return
    
    # Check if key exists and is unused
    key = await db.get_key_by_code(key_code)
    if not key:
        await message.answer(
            get_text("key_not_found"),
            reply_markup=get_back_keyboard()
        )
        await state.clear()
        return
    
    if key['used']:
        await message.answer(
            get_text("key_already_used"),
            reply_markup=get_back_keyboard()
        )
        await state.clear()
        return
    
    # Store key info and ask for UDID
    await state.update_data(key_code=key_code, key_plan=key['plan'])
    
    plan_name = PLANS.get(key['plan'], key['plan'])
    await message.answer(
        get_text("key_valid", plan=plan_name),
        reply_markup=get_back_keyboard()
    )
    await state.set_state(BotStates.waiting_for_key_udid)

@router.message(StateFilter(BotStates.waiting_for_key_udid))
async def process_key_udid(message: Message, state: FSMContext, db, config):
    """Process UDID input for key usage"""
    udid = message.text.strip().upper()
    
    if not re.match(r'^[0-9A-F]{8}-[0-9A-F]{16}$', udid):
        await message.answer(
            get_text("invalid_udid"),
            reply_markup=get_back_keyboard()
        )
        return
    
    data = await state.get_data()
    key_code = data.get("key_code")
    plan = data.get("key_plan")
    
    user = await db.get_user(message.from_user.id)
    
    # Add electric reaction to the UDID message
    await message.react([{"type": "emoji", "emoji": "⚡"}])
    
    try:
        api_client = OneBotAPIClient(config.API_BASE_URL)
        result = await api_client.register_udid(user["api_key"], udid, plan)
        
        # Always fetch the latest certificate data for accurate status
        try:
            certificates = await api_client.get_certificate(user["api_key"], udid=udid)
            if certificates:
                cert_data = certificates[0]
                # Use certificate data for status determination (most accurate)
                status = determine_status(cert_data)
                # Save complete certificate data
                await db.save_certificate(
                    message.from_user.id,
                    udid,
                    cert_data.get("id", ""),
                    cert_data
                )
                # Use name from certificate data if available
                name = cert_data.get('name', result.get('name', 'N/A'))
            else:
                # Fallback to registration response
                status = determine_status(result)
                name = result.get('name', 'N/A')
        except:
            # Fallback to registration response
            status = determine_status(result)
            name = result.get('name', 'N/A')
        
        await db.save_registration(
            message.from_user.id,
            udid,
            result.get("certificate_id", ""),
            plan,
            result,
            status
        )
        
        # Mark key as used
        await db.use_key(key_code)
        
        # No need to close since we're using context managers now
        
        status_emoji = "🟡" if status == "processing" else "🟢"
        
        # Format registration success with clean info
        current_date = datetime.now().strftime('%d/%m/%Y')
        plan_name = PLANS.get(plan, plan)
        success_text = get_text("key_registration_success", 
            udid=udid, 
            date=current_date, 
            status=get_text(f"status_{status.lower()}"), 
            emoji=status_emoji, 
            name=name,
            plan=plan_name,
            key_code=key_code
        )
        
        await message.answer(
            success_text,
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await message.answer(
            get_text("registration_failed", error=str(e)),
            reply_markup=get_back_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "manage_ipas")
async def show_ipa_management(callback: CallbackQuery, db):
    """Show IPA management menu (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    user = await db.get_user(callback.from_user.id)
    
    if not user or not user.get("api_key"):
        await callback.answer(get_text("error_api_key_first"), show_alert=True)
        return
    
    ipas = await db.get_user_ipas(callback.from_user.id)
    
    text = get_text("ipa_management", count=len(ipas))
    
    await callback.message.edit_text(
        text,
        reply_markup=get_ipa_management_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "upload_ipa")
async def start_ipa_upload(callback: CallbackQuery, state: FSMContext):
    """Start IPA upload process (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    await callback.message.edit_text(
        get_text("upload_ipa_start"),
        reply_markup=get_back_keyboard()
    )
    await state.set_state(BotStates.waiting_for_ipa_file)
    await callback.answer()

@router.message(StateFilter(BotStates.waiting_for_ipa_file))
async def process_ipa_file(message: Message, state: FSMContext, db):
    """Process uploaded IPA file and save locally (admin only)"""
    if not is_admin(message.from_user.id):
        await message.answer("Access denied!")
        return
        
    if not message.document or not message.document.file_name.endswith('.ipa'):
        await message.answer(
            get_text("ipa_file_invalid"),
            reply_markup=get_back_keyboard()
        )
        return
    
    try:
        # Show processing message
        processing_msg = await message.answer(get_text("ipa_uploading"))
        
        # Download the IPA file
        file = await message.bot.get_file(message.document.file_id)
        file_data = await message.bot.download_file(file.file_path)
        ipa_data = file_data.read()
        
        # Save IPA locally using IPAManager
        ipa_manager = IPAManager()
        local_path = await ipa_manager.save_ipa_locally(ipa_data, message.document.file_name)
        file_size = len(ipa_data)
        
        # Save IPA info to database with minimal info
        ipa_id = await db.save_ipa(
            message.from_user.id,
            message.document.file_name,
            local_path,
            file_size
        )
        
        # Delete processing message
        await processing_msg.delete()
        
        success_text = get_text("ipa_upload_success",
            filename=message.document.file_name,
            size=file_size / 1024 / 1024
        )
        
        await message.answer(
            success_text,
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        await message.answer(
            get_text("ipa_upload_error", error=str(e)),
            reply_markup=get_back_keyboard()
        )
    
    await state.clear()

@router.callback_query(F.data == "list_ipas")
async def list_user_ipas(callback: CallbackQuery, db):
    """List user's IPAs (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    ipas = await db.get_user_ipas(callback.from_user.id)
    
    if not ipas:
        await callback.message.edit_text(
            get_text("no_ipas"),
            reply_markup=get_ipa_management_keyboard()
        )
        await callback.answer()
        return
    
    text = get_text("ipa_list_header")
    
    builder = InlineKeyboardBuilder()
    
    for ipa in ipas:
        text += f"📱 {ipa['app_name']} v{ipa['version']}\n"
        text += f"   📦 {ipa['bundle_id']}\n"
        text += f"   📅 {format_date(ipa['created_at'])}\n\n"
        
        builder.row(
            InlineKeyboardButton(
                text=f"📱 {ipa['app_name']}",
                callback_data=f"ipa_details_{ipa['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="manage_ipas")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("ipa_details_"))
async def show_ipa_details(callback: CallbackQuery, db):
    """Show IPA details (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    ipa_id = int(callback.data.replace("ipa_details_", ""))
    ipa = await db.get_ipa_by_id(ipa_id)
    
    if not ipa or ipa['user_id'] != callback.from_user.id:
        await callback.answer(get_text("ipa_not_found"), show_alert=True)
        return
    
    # Check if local file still exists
    import os
    local_exists = os.path.exists(ipa['local_path']) if ipa['local_path'] else False
    
    text = get_text("ipa_details",
        app_name=ipa['app_name'],
        bundle_id=ipa['bundle_id'],
        version=ipa['version'],
        filename=ipa['original_filename'],
        size=ipa['file_size'] / 1024 / 1024,
        date=format_date(ipa['created_at']),
        local_status=get_text("ipa_local_available") if local_exists else get_text("ipa_local_missing"),
        status=get_text("ipa_status_ready") if ipa['install_url'] else get_text("ipa_status_waiting")
    )
    
    if ipa['signed_at']:
        text += get_text("ipa_signed_date", date=format_date(ipa['signed_at']))
    
    await callback.message.edit_text(
        text,
        reply_markup=get_ipa_actions_keyboard(ipa_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("ipa_link_"))
async def get_ipa_install_link(callback: CallbackQuery, db):
    """Get IPA install link (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    ipa_id = int(callback.data.replace("ipa_link_", ""))
    ipa = await db.get_ipa_by_id(ipa_id)
    
    if not ipa or ipa['user_id'] != callback.from_user.id:
        await callback.answer(get_text("ipa_not_found"), show_alert=True)
        return
    
    if not ipa['install_url']:
        await callback.answer(get_text("ipa_not_signed"), show_alert=True)
        return
    
    text = get_text("ipa_install_link", 
        app_name=ipa['app_name'], 
        install_url=ipa['install_url'], 
        plist_url=ipa['plist_url'], 
        ipa_url=ipa['ipa_url']
    )
    
    await callback.message.edit_text(text, reply_markup=get_ipa_actions_keyboard(ipa_id))
    await callback.answer()

@router.callback_query(F.data.startswith("delete_ipa_"))
async def delete_ipa_file(callback: CallbackQuery, db):
    """Delete IPA file (admin only)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied!", show_alert=True)
        return
        
    ipa_id = int(callback.data.replace("delete_ipa_", ""))
    
    # Delete from database and get filenames
    filenames = await db.delete_ipa(ipa_id, callback.from_user.id)
    
    if not filenames:
        await callback.answer(get_text("ipa_not_found"), show_alert=True)
        return
    
    # Delete from local storage and R2 storage
    ipa_manager = IPAManager()
    
    # Delete local file
    if filenames['local_path']:
        ipa_manager.delete_local_ipa(filenames['local_path'])
    
    # Delete signed files from R2 if they exist
    if filenames['ipa_filename'] and filenames['plist_filename']:
        await ipa_manager.delete_ipa_files(filenames['ipa_filename'], filenames['plist_filename'])
    
    await callback.message.edit_text(
        get_text("ipa_deleted"),
        reply_markup=get_ipa_management_keyboard()
    )
    await callback.answer()

@router.message()
async def handle_unknown_message(message: Message):
    """Handle unknown messages"""
    await message.answer(
        get_text("unknown_command"),
        reply_markup=get_main_menu_keyboard(message.from_user.id)
    )
