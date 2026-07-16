(() => {
  "use strict";
  const lang = document.documentElement.lang === "en" ? "en" : "es";
  const words = {
    es:{error:"No se pudo cargar el parte diario.",copied:"Copiado",copyError:"No se pudo copiar"},
    en:{error:"The daily brief could not be loaded.",copied:"Copied",copyError:"Could not copy"}
  }[lang];
  const statusClass = status => ({ABIERTO:"is-open",CERRADO:"is-closed",INCIERTO:"is-uncertain"}[status] || "is-uncertain");
  const formatDate = value => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(lang === "es" ? "es-ES" : "en-GB", {
      dateStyle:"long",timeStyle:"short",timeZone:lang === "es" ? "Europe/Madrid" : "UTC"
    }).format(date) + (lang === "en" ? " UTC" : "");
  };
  const getJSON = async file => {
    const response = await fetch(`${file}?v=${Date.now()}`, {cache:"no-store"});
    if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
    return response.json();
  };
  const setText = (id,value) => {const node=document.getElementById(id);if(node)node.textContent=value ?? "—";};
  const renderList = (id,items) => {
    const root=document.getElementById(id);if(!root)return;root.replaceChildren();
    (items||[]).forEach(value=>{const li=document.createElement("li");li.textContent=value;root.append(li);});
  };
  const renderEvidence = items => {
    const root=document.getElementById("briefEvidence");if(!root)return;root.replaceChildren();
    (items||[]).slice(0,5).forEach(item=>{
      const article=document.createElement("article");
      const meta=document.createElement("p");meta.textContent=`${item.source_name||"—"} · ${formatDate(item.published_at)}`;
      const heading=document.createElement("h3");const link=document.createElement("a");
      link.href=item.source_url||"#";link.target="_blank";link.rel="noopener noreferrer";link.textContent=item.title||"Evidence";
      heading.append(link);article.append(meta,heading);root.append(article);
    });
  };
  const renderArchive = items => {
    const root=document.getElementById("briefArchive");if(!root)return;root.replaceChildren();
    (items||[]).slice(0,6).forEach(item=>{
      const article=document.createElement("article");const time=document.createElement("time");
      time.textContent=item.date||"—";const heading=document.createElement("h3");
      heading.textContent=lang==="es"?item.operational_label_es:item.operational_label_en;
      const text=document.createElement("p");text.textContent=lang==="es"?item.summary_es:item.summary_en;
      article.append(time,heading,text);root.append(article);
    });
  };
  async function renderBrief(){
    const loading=document.getElementById("briefLoading");
    try{
      const [brief,archive]=await Promise.all([getJSON("/daily-brief.json"),getJSON("/daily-brief-archive.json")]);
      if(loading)loading.hidden=true;
      setText("briefDate",brief.date);
      setText("briefOperational",lang==="es"?brief.operational_label_es:brief.operational_label_en);
      setText("briefSummary",lang==="es"?brief.summary_es:brief.summary_en);
      setText("briefConfidence",brief.confidence_label?.[lang]||brief.confidence);
      setText("briefGenerated",formatDate(brief.generated_at));
      setText("briefChange",lang==="es"?brief.change_es:brief.change_en);
      const pill=document.getElementById("briefStatusPill");
      if(pill){pill.textContent=lang==="es"?brief.status_label_es:brief.status_label_en;pill.className=`brief-pill ${statusClass(brief.status)}`;}
      renderList("briefRisks",lang==="es"?brief.risks_es:brief.risks_en);
      renderList("briefWatch",lang==="es"?brief.watchlist_es:brief.watchlist_en);
      renderEvidence(brief.evidence);
      renderArchive(Array.isArray(archive)?archive:archive.items);
    }catch(error){console.error(error);if(loading){loading.hidden=false;loading.textContent=words.error;}}
  }
  async function renderDrafts(){
    const roots=document.querySelectorAll("[data-draft]");if(!roots.length)return;
    try{
      const data=await getJSON("/social-drafts.json");
      roots.forEach(root=>{const area=root.querySelector("textarea");if(area)area.value=data[root.dataset.draft]||"";});
    }catch(error){console.error(error);}
  }
  document.addEventListener("DOMContentLoaded",()=>{
    renderBrief();renderDrafts();
    document.querySelectorAll("[data-copy-target]").forEach(button=>{
      button.addEventListener("click",async()=>{
        const target=document.querySelector(button.dataset.copyTarget);
        const feedback=button.parentElement?.querySelector(".copy-feedback");
        try{await navigator.clipboard.writeText(target?.value||target?.textContent||"");if(feedback)feedback.textContent=words.copied;}
        catch(error){if(feedback)feedback.textContent=words.copyError;}
      });
    });
  });
})();
