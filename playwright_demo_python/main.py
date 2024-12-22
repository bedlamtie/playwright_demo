import asyncio
import sys

from playwright.async_api import async_playwright, TimeoutError
from rich.console import Console
from rich.prompt import Prompt

console = Console()


async def main():
    # Setup
    async with async_playwright() as p:
        console.print('[green]模拟浏览器查询，Endress产品订单号，自增第三位到第六位。\n[/]')
        console.print('Start Chromium Browser...')
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()
        console.print('Chromium Browser Ready')

        sleep_time = None
        while not sleep_time:
            sleep_time = Prompt.ask('Enter Sleep Time (seconds)', default='2000')
            if not sleep_time or int(sleep_time) < 1:
                console.print('[red]Sleep Time should be greater than 0[/]')
                sleep_time = None

        start_sn = None
        while not start_sn:
            start_sn = Prompt.ask('Enter Start SN', default='w5021927ka0')
            # start_sn = Prompt.ask('Enter Start SN', default='w506eb27ka0')
            if not start_sn or len(start_sn) != 11:
                console.print('[red]SN is Empty, please enter a valid SN[/]')
                start_sn = None

        search_count = None
        while not search_count:
            search_count = Prompt.ask('Enter Search Count', default='10')
            if not search_count or int(search_count) < 1:
                console.print('[red]Search Count should be greater than 0[/]')
                search_count = None

        console.rule(f'Start SN: {start_sn}\nSearch Count: {search_count}')

        # Go to Endress
        console.print('Go to Endress')
        await page.goto('https://www.endress.com.cn/zh/product-tools')
        await page.wait_for_load_state('load')

        # Accept cookies
        console.print('Accept cookies')
        accept_button = page.get_by_role('button', name='全部接受')
        if await accept_button.is_visible():
            await accept_button.click()

        # Go to Device Viewer
        console.print('Go to Device Viewer')
        await page.locator('li').filter(has_text='访问设备的具体信息').get_by_role('link').click()

        # Wait for the iframe to load
        await page.wait_for_selector('#eh-page iframe')
        iframe = page.locator("#eh-page iframe").content_frame
        sn_input = iframe.get_by_label('*')
        sn_button = iframe.get_by_role('button', name='Search')

        try:
            await sn_button.wait_for(state='attached')
        except TimeoutError as err:
            console.print(f'[red]GoTo Device Viewer failed: {err.name}[/]')
            await context.close()
            await browser.close()
            Prompt.ask('Press any key to exit...')
            sys.exit(0)

        console.print('[green]Device Viewer loaded[/]')

        # SN: w5021927ka0
        no = start_sn[2:6]
        prefix = start_sn[:2]
        suffix = start_sn[6:]

        not_order_code_counter = 0

        for i in range(int(search_count)):

            if not_order_code_counter >= 10:
                console.print('[red]No order code found for 10 times, exit[/]')
                break

            no = format(int(no, 16) + 1, '04x')

            sn = f'{prefix}{no}{suffix}'
            console.print(f'\nSearch SN: {sn.upper()}')
            await sn_input.fill(sn)
            await sn_button.click()

            # w5045d27ka0
            device_details = iframe.get_by_role("tabpanel").locator("div").filter(has_text="Device details").nth(3)

            try:
                has_data = asyncio.create_task(
                    device_details.locator('div.v-gridlayout-slot').filter(has_text=sn).wait_for(state='attached'))
                not_data = asyncio.create_task(
                    iframe.get_by_text("No data found for this serial").wait_for(state='attached'))

                done, pending = await asyncio.wait(fs=[has_data, not_data], timeout=30, return_when='FIRST_COMPLETED')

                # 取消并等待所有未完成的任务
                for task in pending:
                    task.cancel()

                await iframe.get_by_text("No data found for this serial").wait_for(state='attached', timeout=100)
                console.print('[red]Not Data[/]')
                not_order_code_counter += 1
                await iframe.get_by_role("button", name="OK").click()
                await page.wait_for_timeout(int(sleep_time))

                continue
            except TimeoutError:
                pass

            device_details_text = await device_details.locator('div.v-gridlayout-slot').nth(5).text_content()
            if not device_details_text:
                console.print('[red]No order code found, try next[/]')
                not_order_code_counter += 1
            else:
                order_code = device_details_text.strip()
                with open('order-code.txt', 'a', encoding='utf-8') as file:
                    file.write(f'{sn.upper()},{order_code.upper()}\n')
                console.print(f'[green]Order code found: {order_code.upper()}[/]')
                not_order_code_counter = 0

            await page.wait_for_timeout(int(sleep_time))

        # Close
        await context.close()
        await browser.close()

        # 按任意键退出
        console.print('[green]\nDone[/]')
        Prompt.ask('Press any key to exit...')
        console.print('[red]Bye[/]')
        sys.exit(0)


if __name__ == '__main__':
    asyncio.run(main())
