document.addEventListener('DOMContentLoaded', () => {

  /* ── 導航列滾動效果 ── */
  const nav = document.querySelector('nav');
  let lastScroll = 0;
  window.addEventListener('scroll', () => {
    const sy = window.scrollY;
    if (sy > 80 && sy > lastScroll) {
      nav.style.transform = 'translateY(-100%)';
    } else {
      nav.style.transform = 'translateY(0)';
    }
    lastScroll = sy;
  });

  /* ── 淡入動畫 ── */
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        entry.target.style.transitionDelay = `${i * 0.08}s`;
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll('.card, .step, .stack-item, .tree-item').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity .6s ease, transform .6s ease';
    observer.observe(el);
  });

  document.addEventListener('scroll', () => {
    document.querySelectorAll('.card.visible, .step.visible, .stack-item.visible, .tree-item.visible').forEach(el => {
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    });
  });

  /* ── 補上 visible class 後才顯示（避免 IntersectionObserver 來不及觸發） ── */
  const style = document.createElement('style');
  style.textContent = `
    .card.visible, .step.visible, .stack-item.visible, .tree-item.visible {
      opacity: 1 !important;
      transform: translateY(0) !important;
    }
  `;
  document.head.appendChild(style);

  /* ── 監控所有卡片、步驟等元素，觸發時加上 class ── */
  const ro = new ResizeObserver(() => {
    document.querySelectorAll('.card:not(.visible), .step:not(.visible), .stack-item:not(.visible), .tree-item:not(.visible)').forEach(el => {
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight * 0.85) {
        el.classList.add('visible');
      }
    });
  });
  ro.observe(document.body);

  /* ── command 區塊一鍵複製 ── */
  document.querySelectorAll('.code-block, .card-cmd').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', async () => {
      try {
        const text = el.textContent.replace(/^[\s$]+/, '');
        await navigator.clipboard.writeText(text);
        const tip = document.createElement('span');
        tip.textContent = ' ✓ 已複製';
        tip.style.cssText = 'position:absolute;right:14px;color:#3fb950;font-family:system-ui;font-size:.75rem;';
        el.style.position = 'relative';
        el.appendChild(tip);
        setTimeout(() => tip.remove(), 1200);
      } catch { /* ignore */ }
    });
  });

});
