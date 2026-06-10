const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  console.log('Puppeteer başlatılıyor...');
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const page = await browser.newPage();
  
  // Set viewport to match A1 aspect ratio (1200x1699) with 300 DPI scale factor (5.847x)
  // This produces a high-resolution print-ready PNG (7016 x 9933 pixels) corresponding to 594x841 mm
  await page.setViewport({ width: 1200, height: 1699, deviceScaleFactor: 5.847 });
  
  try {
    const htmlPath = path.resolve(__dirname, 'poster.html');
    const fileUrl = `file:///${htmlPath.replace(/\\/g, '/')}`;
    console.log(`Poster yükleniyor: ${fileUrl}`);
    
    await page.goto(fileUrl, { 
      waitUntil: 'load',
      timeout: 30000
    });
    
    // Wait for web fonts (Montserrat, Inter) and QR code API to load completely
    console.log('Fontlar ve QR kod yükleniyor (4 saniye bekleniyor)...');
    await new Promise(r => setTimeout(r, 4000));
    
    // Save as high-resolution PNG
    const pngPath = path.resolve(__dirname, 'lawagent_poster.png');
    console.log(`PNG Poster kaydediliyor: ${pngPath}`);
    await page.screenshot({
      path: pngPath,
      type: 'png',
      fullPage: true
    });
    
    // Save as printable vector A1 PDF
    const pdfPath = path.resolve(__dirname, 'lawagent_poster.pdf');
    console.log(`PDF Poster kaydediliyor: ${pdfPath}`);
    await page.pdf({
      path: pdfPath,
      format: 'A1',
      preferCSSPageSize: true,
      printBackground: true,
      margin: { top: '0px', right: '0px', bottom: '0px', left: '0px' }
    });
    
    console.log('Poster başarıyla oluşturuldu!');
  } catch (error) {
    console.error('Poster oluşturulurken hata meydana geldi:', error);
  } finally {
    await browser.close();
  }
})();
