import logging
import signal
import threading
from telebot import types
from config import bot, ADMIN_ID
from downloader_queue import start_worker, stop_worker

import handlers
import callbacks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger(__name__)
_shutdown_requested = threading.Event()


def _configure_bot_commands():
    """
    Configure Telegram command menus with scopes:
    - Default scope: safe public commands only
    - Admin chat scope: includes admin-only commands
    """
    public_commands = [
        types.BotCommand('start', 'Start bot / Open main menu'),
    ]

    admin_commands = [
        types.BotCommand('adduser', 'Approve user: /adduser <id>'),
        types.BotCommand('deluser', 'Disable user: /deluser <id>'),
        types.BotCommand('setquota', 'Set quota: /setquota <id> <files> <GB>'),
        types.BotCommand('users', 'Manage users panel: /users'),
        types.BotCommand('togglereg', 'Toggle self-registration'),
        types.BotCommand('setgithub', 'Set GitHub token: /setgithub <TOKEN> <owner/repo>'),
        types.BotCommand('broadcast', 'Broadcast: /broadcast <message>'),
    ]

    # Everyone sees only public commands.
    bot.set_my_commands(
        public_commands,
        scope=types.BotCommandScopeDefault(),
    )

    # The admin sees both public + admin commands in their own chat menu.
    if ADMIN_ID > 0:
        bot.set_my_commands(
            public_commands + admin_commands,
            scope=types.BotCommandScopeChat(ADMIN_ID),
        )


def _request_shutdown(signum=None, frame=None):
    if _shutdown_requested.is_set():
        return

    _shutdown_requested.set()
    if signum is not None:
        logger.info("Shutdown requested by signal %s", signum)
    else:
        logger.info("Shutdown requested")

    try:
        bot.stop_polling()
    except Exception:
        logger.exception("Error while stopping Telegram polling")

    stop_worker(cancel_pending=True)


def _register_signal_handlers():
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _request_shutdown)
        except (AttributeError, ValueError):
            logger.debug("Signal %s is not available in this runtime", sig)


def main():
    _register_signal_handlers()
    start_worker()
    try:
        bot.remove_webhook()
        _configure_bot_commands()
        logger.info("Bot is running")

        while not _shutdown_requested.is_set():
            try:
                bot.infinity_polling(timeout=30, long_polling_timeout=30)
            except KeyboardInterrupt:
                _request_shutdown()
                break
            except Exception:
                if _shutdown_requested.is_set():
                    break
                logger.exception("Polling failed; restarting in 5 seconds")
                if _shutdown_requested.wait(5):
                    break
    finally:
        _request_shutdown()


if __name__ == '__main__':
    main()
