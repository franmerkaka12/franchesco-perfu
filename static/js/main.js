/* ==========================================================================
   FRANCHESCO · Interacciones y animaciones de la tienda
   ========================================================================== */
(function () {
  'use strict';

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  /* --- Preloader ---------------------------------------------------------- */
  const ocultarPreloader = () => { const p = $('#preloader'); if (p) p.classList.add('oculto'); };
  window.addEventListener('load', ocultarPreloader);
  setTimeout(ocultarPreloader, 2500); // por si alguna imagen tarda demasiado

  /* --- Header compacto y botón "volver arriba" ---------------------------- */
  const header = $('.header');
  const volver = $('.volver-arriba');
  const alScroll = () => {
    const y = window.scrollY;
    if (header) {
      header.classList.toggle('con-sombra', y > 10);
      header.classList.toggle('compacto', y > 140);
    }
    if (volver) volver.classList.toggle('visible', y > 600);
  };
  window.addEventListener('scroll', alScroll, { passive: true });
  alScroll();
  if (volver) volver.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  /* --- Aparición de elementos al hacer scroll ----------------------------- */
  const revelables = $$('[data-reveal]');
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    // Escalonado: cada hijo dentro de un mismo grupo aparece con un pequeño retraso
    $$('[data-reveal-grupo]').forEach((grupo) => {
      $$('[data-reveal]', grupo).forEach((el, i) => el.style.setProperty('--retraso', `${Math.min(i, 8) * 0.07}s`));
    });
    revelables.forEach((el) => obs.observe(el));
  } else {
    revelables.forEach((el) => el.classList.add('visible'));
  }

  /* --- Toasts ------------------------------------------------------------- */
  const ICONOS = { success: 'bi-check-circle-fill', danger: 'bi-x-circle-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
  function cerrarToast(t) { t.classList.add('saliendo'); setTimeout(() => t.remove(), 400); }
  function prepararToast(t) {
    const btn = $('.cerrar', t);
    if (btn) btn.addEventListener('click', () => cerrarToast(t));
    setTimeout(() => cerrarToast(t), 5200);
  }
  window.mostrarToast = function (mensaje, tipo = 'success', htmlExtra = '') {
    const zona = $('.zona-toasts');
    if (!zona) return;
    const t = document.createElement('div');
    t.className = `toast-f ${tipo}`;
    t.setAttribute('role', 'status');
    t.innerHTML = `<i class="bi ${ICONOS[tipo] || ICONOS.info} icono"></i><div></div><button class="cerrar" aria-label="Cerrar"><i class="bi bi-x-lg"></i></button>`;
    t.children[1].textContent = mensaje;
    if (htmlExtra) t.children[1].insertAdjacentHTML('beforeend', htmlExtra);
    zona.appendChild(t);
    prepararToast(t);
  };
  $$('.zona-toasts .toast-f').forEach(prepararToast);

  /* --- Agregar al carrito sin recargar la página (AJAX) ------------------- */
  function actualizarContador(cantidad) {
    $$('.contador-carrito').forEach((c) => {
      c.textContent = cantidad;
      c.classList.toggle('vacio', !cantidad);
      c.classList.remove('rebote'); void c.offsetWidth; c.classList.add('rebote');
    });
  }

  document.addEventListener('submit', async (ev) => {
    const form = ev.target.closest('form.js-add-cart');
    if (!form) return;
    ev.preventDefault();
    const boton = $('button[type="submit"], button:not([type])', form);
    const icono = boton ? $('i', boton) : null;
    const iconoOriginal = icono ? icono.className : '';
    if (boton) { boton.disabled = true; boton.classList.add('cargando'); }
    if (icono) icono.className = 'bi bi-arrow-repeat';
    try {
      const resp = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
      });
      if (!resp.ok) throw new Error('Error del servidor');
      const datos = await resp.json();
      actualizarContador(datos.cantidad);
      mostrarToast(datos.mensaje, datos.ok ? 'success' : 'warning', datos.ok ? ' <a href="/carrito/">Ver carrito</a>' : '');
      if (icono && datos.ok) icono.className = 'bi bi-check2';
    } catch (e) {
      mostrarToast('No pudimos agregar el producto. Intentá nuevamente.', 'danger');
    } finally {
      setTimeout(() => {
        if (boton) { boton.disabled = false; boton.classList.remove('cargando'); }
        if (icono) icono.className = iconoOriginal;
      }, 900);
    }
  });

  /* --- Selector de cantidad (+ / -) --------------------------------------- */
  document.addEventListener('click', (ev) => {
    const btn = ev.target.closest('[data-cantidad]');
    if (!btn) return;
    const caja = btn.closest('.selector-cantidad');
    const input = $('input', caja);
    const min = parseInt(input.min || '1', 10);
    const max = parseInt(input.max || '999', 10);
    let valor = parseInt(input.value || '1', 10) + parseInt(btn.dataset.cantidad, 10);
    valor = Math.max(min, Math.min(max, valor));
    if (String(valor) !== input.value) {
      input.value = valor;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  // En el carrito, el cambio de cantidad se envía automáticamente
  document.addEventListener('change', (ev) => {
    const input = ev.target.closest('.js-autoenviar input');
    if (!input) return;
    clearTimeout(input._t);
    input._t = setTimeout(() => input.form.submit(), 450);
  });

  /* --- Sliders horizontales de productos ---------------------------------- */
  $$('.slider').forEach((slider) => {
    const pista = $('.slider__pista', slider);
    const barra = $('.slider__barra', slider);
    const prev = $('[data-slider="prev"]', slider);
    const next = $('[data-slider="next"]', slider);
    if (!pista) return;
    const paso = () => pista.clientWidth * 0.8;
    const actualizar = () => {
      const max = pista.scrollWidth - pista.clientWidth;
      const visible = pista.clientWidth / pista.scrollWidth;
      if (barra) {
        barra.style.width = `${Math.min(100, visible * 100)}%`;
        const recorrido = max > 0 ? pista.scrollLeft / max : 0;
        barra.style.transform = `translateX(${recorrido * (1 / visible - 1) * 100}%)`;
      }
      if (prev) prev.disabled = pista.scrollLeft <= 2;
      if (next) next.disabled = pista.scrollLeft >= max - 2;
    };
    if (prev) prev.addEventListener('click', () => pista.scrollBy({ left: -paso() }));
    if (next) next.addEventListener('click', () => pista.scrollBy({ left: paso() }));
    pista.addEventListener('scroll', actualizar, { passive: true });
    window.addEventListener('resize', actualizar);
    actualizar();
  });

  /* --- Zoom en la imagen del producto ------------------------------------- */
  $$('.galeria').forEach((g) => {
    const media = g.querySelector('img, svg');
    g.addEventListener('mousemove', (e) => {
      const r = g.getBoundingClientRect();
      media.style.transformOrigin = `${((e.clientX - r.left) / r.width) * 100}% ${((e.clientY - r.top) / r.height) * 100}%`;
    });
    g.addEventListener('mouseenter', () => g.classList.add('zoom'));
    g.addEventListener('mouseleave', () => g.classList.remove('zoom'));
  });

  /* --- Copiar código de cupón --------------------------------------------- */
  $$('[data-copiar]').forEach((el) => {
    el.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(el.dataset.copiar);
        mostrarToast(`Código ${el.dataset.copiar} copiado. ¡Usalo al finalizar tu compra!`, 'info');
      } catch (e) { /* el navegador no permite copiar */ }
    });
  });

  /* --- Confirmaciones ----------------------------------------------------- */
  document.addEventListener('submit', (ev) => {
    const msg = ev.target.dataset && ev.target.dataset.confirmar;
    if (msg && !window.confirm(msg)) ev.preventDefault();
  }, true);
})();

