import { chromium, devices } from 'playwright';
import consola from 'consola';
import fs from 'fs';

async function main() {
  
    consola.info('模拟浏览器查询，Endress产品订单号，自增第三位到第六位。\n');
    consola.start('Start Chromium Browser...');

    const browser = await chromium.launch();
    const context = await browser.newContext(devices['Desktop Chrome']);
    const page = await context.newPage();
    consola.ready('Chromium Browser Ready');

    // 用户输入
    let sleepTime: number | undefined;
    while (!sleepTime) {
        sleepTime = Number(await consola.prompt('Enter Sleep Time (seconds): ', { initial: '2000' }));
        if (!sleepTime || sleepTime <= 0) {
            consola.error('Sleep Time should be greater than 0');
            sleepTime = undefined;
        }
    }

    let startSn: string | undefined;
    while (!startSn) {
        startSn = await consola.prompt('Enter Start SN: ', { initial: 'w5021927ka0' });
        if (!startSn || startSn.length !== 11) {
            consola.error('SN is Empty, please enter a valid SN');
            startSn = undefined;
        }
    }

    let searchCount: number | undefined;
    while (!searchCount) {
        searchCount = Number(await consola.prompt('Enter Search Count: ', { initial: '10' }));
        if (!searchCount || searchCount < 1) {
            consola.error('Search Count should be greater than 0');
            searchCount = undefined;
        }
    }

    consola.box(`Start SN: ${startSn}\nSearch Count: ${searchCount}`);

    // 导航到 Endress 网站
    consola.info('Navigating to Endress website...');
    await page.goto('https://www.endress.com.cn/zh/product-tools');
    await page.waitForLoadState('load');

    // 接受 Cookie
    consola.info('Accepting cookies...');
    await page.click('button:has-text("全部接受")', { timeout: 5000 });

    // 进入 Device Viewer
    consola.start('Entering Device Viewer...');
    await page.locator('li').filter({ hasText: '访问设备的具体信息' }).getByRole('link').click();
    await page.waitForSelector('#eh-page iframe');

    const frame = page.frameLocator('#eh-page iframe');
    const snInput = frame.getByLabel('*');
    const snButton = frame.getByRole('button', { name: 'Search' });
    await snButton.waitFor({ state: 'attached' });
    consola.success('Device Viewer loaded\n');

    let [prefix, no, suffix] = [startSn.slice(0, 2), startSn.slice(2, 6), startSn.slice(6)];
    let notOrderCodeCounter = 0;

    for (let i = 0; i < searchCount; i++) {
        if (notOrderCodeCounter >= 10) {
            consola.error('No order code found for 10 times, exit');
            break;
        }

        no = (parseInt(no, 16) + 1).toString(16).padStart(4, '0');

        const sn = `${prefix}${no}${suffix}`;
        consola.start(`Search SN: ${sn.toUpperCase()}`);
        await snInput.fill(sn);
        await snButton.click();

        try {
            await Promise.race([
                frame.locator('div.v-gridlayout-slot').filter({ hasText: sn }).waitFor(),
                frame.locator('text=No data found for this serial').waitFor()
            ]);

            if (await frame.locator('text=No data found for this serial').isVisible()) {
                consola.error('Not Data\n');
                notOrderCodeCounter++;
                await frame.getByRole('button', { name: 'OK' }).click();
                await page.waitForTimeout(sleepTime);
                continue;
            }

            const deviceDetailsText = await frame.locator('div.v-gridlayout-slot').nth(5).textContent();
            if (!deviceDetailsText) {
                consola.error('No order code found, try next\n');
                notOrderCodeCounter++;
            } else {
                const orderCode = deviceDetailsText.trim();
                fs.appendFileSync('order-code.txt', `${sn.toUpperCase()},${orderCode.toUpperCase()}\n`, 'utf8');
                consola.success(`Order code found: ${orderCode.toUpperCase()}\n`);
                notOrderCodeCounter = 0;
            }
        } catch (error) {
            consola.error('Error during search:', error, '\n');
        }

        await page.waitForTimeout(sleepTime);
    }

    // 关闭浏览器
    await context.close();
    await browser.close();

    consola.success('Done');
    process.exit(0);
}

main().catch(err => {
    consola.error('Unexpected error:', err);
    process.exit(1);
});
