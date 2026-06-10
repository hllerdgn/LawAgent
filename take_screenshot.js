const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  await page.setViewport({ width: 400, height: 800, deviceScaleFactor: 3 });
  
  const htmlPath = path.resolve(__dirname, 'screenshot_chatbot.html');
  await page.goto(`file:///${htmlPath.replace(/\\/g, '/')}`, { 
    waitUntil: 'networkidle0',
    timeout: 10000
  });
  
  await new Promise(r => setTimeout(r, 3000));
  
  const chatbot = await page.$('.chatbot-container');
  if (chatbot) {
    await chatbot.screenshot({
      path: path.resolve(__dirname, 'lawagent_chatbot_screenshot.png'),
      type: 'png'
    });
    console.log('Screenshot saved!');
  }
  
  await browser.close();
  console.log('Done!');
})();
