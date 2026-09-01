(() => {
  const lang = document.documentElement.lang.startsWith('en') ? 'en' : 'es';
  const form = document.querySelector('[data-embed-form]');
  const frame = document.querySelector('[data-embed-preview]');
  const code = document.querySelector('[data-embed-code]');
  if (!form || !frame || !code) return;
  const update = () => {
    const data = new FormData(form);
    const selectedLang = data.get('lang');
    const theme = data.get('theme');
    const compact = data.get('compact') === '1' ? '1' : '0';
    const height = compact === '1' ? 175 : 260;
    const path = selectedLang === 'en' ? 'en-widget.html' : 'widget.html';
    const src = `https://estrechoormuz.com/${path}?lang=${selectedLang}&theme=${theme}&compact=${compact}`;
    frame.src = src;
    frame.style.height = `${height}px`;
    code.textContent = `<iframe src="${src}" title="${selectedLang === 'en' ? 'Live Strait of Hormuz status' : 'Estado en directo del estrecho de Ormuz'}" width="100%" height="${height}" loading="lazy" style="border:0;border-radius:20px;overflow:hidden" referrerpolicy="strict-origin-when-cross-origin"></iframe>`;
  };
  form.addEventListener('change', update);
  document.querySelector('[data-copy-embed]')?.addEventListener('click', async (e) => {
    const button = e.currentTarget;
    try {
      await navigator.clipboard.writeText(code.textContent);
      button.textContent = lang === 'en' ? 'Copied' : 'Copiado';
    } catch {
      button.textContent = lang === 'en' ? 'Select and copy the code below' : 'Selecciona y copia el código de abajo';
    }
    setTimeout(() => { button.textContent = lang === 'en' ? 'Copy code' : 'Copiar código'; }, 3000);
  });
  update();
})();
