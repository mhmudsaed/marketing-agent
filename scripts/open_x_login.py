"""Open the persistent X browser profile for one-time login setup."""
import asyncio

from clients.playwright_x import XPlaywrightPublisher


async def main():
    publisher = XPlaywrightPublisher()
    playwright, context = await publisher._open_context()
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(publisher.login_url, wait_until="domcontentloaded", timeout=60000)
        await page.bring_to_front()
        print("X login window is open.")
        print(f"Persistent profile: {publisher.user_data_dir}")
        print("Sign in inside the browser window. When X shows you as logged in, press Enter here.")
        await asyncio.to_thread(input)
    finally:
        await context.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main())
