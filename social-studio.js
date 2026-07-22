(() => {
  const canvas = document.querySelector('[data-social-canvas]');
  const textBox = document.querySelector('[data-social-text]');
  const langSelect = document.querySelector('[data-social-lang]');
  if (!canvas || !textBox || !langSelect) return;
  const ctx = canvas.getContext('2d');
  let statusData = null;
  function rounded(x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r);}
  function wrap(text,x,y,maxWidth,lineHeight,maxLines=5){const words=String(text||'').split(/\s+/);let line='',lines=[];for(const word of words){const test=line?line+' '+word:word;if(ctx.measureText(test).width>maxWidth&&line){lines.push(line);line=word;}else line=test;}if(line)lines.push(line);lines=lines.slice(0,maxLines);lines.forEach((l,i)=>ctx.fillText(l,x,y+i*lineHeight));return y+lines.length*lineHeight;}
  function render(){
    if(!statusData)return; const en=langSelect.value==='en'; const W=1200,H=630; canvas.width=W;canvas.height=H;
    const status=statusData.status||'INCIERTO'; const accent=status==='ABIERTO'?'#2ee6b8':status==='CERRADO'?'#ff6b6b':'#ffbd59';
    const grad=ctx.createLinearGradient(0,0,W,H);grad.addColorStop(0,'#06101d');grad.addColorStop(.55,'#0d1d2d');grad.addColorStop(1,'#07111f');ctx.fillStyle=grad;ctx.fillRect(0,0,W,H);
    const glow=ctx.createRadialGradient(1040,80,10,1040,80,430);glow.addColorStop(0,accent+'44');glow.addColorStop(1,'transparent');ctx.fillStyle=glow;ctx.fillRect(0,0,W,H);
    ctx.strokeStyle='#68d9ff33';ctx.lineWidth=2;rounded(32,32,W-64,H-64,30);ctx.stroke();
    ctx.fillStyle='#68d9ff';ctx.font='900 23px Arial';ctx.letterSpacing='3px';ctx.fillText('ESTRECHO ORMUZ',72,92);
    ctx.fillStyle='#9db5c8';ctx.font='700 18px Arial';ctx.fillText(en?'INDEPENDENT MARITIME MONITOR':'OBSERVATORIO MARÍTIMO INDEPENDIENTE',72,124);
    ctx.fillStyle=accent;ctx.beginPath();ctx.arc(1090,92,9,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#9db5c8';ctx.font='800 18px Arial';ctx.textAlign='right';ctx.fillText(en?'LIVE STATUS':'ESTADO EN DIRECTO',1060,100);ctx.textAlign='left';
    ctx.fillStyle='#7f9aad';ctx.font='800 18px Arial';ctx.fillText(en?'CURRENT CONDITION':'SITUACIÓN ACTUAL',72,205);
    const label=en?statusData.operational_label_en:statusData.operational_label_es;ctx.fillStyle=accent;ctx.font='950 64px Arial';wrap((label||status).toUpperCase(),72,282,980,70,2);
    ctx.fillStyle='#c6d8e5';ctx.font='400 25px Arial';const sy=wrap(en?statusData.summary_en:statusData.summary_es,72,405,850,34,3);
    ctx.fillStyle='#7f9aad';ctx.font='700 16px Arial';const d=statusData.checked_at?new Date(statusData.checked_at):null;const formatted=d&&!isNaN(d)?new Intl.DateTimeFormat(en?'en-GB':'es-ES',{dateStyle:'medium',timeStyle:'short'}).format(d):'—';ctx.fillText((en?'UPDATED: ':'ACTUALIZADO: ')+formatted,72,552);ctx.fillText((en?'CONFIDENCE: ':'CONFIANZA: ')+(statusData.confidence||'—'),440,552);
    ctx.fillStyle='#edf7ff';ctx.font='900 21px Arial';ctx.textAlign='right';ctx.fillText('estrechoormuz.com',1120,552);ctx.textAlign='left';
    const url=en?'https://estrechoormuz.com/en.html?utm_source=social&utm_medium=organic&utm_campaign=live_status':'https://estrechoormuz.com/?utm_source=social&utm_medium=organic&utm_campaign=estado_actual';
    const summary=en?statusData.summary_en:statusData.summary_es;
    textBox.value=en?`Strait of Hormuz status: ${label || status}.\n\n${summary}\n\nVerified evidence, history and public methodology:\n${url}\n\n#Hormuz #Shipping #Energy #Geopolitics`:`Estado del estrecho de Ormuz: ${label || status}.\n\n${summary}\n\nEvidencias verificadas, historial y metodología pública:\n${url}\n\n#Ormuz #Energía #TransporteMarítimo #Geopolítica`;
  }
  fetch('/status.json?studio='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(d=>{statusData=d;render();});
  langSelect.addEventListener('change',render);
  document.querySelector('[data-download-card]')?.addEventListener('click',()=>{const a=document.createElement('a');a.download=`ormuz-status-${langSelect.value}.png`;a.href=canvas.toDataURL('image/png');a.click();});
  document.querySelector('[data-copy-post]')?.addEventListener('click',async e=>{await navigator.clipboard.writeText(textBox.value);const old=e.currentTarget.textContent;e.currentTarget.textContent=langSelect.value==='en'?'Copied':'Copiado';setTimeout(()=>e.currentTarget.textContent=old,1400);});
})();
