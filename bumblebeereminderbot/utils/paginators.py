from dataclasses import dataclass

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, ReplyKeyboardMarkup

from bumblebeereminderbot.telegram.kbd.inline import get_callback_btns, MovePage

@dataclass
class Page():
    event: Message | CallbackQuery
    text: str | None = None
    keyboard: dict[str, str] | None = None
    keyboard_size: tuple[int] = (2,)


class Paginator():
    def __init__(
            self,
            items: list[Page],
            page_size: int = 10
        ) -> None:
        self.items = items
        self.page_size = page_size
        self.total_items = len(items)
        self.current_page = 1
        self.total_pages = (self.total_items + self.page_size - 1) // self.page_size

    def _get_keyboard(self, page_number: int) -> dict:
        standard_keyboard: dict[str, str] = {}
        
        if self.has_prev(page_number):
            standard_keyboard["Пред."] = MovePage(move_to=-1).pack()
        if self.has_next(page_number):
            standard_keyboard["След."] = MovePage(move_to=1).pack()
        
        return standard_keyboard
        

    async def _get_page(self, page_number: int) -> None:
        
        if not (1 < self.current_page < self.total_pages):
            raise ValueError("Page number out of range")
        
        item = self.items[page_number]
        if isinstance(item.event, Message):
            await item.event.answer(
                text=item.text,
                reply_markup=get_callback_btns(
                    btns={**item.keyboard, **self._get_keyboard(page_number)},
                    sizes=item.keyboard_size,
                    custom=True
                )
            )
        else:
            await item.event.message.answer(
                text=item.text,
                reply_markup=get_callback_btns(
                    btns={**item.keyboard, **self._get_keyboard(page_number)},
                    sizes=item.keyboard_size,
                    custom=True
                )
            )
    
    
    async def current(self) -> None:
        if not (1 < self.current_page < self.total_pages):
            raise ValueError("Page number out of range")
        return await self._get_page(self.current_page)
    
    async def next(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
        return await self.current()
    
    async def prev(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
        return await self.current()
    
    async def set_current_page(self, page_number: int) -> None:
        if 1 < page_number < self.total_pages:
            self.current_page = page_number
        else:
            raise ValueError("Page number out of range")
        return await self.current()
    
    def has_next(self, page_number: int) -> bool:
        if page_number < self.total_pages:
            return True
        return False

    def has_prev(self, page_number: int) -> bool:
        if 1 < page_number <= self.total_pages:
            return True
        return False
