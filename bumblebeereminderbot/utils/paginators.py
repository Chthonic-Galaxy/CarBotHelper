from dataclasses import dataclass, field
from typing import Sequence, Union, TypeAlias, Optional, Any, Protocol
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardBuilder
from datetime import datetime, timedelta

# Type Definitions
EventType: TypeAlias = Union[Message, CallbackQuery]
KeyboardDataType: TypeAlias = Union[str, CallbackData]
ContentType: TypeAlias = Union[str, Sequence[str]]

# Exceptions
class PaginatorException(Exception):
    """Base exception for Paginator-related errors."""
    pass

class ContentValidationError(PaginatorException):
    """Raised when content validation fails."""
    pass

class NavigationError(PaginatorException):
    """Raised when navigation operations fails."""
    pass

# Protocols
class CacheProtocol(Protocol):
    async def get(self, key: str) -> Optional[Any]:
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ...
    
    async def delete(self, key: str) -> None:
        ...

# Cache Implementation
class MemoryCache:
    def __init__(self):
        self._cache: dict[str, tuple[Any, Optional[datetime]]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        if expiry and datetime.now() > expiry:
            await self.delete(key)
            return None
        
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expiry = datetime.now() + timedelta(seconds=ttl) if ttl else None
        self._cache[key] = (value, expiry)
    
    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

# Data Classes
@dataclass
class PaginatorConfig:
    """Configuration for paginator behavior."""
    cache_ttl: Optional[int] = 3600  # Cache TTL in seconds
    show_page_numbers: bool = True
    show_first_last: bool = True
    row_sizes: tuple[int, ...] = field(default_factory=lambda: (2,))
    loading_text: str = "Loading..."
    error_text: str = "An error occurred. Please try again."

@dataclass
class PaginatorKeyboard:
    """Container for keyboard data."""
    buttons: dict[str, KeyboardDataType] = field(default_factory=dict)
    row_sizes: tuple[int, ...] = field(default_factory=lambda: (2,))

@dataclass
class PaginatorPage:
    """Container for page data."""
    event: EventType
    content: ContentType
    keyboard: Optional[PaginatorKeyboard] = None
    config: PaginatorConfig = field(default_factory=PaginatorConfig)

# Callback Data
class MovePage(CallbackData, prefix="paginator"):
    """Callback data for pagination navigation."""
    action: str  # 'next', 'prev', 'current', 'first', 'last'
    page: Optional[int] = None

# Content Manager
class ContentManager:
    """Handles content processing and validation."""
    
    @staticmethod
    def validate_content(content: ContentType) -> None:
        """Validate content format and structure."""
        if not content:
            raise ContentValidationError("Content cannot be empty")
        
        if isinstance(content, str):
            if not content.strip():
                raise ContentValidationError("Content string cannot be empty")
        elif isinstance(content, Sequence):
            if not all(isinstance(item, str) for item in content):
                raise ContentValidationError("All content items must be strings")
            if not all(item.strip() for item in content):
                raise ContentValidationError("Content items cannot be empty")
        else:
            raise ContentValidationError("Invalid content type")

    @staticmethod
    def format_content(content: ContentType) -> list[str]:
        """Format content into a list of strings."""
        if isinstance(content, str):
            return [content]
        return list(content)

# Keyboard Builder
class KeyboardBuilder:
    """Handles keyboard construction and formatting."""
    
    @staticmethod
    def create_navigation(
        current_page: int,
        total_pages: int,
        config: PaginatorConfig
    ) -> dict[str, KeyboardDataType]:
        """Create navigation keyboard buttons."""
        keyboard: dict[str, KeyboardDataType] = {}
        
        if config.show_first_last and current_page > 1:
            keyboard["⏮️"] = MovePage(action="first")
        
        if current_page > 1:
            keyboard["⬅️"] = MovePage(action="prev")
        
        if config.show_page_numbers:
            keyboard[f"{current_page}/{total_pages}"] = MovePage(action="current")
        
        if current_page < total_pages:
            keyboard["➡️"] = MovePage(action="next")
        
        if config.show_first_last and current_page < total_pages:
            keyboard["⏭️"] = MovePage(action="last")
        
        return keyboard

    @staticmethod
    def merge_keyboards(
        nav_keyboard: dict[str, KeyboardDataType],
        custom_keyboard: Optional[PaginatorKeyboard]
    ) -> dict[str, KeyboardDataType]:
        """Merge navigation and custom keyboards."""
        if custom_keyboard is None:
            return nav_keyboard
        return {**custom_keyboard.buttons, **nav_keyboard}

    @staticmethod
    def build_keyboard(
        buttons: dict[str, KeyboardDataType],
        row_sizes: tuple[int, ...]
    ) -> InlineKeyboardMarkup:
        """Build final keyboard markup."""
        builder = InlineKeyboardBuilder()
        
        for text, callback_data in buttons.items():
            builder.add(InlineKeyboardButton(
                text=text,
                callback_data=callback_data if isinstance(callback_data, str)
                else callback_data.pack()
            ))
        
        return builder.adjust(*row_sizes).as_markup()

# Main Paginator Class
class Paginator:
    """
    Advanced paginator for handling paginated content with inline keyboards in Telegram.
    
    Features:
    - Content validation and formatting
    - Customizable navigation
    - Memory-efficient caching
    - Comprehensive error handling
    - Loading states
    - Configurable behavior
    """
    
    def __init__(
        self,
        page: PaginatorPage,
        cache: Optional[CacheProtocol] = None
    ):
        """Initialize paginator with content and optional cache."""
        self.page = page
        self.cache = cache or MemoryCache()
        self.content_manager = ContentManager()
        self.keyboard_builder = KeyboardBuilder()
        
        self._initialize()
    
    def _initialize(self) -> None:
        """Initialize paginator state."""
        self.content_manager.validate_content(self.page.content)
        self.content = self.content_manager.format_content(self.page.content)
        self.total_pages = len(self.content)
        self.current_page = 1
    
    async def _get_page_content(self, page: int) -> tuple[str, InlineKeyboardMarkup]:
        """Get content and keyboard for specified page."""
        cache_key = f"page_{id(self)}_{page}"
        
        # Try to get from cache
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Generate new content
        nav_keyboard = self.keyboard_builder.create_navigation(
            page, self.total_pages, self.page.config
        )
        
        merged_keyboard = self.keyboard_builder.merge_keyboards(
            nav_keyboard, self.page.keyboard
        )
        
        markup = self.keyboard_builder.build_keyboard(
            merged_keyboard,
            self.page.config.row_sizes
        )
        
        content = (self.content[page - 1], markup)
        
        # Cache the result
        if self.page.config.cache_ttl:
            await self.cache.set(cache_key, content, self.page.config.cache_ttl)
        
        return content
    
    async def show_page(self, page: Optional[int] = None) -> None:
        """Show specified page or current page."""
        target_page = page or self.current_page
        
        if not 1 <= target_page <= self.total_pages:
            raise NavigationError(f"Page {target_page} out of range (1-{self.total_pages})")
        
        try:
            # Show loading state
            if isinstance(self.page.event, Message):
                message = await self.page.event.answer(
                    text=self.page.config.loading_text
                )
            else:
                message = await self.page.event.message.edit_text(
                    text=self.page.config.loading_text
                )
            
            # Get and show content
            content, markup = await self._get_page_content(target_page)
            
            if isinstance(self.page.event, Message):
                await message.edit_text(text=content, reply_markup=markup)
            else:
                await self.page.event.message.edit_text(
                    text=content,
                    reply_markup=markup
                )
                await self.page.event.answer()
                
        except Exception as e:
            # Handle errors
            error_text = f"{self.page.config.error_text}\nDetails: {str(e)}"
            if isinstance(self.page.event, Message):
                await message.edit_text(text=error_text)
            else:
                await self.page.event.message.edit_text(text=error_text)
            raise PaginatorException(f"Failed to show page: {e}")
    
    async def handle_navigation(self, callback_data: MovePage) -> None:
        """Handle navigation callback."""
        match callback_data.action:
            case "next":
                if self.current_page < self.total_pages:
                    self.current_page += 1
            case "prev":
                if self.current_page > 1:
                    self.current_page -= 1
            case "first":
                self.current_page = 1
            case "last":
                self.current_page = self.total_pages
            case "current":
                pass
        
        await self.show_page()