"""
Wrapper para executar Playwright em thread separado (Windows fix)
"""

import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import functools

# Nota: A policy é definida em main.py para evitar conflitos
# WindowsProactorEventLoopPolicy é necessário para subprocessos (Playwright)


def run_in_thread_with_new_loop(async_func):
    """
    Decorator para executar função async em thread separado com novo event loop.
    Isso resolve o problema do Playwright no Windows.
    """
    @functools.wraps(async_func)
    def wrapper(*args, **kwargs):
        def run_async():
            # Cria novo ProactorEventLoop para esta thread (suporta subprocessos)
            if sys.platform == 'win32':
                loop = asyncio.ProactorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_func(*args, **kwargs))
            finally:
                loop.close()

        # Executa em thread pool
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_async)
            return future.result()

    return wrapper


async def run_in_executor(async_func, *args, **kwargs):
    """
    Executa função async em executor separado.
    Útil para chamar de dentro de funções async.
    """
    loop = asyncio.get_event_loop()

    def sync_wrapper():
        # Cria novo ProactorEventLoop para esta thread (suporta subprocessos)
        if sys.platform == 'win32':
            new_loop = asyncio.ProactorEventLoop()
        else:
            new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            new_loop.close()

    with ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(executor, sync_wrapper)

    return result
