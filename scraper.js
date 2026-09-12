const { chromium } = require('playwright');
const fs = require('fs');

const OUTPUT_DIR = 'output';
fs.mkdirSync(OUTPUT_DIR, { recursive: true });

// টার্গেট URL (টিভি চ্যানেল লিস্ট)
const TARGET_URL = 'https://toffeelive.com/en/watch';

async function scrapeChannels() {
  console.log('🚀 Launching browser...');
  
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
  });
  
  const page = await context.newPage();
  
  // সব ডেটা স্টোর করার জন্য অ্যারে
  const channels = [];
  const m3u8Links = [];
  const cookies = [];
  let userAgent = '';
  
  // Network request মনিটর করা
  page.on('response', async (response) => {
    const url = response.url();
    const headers = response.headers();
    
    // M3U8 লিংক খোঁজা
    if (url.includes('.m3u8') || url.includes('playlist') || url.includes('manifest')) {
      console.log('🎬 Found M3U8:', url);
      m3u8Links.push({
        url: url,
        headers: headers,
        timestamp: new Date().toISOString()
      });
    }
    
    // API রেসপন্স চেক করা
    if (url.includes('content-prod') || url.includes('entitlement')) {
      try {
        const contentType = headers['content-type'] || '';
        if (contentType.includes('json')) {
          const body = await response.text();
          console.log('📡 API Response:', url);
        }
      } catch (e) {}
    }
  });
  
  // পেজে যাওয়া
  console.log('🌐 Navigating to:', TARGET_URL);
  
  try {
    await page.goto(TARGET_URL, {
      waitUntil: 'networkidle',
      timeout: 60000
    });
    
    // ইউজার এজেন্ট সংগ্রহ
    userAgent = await page.evaluate(() => navigator.userAgent);
    console.log('🆔 User Agent:', userAgent);
    
    // কুকি সংগ্রহ
    const pageCookies = await context.cookies();
    console.log('🍪 Cookies found:', pageCookies.length);
    
    // HTML Local Storage থেকে ডেটা নেওয়া
    const localStorage = await page.evaluate(() => {
      const data = {};
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        data[key] = localStorage.getItem(key);
      }
      return data;
    });
    
    // Session Storage
    const sessionStorage = await page.evaluate(() => {
      const data = {};
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i);
        data[key] = sessionStorage.getItem(key);
      }
      return data;
    });
    
    // চ্যানেল লিস্ট এক্সট্রাক্ট করা
    console.log('📺 Extracting channels...');
    
    // বিভিন্ন সিলেক্টর ট্রাই করা
    const channelData = await page.evaluate(() => {
      const channels = [];
      
      // কমন সিলেক্টরগুলো
      const selectors = [
        '[data-testid="channel-item"]',
        '.channel-item',
        '.channel-card',
        '[class*="channel"]',
        '.rail-item',
        '.slider-item'
      ];
      
      for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        elements.forEach((el, index) => {
          const name = el.textContent?.trim() || 
                      el.querySelector('img')?.alt || 
                      `Channel ${index + 1}`;
          
          const logo = el.querySelector('img')?.src || '';
          const link = el.querySelector('a')?.href || '';
          
          if (name && name.length > 0) {
            channels.push({
              id: index + 1,
              name: name,
              logo: logo,
              pageUrl: link,
              category: 'Unknown'
            });
          }
        });
      }
      
      return channels;
    });
    
    console.log(`✅ Found ${channelData.length} channels`);
    
    // পেজের HTML সেভ করা (পরে পার্সিং এর জন্য)
    const htmlContent = await page.content();
    fs.writeFileSync(`${OUTPUT_DIR}/page-source.html`, htmlContent);
    
    // API কল লিস্ট সংগ্রহ
    const apiCalls = await page.evaluate(() => {
      return window.performance.getEntriesByType('resource')
        .filter(r => r.name.includes('api') || r.name.includes('content'))
        .map(r => ({
          url: r.name,
          type: r.initiatorType,
          duration: r.duration
        }));
    });
    
    // সব ডেটা একত্রিত করা
    const finalData = {
      scrapedAt: new Date().toISOString(),
      sourceUrl: TARGET_URL,
      userAgent: userAgent,
      cookies: pageCookies.map(c => ({
        name: c.name,
        value: c.value,
        domain: c.domain,
        path: c.path
      })),
      localStorage: localStorage,
      sessionStorage: sessionStorage,
      channels: channelData,
      m3u8Links: m3u8Links,
      apiCalls: apiCalls
    };
    
    // JSON হিসেবে সেভ
    fs.writeFileSync(
      `${OUTPUT_DIR}/channels-data.json`, 
      JSON.stringify(finalData, null, 2)
    );
    
    // M3U ফাইল তৈরি (VLC/IPTV প্লেয়ারের জন্য)
    let m3uContent = '#EXTM3U\n';
    m3uLinks.forEach((link, index) => {
      m3uContent += `#EXTINF:-1, Channel ${index + 1}\n`;
      m3uContent += `${link.url}\n`;
    });
    fs.writeFileSync(`${OUTPUT_DIR}/playlist.m3u`, m3uContent);
    
    // রিপোর্ট তৈরি
    const report = `
# Scraping Report

**Time:** ${new Date().toISOString()}
**Source:** ${TARGET_URL}

## Summary
- Channels Found: ${channelData.length}
- M3U8 Links: ${m3u8Links.length}
- Cookies: ${pageCookies.length}

## User Agent
\`\`\`
${userAgent}
\`\`\`

## Sample Cookies
${pageCookies.slice(0, 5).map(c => `- ${c.name}: ${c.value.substring(0, 50)}...`).join('\n')}

## Channels
${channelData.slice(0, 10).map(c => `- ${c.name}`).join('\n')}
${channelData.length > 10 ? `\n... and ${channelData.length - 10} more` : ''}
`;
    
    fs.writeFileSync(`${OUTPUT_DIR}/report.md`, report);
    
    console.log('💾 Data saved to output/ directory');
    console.log('📄 Files created:');
    console.log('   - channels-data.json');
    console.log('   - playlist.m3u');
    console.log('   - report.md');
    console.log('   - page-source.html');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    
    // এরর হলেও স্ক্রিনশট নেওয়া
    await page.screenshot({ 
      path: `${OUTPUT_DIR}/error-screenshot.png`,
      fullPage: true 
    });
    
    throw error;
    
  } finally {
    await browser.close();
    console.log('🔒 Browser closed');
  }
}

// রান করা
scrapeChannels().catch(console.error);