/* --- Tarjetas con varios tamaños: al tocar los ml cambia el precio --- */
(function () {
  'use strict';
  document.addEventListener('click', (ev) => {
    const chip = ev.target.closest('.js-card-ml');
    if (!chip) return;
    ev.preventDefault();
    const card = chip.closest('.card-producto');
    const d = chip.dataset;
    card.querySelectorAll('.js-card-ml').forEach((c) => {
      c.classList.toggle('activo', c === chip);
      c.setAttribute('aria-pressed', c === chip ? 'true' : 'false');
    });
    const poner = (sel, txt) => card.querySelectorAll(sel).forEach((el) => { el.textContent = txt; });
    poner('.js-card-precio', d.precio);
    poner('.js-card-cuota', d.cuota);
    poner('.js-card-sinimp', d.sinimp);
    const antes = card.querySelector('.js-card-antes');
    if (antes) { antes.textContent = d.antes; antes.classList.toggle('d-none', !d.antes); }
    const off = card.querySelector('.js-card-off');
    if (off) { off.textContent = d.off + '%'; off.classList.toggle('d-none', d.off === '0'); }
    card.querySelectorAll('.js-card-link').forEach((a) => { a.href = d.url; });
    const form = card.querySelector('.js-card-form');
    if (form) form.action = d.agregar;
    const disponible = d.disponible === '1';
    if (form) form.classList.toggle('d-none', !disponible);
    const sinStock = card.querySelector('.js-card-sinstock');
    if (sinStock) sinStock.classList.toggle('d-none', disponible);
    // pequeño destello en el precio
    const precio = card.querySelector('.js-card-precio');
    if (precio && precio.animate) precio.animate([{ opacity: 0.3 }, { opacity: 1 }], { duration: 250 });
  });
})();
