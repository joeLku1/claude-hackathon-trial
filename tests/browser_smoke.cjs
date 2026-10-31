/* Run with Plotcraft serving locally and Playwright + Chromium installed. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1500, height: 1050}});
  const failures=[];
  page.on('pageerror', error=>failures.push(error.message));
  page.setDefaultTimeout(15000);
  const renderAfter = async action => {
    const response = page.waitForResponse(r=>r.url().endsWith('/api/render') && r.request().method()==='POST');
    await action();
    const result=await (await response).json();
    await page.waitForFunction(()=>!/Updating|Preparing/.test(document.getElementById('renderStatus').textContent));
    return result;
  };
  const edit = async (selector,value) => renderAfter(async()=>{
    const input=page.locator(selector);await input.fill(value);await input.dispatchEvent('change');
  });
  const saved = async action => {
    const pending=page.waitForEvent('download');await action();const download=await pending;
    const stream=await download.createReadStream(),chunks=[];for await(const chunk of stream)chunks.push(chunk);
    return Buffer.concat(chunks);
  };
  try {
    await page.goto('http://127.0.0.1:8765');
    await page.waitForFunction(()=>document.getElementById('renderStatus').textContent.includes('Up to date'));
    await page.locator('#chartImage').evaluate(img=>img.decode());
    assert.equal(await page.locator('#notice').isVisible(),false);
    fs.mkdirSync('test-results',{recursive:true});
    await page.screenshot({path:'test-results/studio.png',fullPage:true});
    let result=await edit('[aria-label="Cell B4"]','100');
    assert.equal(result.values[5][1],107);
    result=await edit('[aria-label="Cell B4"]','=B4');
    assert.match(result.errors.B4,/Circular/);
    assert.equal(await page.locator('#export').isDisabled(),true);
    result=await renderAfter(()=>page.locator('#undo').click());
    assert.equal(result.values[5][1],107);
    await renderAfter(()=>page.locator('[data-type="line"]').click());
    await renderAfter(()=>page.locator('[data-theme="1"]').click());
    await renderAfter(()=>page.locator('#addNote').click());
    await edit('[aria-label="Annotation 2 text"]','A community, growing together.');
    const before=await page.locator('[data-drag-note="1"]').boundingBox();
    await renderAfter(async()=>{
      await page.mouse.move(before.x+8,before.y+8);await page.mouse.down();
      await page.mouse.move(before.x+85,before.y+40,{steps:8});await page.mouse.up();
    });
    const after=await page.locator('[data-drag-note="1"]').boundingBox();
    assert.ok(after.x>before.x+50);
    await page.locator('[aria-label="Cell B1"]').click();
    await renderAfter(()=>page.locator('#cellFormat').selectOption('currency'));
    await renderAfter(()=>page.locator('#cellBold').click());
    await page.locator('#projectName').click();
    assert.equal(await page.locator('[aria-label="Cell B1"]').inputValue(),'$28.00');
    const projectBytes=await saved(()=>page.locator('#saveProject').click());
    const project=JSON.parse(projectBytes);
    assert.equal(project.chart.type,'line');assert.equal(project.chart.background,'#192435');
    assert.equal(project.annotations[1].text,'A community, growing together.');
    for(const [format,signature] of [['svg','<?xml'],['png','\x89PNG'],['pdf','%PDF']]){
      await page.locator('#exportFormat').selectOption(format);
      const bytes=await saved(()=>page.locator('#export').click());
      assert.equal(bytes.subarray(0,signature.length).toString('latin1'),signature);
      if(format==='svg')assert.ok(bytes.includes(Buffer.from('A community, growing together.')));
    }
    await page.locator('#chartImage').evaluate(img=>img.decode());
    await page.screenshot({path:'test-results/after-hours.png',fullPage:true});
    await page.locator('#importCsv').click();
    await renderAfter(()=>page.locator('#fileInput').setInputFiles({name:'demo.csv',mimeType:'text/csv',buffer:Buffer.from('Month,Revenue\nJuly,12\nAugust,18')}));
    assert.equal(await page.locator('#dataCount').textContent(),'2 rows · 1 series');
    assert.equal(await page.locator('[data-chart="background"]').inputValue(),'#192435');
    await page.locator('#openProject').click();
    await renderAfter(()=>page.locator('#fileInput').setInputFiles({name:'saved.plotcraft.json',mimeType:'application/json',buffer:projectBytes}));
    assert.equal(await page.locator('#dataCount').textContent(),'6 rows · 2 series');
    await renderAfter(()=>page.locator('#undo').click());
    assert.equal(await page.locator('#dataCount').textContent(),'2 rows · 1 series');
    await renderAfter(()=>page.locator('#redo').click());
    assert.equal(await page.locator('#dataCount').textContent(),'6 rows · 2 series');
    await page.reload();await page.waitForFunction(()=>document.getElementById('renderStatus').textContent.includes('Up to date'));
    assert.equal(await page.locator('[data-chart="background"]').inputValue(),'#192435');
    assert.equal(await page.locator('[aria-label="Annotation 2 text"]').inputValue(),'A community, growing together.');
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'test-results/mobile.png',fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'Mobile layout must not overflow');
    assert.deepEqual(failures,[]);
    console.log('Browser smoke passed: edit/recalculate, errors, undo/redo, themes, text drag, cell formatting, all exports, CSV, project reload, autosave, mobile.');
  } catch(error) {
    fs.mkdirSync('test-results',{recursive:true});
    await page.screenshot({path:'test-results/failure.png',fullPage:true});
    throw error;
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
