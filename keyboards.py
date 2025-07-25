from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PLANS, is_admin
from languages import lang_manager

def get_text(key: str, **kwargs) -> str:
    """Get localized text"""
    return lang_manager.get_text(key, **kwargs)

def get_main_menu_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Get main menu keyboard - different for admin vs normal users"""
    builder = InlineKeyboardBuilder()
    
    if is_admin(user_id):
        # Admin gets full menu
        # First row - Main actions
        builder.row(
            InlineKeyboardButton(text=get_text("btn_register_udid"), callback_data="register"),
            InlineKeyboardButton(text=get_text("btn_search"), callback_data="search")
        )
        # Second row - Key and IPA management
        builder.row(
            InlineKeyboardButton(text=get_text("btn_use_key"), callback_data="use_key"),
            InlineKeyboardButton(text=get_text("btn_manage_ipas"), callback_data="manage_ipas")
        )
        # Third row - Settings
        builder.row(
            InlineKeyboardButton(text=get_text("btn_settings"), callback_data="settings")
        )
    else:
        # Normal users get limited menu - only Search and Use Key
        builder.row(
            InlineKeyboardButton(text=get_text("btn_search"), callback_data="search"),
            InlineKeyboardButton(text=get_text("btn_use_key"), callback_data="use_key")
        )
    
    return builder.as_markup()

def get_plans_keyboard() -> InlineKeyboardMarkup:
    """Get plans selection keyboard"""
    builder = InlineKeyboardBuilder()
    
    for plan_id, description in PLANS.items():
        builder.row(
            InlineKeyboardButton(
                text=description,
                callback_data=f"plan_{plan_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_key_plans_keyboard() -> InlineKeyboardMarkup:
    """Get plans selection keyboard for key creation"""
    builder = InlineKeyboardBuilder()
    
    for plan_id, description in PLANS.items():
        builder.row(
            InlineKeyboardButton(
                text=description,
                callback_data=f"key_plan_{plan_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="settings")
    )
    
    return builder.as_markup()

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Get back to main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="back_to_main")
    )
    return builder.as_markup()

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Get settings keyboard - horizontal layout"""
    builder = InlineKeyboardBuilder()
    
    # First row - API Key and Thumbnails
    builder.row(
        InlineKeyboardButton(text=get_text("btn_set_api_key"), callback_data="set_api_key"),
        InlineKeyboardButton(text=get_text("btn_set_thumbnails"), callback_data="set_thumbnails")
    )
    
    # Second row - Create Keys
    builder.row(
        InlineKeyboardButton(text=get_text("btn_create_keys"), callback_data="create_keys")
    )
    
    # Third row - Back button
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_certificate_keyboard(udid: str, enabled: bool = True, status: str = "active", user_id: int = None) -> InlineKeyboardMarkup:
    """Get certificate management keyboard - different for admin vs normal users"""
    builder = InlineKeyboardBuilder()
    
    # Only admin gets toggle button
    if is_admin(user_id):
        toggle_emoji = "🟢" if enabled else "🔴"
        toggle_text = f"{toggle_emoji} {'Enabled' if enabled else 'Disabled'}"
        builder.row(
            InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_{udid}")
        )
    
    # Get Certificate button (only if enabled and active)
    if enabled and status == "active":
        builder.row(
            InlineKeyboardButton(text=get_text("btn_get_certificate"), callback_data=f"download_cert_{udid}")
        )
    
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_udid_input_keyboard() -> InlineKeyboardMarkup:
    """Get UDID input keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="back_to_main")
    )
    return builder.as_markup()

def get_ipa_management_keyboard() -> InlineKeyboardMarkup:
    """Get IPA management keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=get_text("btn_upload_ipa"), callback_data="upload_ipa"),
        InlineKeyboardButton(text=get_text("btn_list_ipas"), callback_data="list_ipas")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_ipa_actions_keyboard(ipa_id: int) -> InlineKeyboardMarkup:
    """Get IPA actions keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=get_text("btn_get_install_link"), callback_data=f"ipa_link_{ipa_id}"),
        InlineKeyboardButton(text=get_text("btn_delete"), callback_data=f"delete_ipa_{ipa_id}")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("btn_back"), callback_data="manage_ipas")
    )
    
    return builder.as_markup()
